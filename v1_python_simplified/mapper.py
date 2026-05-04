"""
mapper.py — LuminaSnake V1

Converts per-band audio analysis (amplitude + dominant frequency) into RGB
colours for the LED strips.

Colour model:
    We work in HSV (Hue, Saturation, Value) because it maps cleanly to the
    perceptual properties of the audio signal:
        - Hue        ← dominant frequency within the band (gradient across band range)
        - Saturation ← fixed at 1.0 for maximum vividness (could be modulated later)
        - Value      ← amplitude (volume) of the band after AGC

    HSV is then converted to RGB for Pygame rendering.
"""

from __future__ import annotations

import colorsys

import config
from audio_analyzer import BandAnalysis

# Type alias — keeping it local avoids circular imports with snake_engine.
RGB = tuple[int, int, int]


class Mapper:
    """Converts BandAnalysis objects into 8-bit RGB tuples.

    One Mapper instance is shared by the SnakeEngine for all strips.
    The class is stateless — map() is a pure function of its inputs.

    Example:
        mapper = Mapper()
        rgb = mapper.map(band_index=0, analysis=BandAnalysis(0.8, 120.0))
    """

    def map(self, band_index: int, analysis: BandAnalysis) -> RGB:
        """Map a single band analysis to an RGB colour.

        Args:
            band_index: Index into config.FREQUENCY_BANDS (0–3).
            analysis:   BandAnalysis containing amplitude and dominant_hz.

        Returns:
            An (R, G, B) tuple with each channel in [0, 255].
        """
        band = config.FREQUENCY_BANDS[band_index]

        # --- Hue: where in the band's hue range does the dominant freq fall? ---
        # We linearly interpolate between hue_min and hue_max based on how high
        # the dominant frequency is within [band.low_hz, band.high_hz].
        freq_norm = _normalise(
            analysis.dominant_hz,
            lo=band.low_hz,
            hi=band.high_hz,
        )
        hue = band.hue_min + freq_norm * (band.hue_max - band.hue_min)

        # --- Saturation: full (1.0) for vivid colours ---
        # At very low amplitudes we desaturate slightly toward grey so that
        # near-silence doesn't produce a faint but fully-saturated colour.
        saturation = 0.6 + 0.4 * analysis.amplitude  # range [0.6, 1.0]

        # --- Value: direct amplitude mapping ---
        # Soft-clamp with a small gamma to bring out mid-range levels.
        value = analysis.amplitude ** 0.7  # gamma < 1 brightens mid-range

        # --- Convert HSV → RGB (colorsys returns floats in [0, 1]) ---
        r_f, g_f, b_f = colorsys.hsv_to_rgb(hue, saturation, value)

        return (int(r_f * 255), int(g_f * 255), int(b_f * 255))


# ---------------------------------------------------------------------------
# Module-level helper
# ---------------------------------------------------------------------------

def _normalise(value: float, lo: float, hi: float) -> float:
    """Linearly map *value* from [lo, hi] to [0.0, 1.0], clamped.

    Args:
        value: Input value to normalise.
        lo:    Lower bound of the input range.
        hi:    Upper bound of the input range.

    Returns:
        Normalised float in [0.0, 1.0].
    """
    if hi <= lo:
        return 0.0
    return max(0.0, min((value - lo) / (hi - lo), 1.0))
