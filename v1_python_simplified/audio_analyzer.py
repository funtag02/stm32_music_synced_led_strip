"""
audio_analyzer.py — LuminaSnake V1

Non-blocking audio capture, FFT analysis, and Auto-Gain Control (AGC).

Design notes:
- PyAudio runs its callback on a dedicated C thread managed by PortAudio.
  We share data with the main thread via a thread-safe queue (queue.Queue).
  This guarantees the Pygame loop is never blocked waiting for audio.
- A Hanning window is pre-computed once and reused every frame to avoid
  spectral leakage (the artefact that makes a pure sine wave look like it
  has energy at many frequencies when it doesn't).
- All FFT/band-energy math is fully vectorised with NumPy — no Python loops
  over individual samples.
"""

from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt
import pyaudio

import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------

@dataclass
class BandAnalysis:
    """Analysis result for a single frequency band at one point in time.

    Attributes:
        amplitude:   Normalised RMS energy in [0.0, 1.0] after AGC.
        dominant_hz: Frequency (Hz) of the bin with peak energy in this band.
    """
    amplitude:    float
    dominant_hz:  float


@dataclass
class AudioFrame:
    """One processed audio frame containing analysis for all bands.

    Attributes:
        bands: Tuple of BandAnalysis, one per entry in config.FREQUENCY_BANDS.
    """
    bands: tuple[BandAnalysis, ...]


# ---------------------------------------------------------------------------
# Internal AGC state (one instance per band)
# ---------------------------------------------------------------------------

@dataclass
class _AGCState:
    """Tracks the running peak energy estimate used by the AGC.

    The AGC works like an automatic volume knob:
    - When the signal is loud, the peak estimate rises quickly (attack).
    - When the signal is quiet, it falls slowly (decay).
    This prevents the LEDs from going dark during quiet passages while still
    reacting dynamically to loud transients.

    Attributes:
        peak: Current peak energy estimate (always > AGC_MIN_ENERGY).
    """
    peak: float = field(default_factory=lambda: config.AGC_MIN_ENERGY)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class AudioAnalyzer:
    """Captures microphone audio and produces per-band frequency analysis.

    Uses a PyAudio stream in callback mode so the capture runs on a
    background thread managed by PortAudio — the main thread only reads
    pre-processed AudioFrame objects from an internal queue.

    Usage:
        analyzer = AudioAnalyzer()
        analyzer.start()
        ...
        frame: AudioFrame | None = analyzer.get_latest_frame()
        ...
        analyzer.stop()

    Raises:
        RuntimeError: If no suitable input device is found on the system.
    """

    def __init__(self) -> None:
        self._pa = pyaudio.PyAudio()
        self._stream: pyaudio.Stream | None = None

        # Queue depth of 1: we only care about the *latest* frame.
        # Any older frames are discarded to prevent audio/visual drift.
        self._frame_queue: queue.Queue[AudioFrame] = queue.Queue(maxsize=1)

        # Pre-compute the Hanning window for CHUNK_SIZE samples.
        # Multiplying the raw PCM chunk by this window before FFT tapers the
        # signal to zero at both ends, eliminating edge discontinuities that
        # would otherwise create phantom frequency energy across the spectrum.
        self._window: npt.NDArray[np.float32] = np.hanning(config.CHUNK_SIZE).astype(np.float32)

        # Pre-compute the FFT frequency axis once (it never changes).
        # np.fft.rfftfreq returns the positive-frequency bins for a real FFT.
        self._freqs: npt.NDArray[np.float64] = np.fft.rfftfreq(
            config.CHUNK_SIZE, d=1.0 / config.SAMPLE_RATE
        )

        # Pre-compute boolean index masks for each frequency band so we don't
        # recompute them on every frame (vectorised boolean indexing is fast,
        # but building the mask has overhead).
        self._band_masks: tuple[npt.NDArray[np.bool_], ...] = tuple(
            (self._freqs >= band.low_hz) & (self._freqs <= band.high_hz)
            for band in config.FREQUENCY_BANDS
        )

        # One AGC state object per band.
        self._agc_states: tuple[_AGCState, ...] = tuple(
            _AGCState() for _ in config.FREQUENCY_BANDS
        )

        # Lock protecting AGC state — the callback thread writes to it, the
        # main thread reads it via get_latest_frame (indirectly through the
        # queue, but the AGC state itself is mutated in the callback).
        # In practice the GIL protects float writes in CPython, but the lock
        # makes intent explicit and future-proofs against free-threaded builds.
        self._agc_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Open the default microphone and begin background capture.

        Raises:
            RuntimeError: If PyAudio cannot open an input stream.
        """
        device_index = self._find_input_device()
        try:
            self._stream = self._pa.open(
                format=config.AUDIO_FORMAT,
                channels=config.CHANNELS,
                rate=config.SAMPLE_RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=config.CHUNK_SIZE,
                stream_callback=self._audio_callback,
                # start=True is the default; the stream begins immediately.
            )
            logger.info("Audio stream opened (device=%s, rate=%d Hz, chunk=%d)",
                        device_index, config.SAMPLE_RATE, config.CHUNK_SIZE)
        except OSError as exc:
            raise RuntimeError(f"Failed to open audio stream: {exc}") from exc

    def stop(self) -> None:
        """Stop the audio stream and release PortAudio resources."""
        if self._stream is not None:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None
        self._pa.terminate()
        logger.info("Audio stream closed.")

    def get_agc_peaks(self) -> tuple[float, ...]:
        """Return the current AGC peak estimate for each band.

        The peak is the running maximum energy the AGC is tracking — it
        represents the dynamic "ceiling" against which amplitude is normalised.
        Useful for displaying "amplitude / peak" in the UI.

        Returns:
            Tuple of floats (one per band), each >= AGC_MIN_ENERGY.
        """
        with self._agc_lock:
            return tuple(state.peak for state in self._agc_states)

    def get_latest_frame(self) -> AudioFrame | None:
        """Return the most recently processed AudioFrame, or None if not ready.

        This method never blocks. The caller should handle None gracefully
        (e.g. reuse the previous frame or skip the snake tick).

        Returns:
            The latest AudioFrame, or None if no new frame is available.
        """
        try:
            return self._frame_queue.get_nowait()
        except queue.Empty:
            return None

    # ------------------------------------------------------------------
    # Internal — PyAudio callback (runs on PortAudio's C thread)
    # ------------------------------------------------------------------

    def _audio_callback(
        self,
        in_data: bytes,
        frame_count: int,          # noqa: ARG002  (required by PyAudio signature)
        time_info: dict,           # noqa: ARG002
        status_flags: int,
    ) -> tuple[None, int]:
        """Called by PortAudio every CHUNK_SIZE samples.

        This method must return quickly — any delay here causes audio glitches.
        We do all the heavy work in NumPy (which releases the GIL internally),
        then push the result onto the queue for the main thread to consume.

        Args:
            in_data:      Raw PCM bytes from the microphone.
            frame_count:  Number of frames in this chunk (= CHUNK_SIZE).
            time_info:    PortAudio timing dict (not used here).
            status_flags: Bitmask of stream status flags (e.g. input overflow).

        Returns:
            (None, pyaudio.paContinue) — we never write output audio.
        """
        if status_flags:
            # paContinue = 0, so any non-zero flag indicates a problem.
            logger.warning("Audio stream status flag: %d (possible buffer overflow)", status_flags)

        # --- 1. Decode raw PCM bytes → normalised float32 array [-1.0, 1.0] ---
        samples = np.frombuffer(in_data, dtype=np.int16).astype(np.float32)
        samples /= 32768.0  # 2^15 — normalise int16 range to [-1, 1]

        # --- 2. Apply Hanning window ---
        windowed = samples * self._window

        # --- 3. Real FFT → magnitude spectrum ---
        # rfft only returns the non-redundant positive-frequency half.
        spectrum: npt.NDArray[np.float32] = np.abs(np.fft.rfft(windowed))

        # --- 4. Analyse each frequency band ---
        frame = self._analyse_bands(spectrum)

        # --- 5. Push to queue (drop oldest if full) ---
        # If the main thread is running slow, we discard the stale frame
        # rather than letting the queue grow unbounded.
        try:
            self._frame_queue.put_nowait(frame)
        except queue.Full:
            try:
                self._frame_queue.get_nowait()   # discard stale frame
            except queue.Empty:
                pass
            self._frame_queue.put_nowait(frame)

        return (None, pyaudio.paContinue)

    # ------------------------------------------------------------------
    # Internal — analysis helpers
    # ------------------------------------------------------------------

    def _analyse_bands(self, spectrum: npt.NDArray[np.float32]) -> AudioFrame:
        """Extract per-band amplitude and dominant frequency from a magnitude spectrum.

        Args:
            spectrum: FFT magnitude array (length = CHUNK_SIZE // 2 + 1).

        Returns:
            AudioFrame with one BandAnalysis per configured frequency band.
        """
        results: list[BandAnalysis] = []

        with self._agc_lock:
            for band, mask, agc in zip(
                config.FREQUENCY_BANDS, self._band_masks, self._agc_states
            ):
                band_spectrum = spectrum[mask]
                band_freqs    = self._freqs[mask]

                if band_spectrum.size == 0:
                    # Degenerate case: no FFT bins fall in this band
                    # (can happen with very small CHUNK_SIZE).
                    results.append(BandAnalysis(amplitude=0.0, dominant_hz=band.low_hz))
                    continue

                # RMS energy — more perceptually stable than peak magnitude.
                energy: float = float(np.sqrt(np.mean(band_spectrum ** 2)))

                # AGC: update peak with asymmetric attack/decay envelope.
                if energy > agc.peak:
                    agc.peak += config.AGC_ATTACK * (energy - agc.peak)
                else:
                    agc.peak -= config.AGC_DECAY  * (agc.peak - energy)

                # Clamp peak to floor to avoid division by zero on silence.
                agc.peak = max(agc.peak, config.AGC_MIN_ENERGY)

                # Normalise energy to [0.0, 1.0].
                amplitude = min(energy / agc.peak, 1.0)

                # Dominant frequency: bin with highest magnitude in this band.
                dominant_hz = float(band_freqs[np.argmax(band_spectrum)])

                results.append(BandAnalysis(amplitude=amplitude, dominant_hz=dominant_hz))

        return AudioFrame(bands=tuple(results))

    # ------------------------------------------------------------------
    # Internal — device selection
    # ------------------------------------------------------------------

    def _find_input_device(self) -> int | None:
        """Return the index of the best available input device.

        Prefers the system default input device. Falls back to the first
        device that supports the configured sample rate and channel count.

        Returns:
            Device index, or None to let PyAudio use the OS default.

        Raises:
            RuntimeError: If no compatible input device is found.
        """
        # Try the system default first — usually the right choice.
        try:
            default_info = self._pa.get_default_input_device_info()
            logger.info("Using default input device: %s", default_info["name"])
            return None  # None tells PyAudio to use the OS default
        except OSError:
            logger.warning("No default input device — scanning all devices...")

        # Manual scan fallback.
        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            if info["maxInputChannels"] >= config.CHANNELS:
                logger.info("Fallback input device [%d]: %s", i, info["name"])
                return i

        raise RuntimeError(
            "No suitable microphone found. "
            "Check that a microphone is connected and not muted by the OS."
        )