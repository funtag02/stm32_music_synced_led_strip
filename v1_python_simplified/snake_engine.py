"""
snake_engine.py — LuminaSnake V1

Manages the four LED strip buffers and the BPM-driven propagation logic.

The "snake" effect:
    At every tick, each LED copies the colour of its left neighbour:
        strip[i] ← strip[i-1]   for i in [1, LEDS_PER_STRIP)
    LED 0 is always freshly computed from the current audio analysis.

Using collections.deque with a fixed maxlen is ideal here:
    - appendleft() pushes a new colour onto the front in O(1).
    - The deque automatically discards the last element when full.
    - This avoids any explicit shift loop — the data structure *is* the snake.
"""

from __future__ import annotations

import time
from collections import deque

import config
from audio_analyzer import AudioFrame
from mapper import Mapper

# Type alias for a single RGB colour.
RGB = tuple[int, int, int]

# Type alias for one full strip state (a deque of RGB tuples).
StripBuffer = deque[RGB]


class SnakeEngine:
    """Manages four LED strip buffers and drives the snake propagation.

    The engine is decoupled from both the audio source and the renderer:
    it receives AudioFrame objects and exposes strip state as plain lists
    of RGB tuples that any renderer (Pygame, UDP, etc.) can consume.

    Attributes:
        bpm:         Current BPM setting. Modifiable at runtime.
        multiplier:  Tick subdivisions per beat (default = 1.0).

    Usage:
        engine = SnakeEngine()
        engine.update(audio_frame)          # call every Pygame frame
        strips = engine.get_strips()        # read current LED state
    """

    def __init__(self) -> None:
        self._mapper = Mapper()

        # One deque per frequency band.  maxlen=LEDS_PER_STRIP means that
        # appendleft() automatically drops the rightmost (oldest) element.
        self._strips: tuple[StripBuffer, ...] = tuple(
            deque(
                [(0, 0, 0)] * config.LEDS_PER_STRIP,
                maxlen=config.LEDS_PER_STRIP,
            )
            for _ in range(config.NUM_STRIPS)
        )

        self.bpm: float = config.DEFAULT_BPM
        self.multiplier: float = config.BPM_MULTIPLIER

        # Timestamp of the last snake tick (used to determine when to advance).
        self._last_tick_time: float = time.monotonic()

        # Cache the last received audio frame so the snake still ticks
        # even if no new audio frame has arrived (fills with silence colours).
        self._last_frame: AudioFrame | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def tick_interval_ms(self) -> float:
        """Current tick interval in milliseconds, derived from BPM.

        Returns:
            Interval in ms between consecutive snake propagation steps.
        """
        bpm = max(config.MIN_BPM, min(self.bpm, config.MAX_BPM))
        return 60_000.0 / (bpm * self.multiplier)

    def update(self, frame: AudioFrame | None) -> None:
        """Advance the snake if the tick interval has elapsed.

        Should be called once per Pygame frame (60 Hz). The snake only
        propagates when enough time has passed according to the current BPM —
        so this method is a no-op on most frames.

        Args:
            frame: Latest audio analysis, or None if no new frame is available.
                   When None, the previous frame is reused (snake keeps moving
                   but new LED-0 colours repeat the last analysis).
        """
        if frame is not None:
            self._last_frame = frame

        now = time.monotonic()
        elapsed_ms = (now - self._last_tick_time) * 1000.0

        if elapsed_ms >= self.tick_interval_ms:
            self._tick()
            # Advance by exactly one interval to keep ticks phase-accurate
            # rather than resetting to `now` (which would drift over time).
            self._last_tick_time += self.tick_interval_ms / 1000.0

    def get_strips(self) -> list[list[RGB]]:
        """Return a snapshot of all strip states as plain lists.

        Returns a copy so the renderer can iterate safely without holding
        any reference to the internal deques.

        Returns:
            List of NUM_STRIPS lists, each containing LEDS_PER_STRIP RGB tuples.
        """
        return [list(strip) for strip in self._strips]

    def set_bpm(self, bpm: float) -> None:
        """Update the BPM and reset the tick timer to avoid a spurious tick.

        Args:
            bpm: New BPM value. Clamped to [MIN_BPM, MAX_BPM].
        """
        self.bpm = max(config.MIN_BPM, min(bpm, config.MAX_BPM))
        # Reset timer so the next tick fires one full interval from *now*,
        # not from when the old BPM was set.
        self._last_tick_time = time.monotonic()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        """Propagate all strips by one step and inject a new LED-0 colour.

        For each strip:
            1. Compute the new LED-0 colour from the current audio analysis.
            2. appendleft() pushes it onto the front of the deque.
               The deque's maxlen automatically drops the last element —
               no explicit shift needed.
        """
        for band_index, strip in enumerate(self._strips):
            band_analysis = (
                self._last_frame.bands[band_index]
                if self._last_frame is not None
                else None
            )

            # Generate the new head colour for this strip.
            new_color: RGB = (
                self._mapper.map(band_index, band_analysis)
                if band_analysis is not None
                else (0, 0, 0)  # silence → black
            )

            # appendleft is O(1) and implicitly shifts the whole snake.
            strip.appendleft(new_color)
