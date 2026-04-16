"""
Global configuration for LuminaSnake V1.

All tunable constants live here. No magic numbers elsewhere.
"""

# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------

SAMPLE_RATE: int = 44100        # Hz — 44.1 kHz is the standard CD-quality rate
CHANNELS: int = 1               # Mono capture — we don't need stereo for spectrum analysis
CHUNK_SIZE: int = 1024          # Samples per PyAudio callback frame.
                                # 1024 @ 44100 Hz ≈ 23 ms of audio per frame.
                                # Lower = more responsive but more CPU overhead.
AUDIO_FORMAT: int = 8           # pyaudio.paInt16 = 16-bit signed integers (value = 8)
                                # Defined here as a raw int to avoid importing pyaudio
                                # in config (keeps this file dependency-free).

# ---------------------------------------------------------------------------
# Frequency bands
# Each band is a (low_hz, high_hz, label, hue_range) tuple.
# hue_range: (min_hue, max_hue) in [0.0, 1.0] for HSV colour mapping.
# ---------------------------------------------------------------------------

from dataclasses import dataclass


@dataclass(frozen=True)
class FrequencyBand:
    """Immutable descriptor for a single frequency band.

    Attributes:
        label:     Human-readable name of the band.
        low_hz:    Lower bound of the frequency range (inclusive).
        high_hz:   Upper bound of the frequency range (inclusive).
        hue_min:   Minimum HSV hue for this band (0.0 = red, 0.667 = blue).
        hue_max:   Maximum HSV hue for this band.
    """
    label:   str
    low_hz:  float
    high_hz: float
    hue_min: float
    hue_max: float


# The four bands, ordered low → high frequency.
# Hue values follow the colour spec from copilot-instructions:
#   Bass      → deep blue / red    (hue wraps: 0.60–0.70 and 0.95–1.0)
#   Mids      → violet / magenta   (0.75–0.90)
#   High-Mids → green / cyan       (0.40–0.55)
#   Highs     → turquoise / white  (0.45–0.55, high saturation → low)
FREQUENCY_BANDS: tuple[FrequencyBand, ...] = (
    FrequencyBand("Bass",      20.0,    250.0,  0.62, 0.72),
    FrequencyBand("Mids",      250.0,  2000.0,  0.75, 0.90),
    FrequencyBand("High-Mids", 2000.0, 6000.0,  0.40, 0.55),
    FrequencyBand("Highs",     6000.0, 20000.0, 0.45, 0.52),
)

# ---------------------------------------------------------------------------
# LED strips
# ---------------------------------------------------------------------------

NUM_STRIPS: int = len(FREQUENCY_BANDS)   # One strip per frequency band (= 4)
LEDS_PER_STRIP: int = 60                 # Number of virtual LEDs per strip

# ---------------------------------------------------------------------------
# Snake / BPM
# ---------------------------------------------------------------------------

DEFAULT_BPM: float = 120.0          # Initial BPM on startup
BPM_MULTIPLIER: float = 1.0         # Tick subdivisions (1.0 = 1 tick per beat)
MIN_BPM: float = 20.0               # Guard against division by zero / absurd values
MAX_BPM: float = 300.0

# ---------------------------------------------------------------------------
# AGC (Auto-Gain Control)
# ---------------------------------------------------------------------------

AGC_ATTACK: float = 0.1     # How fast the gain rises when signal is loud  (0–1)
AGC_DECAY: float = 0.005    # How fast the gain falls when signal is quiet  (0–1)
                             # Decay is intentionally slower than attack to avoid
                             # the gain pumping wildly during silent gaps.
AGC_MIN_ENERGY: float = 1e-8 # Floor to prevent division by zero on silence

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

FPS: int = 60                   # Pygame target framerate (independent of BPM tick)

LED_RADIUS: int = 8             # Pixel radius of each virtual LED circle
LED_SPACING: int = 20           # Centre-to-centre pixel distance between LEDs
STRIP_MARGIN_X: int = 20        # Left/right padding around the strip area
STRIP_MARGIN_Y: int = 60        # Top padding (space for the band label)
STRIP_GAP_Y: int = 80           # Vertical gap between consecutive strips

# Derived window dimensions — computed once from the constants above.
WINDOW_WIDTH: int  = STRIP_MARGIN_X * 2 + LEDS_PER_STRIP * LED_SPACING
WINDOW_HEIGHT: int = STRIP_MARGIN_Y + NUM_STRIPS * STRIP_GAP_Y + 80  # +80 for BPM UI

BACKGROUND_COLOR: tuple[int, int, int] = (10, 10, 15)   # Near-black background
LABEL_COLOR: tuple[int, int, int]      = (180, 180, 180)
UI_COLOR: tuple[int, int, int]         = (220, 220, 220)
INPUT_BG_COLOR: tuple[int, int, int]   = (30, 30, 40)
INPUT_ACTIVE_COLOR: tuple[int, int, int] = (60, 60, 80)

FONT_SIZE_LABEL: int = 16
FONT_SIZE_UI: int = 18
