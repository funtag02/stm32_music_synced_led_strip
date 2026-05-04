"""
display.py — LuminaSnake V1

Pygame-based renderer for the four virtual LED strips plus BPM input UI.

Architecture:
    BaseRenderer (ABC) defines the contract that any V2+ renderer must satisfy.
    PygameRenderer implements it for the V1 simulation.

    This separation means swapping Pygame for a UDP sender in V2 only requires:
        1. Writing a new class that inherits BaseRenderer.
        2. Passing it to main.py instead of PygameRenderer.
    Nothing else changes.

UI layout (per strip):
    ┌───────────────────────────────────────────────────┐
    │  [Band Label]                                      │
    │  ● ● ● ● ● ● ● ● … (60 LED circles)              │
    └───────────────────────────────────────────────────┘
    ┌─────────────────────────────────────┐
    │  BPM: [___120___]  [Valider]        │
    └─────────────────────────────────────┘
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pygame

import config

# Type alias — consistent with snake_engine.py
RGB = tuple[int, int, int]


# ---------------------------------------------------------------------------
# Abstract contract (V2-ready)
# ---------------------------------------------------------------------------

class BaseRenderer(ABC):
    """Abstract base class for all LuminaSnake renderers.

    Any class that visualises or transmits LED data must implement this
    interface. This allows main.py to be renderer-agnostic.
    """

    @abstractmethod
    def render(
        self,
        strips: list[list[RGB]],
        band_metrics: list[tuple[float, float]] | None = None,
    ) -> None:
        """Push the current strip state to the output (screen, UDP, serial…).

        Args:
            strips:       List of NUM_STRIPS lists, each with LEDS_PER_STRIP RGB tuples.
                          strips[0] = Bass strip, strips[3] = Highs strip.
                          Index 0 of each inner list = the "head" (newest) LED.
            band_metrics: Optional list of (amplitude, agc_peak) pairs, one per band.
                          Used by visual renderers to display live values next to labels.
        """
        ...

    @abstractmethod
    def handle_events(self) -> dict:
        """Process input events and return a dictionary of actions.

        Returns:
            A dict that may contain:
                "quit"     → bool  — True if the user requested to close.
                "new_bpm"  → float — A new BPM value if the user submitted one.
        """
        ...

    @abstractmethod
    def teardown(self) -> None:
        """Release any resources held by the renderer (window, socket, etc.)."""
        ...


# ---------------------------------------------------------------------------
# Pygame renderer
# ---------------------------------------------------------------------------

class PygameRenderer(BaseRenderer):
    """Renders the four LED strips and BPM input UI using Pygame.

    The renderer runs at config.FPS (60 Hz), completely independent of the
    snake's BPM tick rate. Pygame's clock.tick() handles frame pacing.

    Attributes:
        clock: Pygame Clock used to cap the framerate at config.FPS.
    """

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("LuminaSnake V1")

        self._screen = pygame.display.set_mode(
            (config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        )
        self.clock = pygame.time.Clock()

        # Font objects — loaded once to avoid per-frame overhead.
        self._font_label = pygame.font.SysFont("monospace", config.FONT_SIZE_LABEL)
        self._font_ui    = pygame.font.SysFont("monospace", config.FONT_SIZE_UI)

        # --- BPM input widget state ---
        self._bpm_text: str = str(int(config.DEFAULT_BPM))
        self._input_active: bool = False    # True when the text field is focused

        # Cached rectangles for hit-testing mouse clicks.
        self._input_rect  = pygame.Rect(0, 0, 0, 0)
        self._button_rect = pygame.Rect(0, 0, 0, 0)

        # Latest band metrics — updated each render call.
        self._band_metrics: list[tuple[float, float]] | None = None

    # ------------------------------------------------------------------
    # BaseRenderer implementation
    # ------------------------------------------------------------------

    def render(
        self,
        strips: list[list[RGB]],
        band_metrics: list[tuple[float, float]] | None = None,
    ) -> None:
        """Draw all strips and the BPM UI, then flip the display buffer.

        Args:
            strips:       Current LED state from SnakeEngine.get_strips().
            band_metrics: List of (amplitude, agc_peak) per band — displayed
                          next to each band label as "amp / peak".
        """
        self._band_metrics = band_metrics  # store for _draw_strips to consume
        self._screen.fill(config.BACKGROUND_COLOR)
        self._draw_strips(strips)
        self._draw_bpm_ui()
        pygame.display.flip()
        self.clock.tick(config.FPS)

    def handle_events(self) -> dict:
        """Process the Pygame event queue.

        Returns:
            Dict with optional keys "quit" (bool) and "new_bpm" (float).
        """
        result: dict = {}

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                result["quit"] = True

            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_mouse_click(event.pos, result)

            elif event.type == pygame.KEYDOWN and self._input_active:
                self._handle_key(event, result)

        return result

    def teardown(self) -> None:
        """Quit Pygame and release the display."""
        pygame.quit()

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def _draw_strips(self, strips: list[list[RGB]]) -> None:
        """Render all four LED strips onto the screen surface.

        Args:
            strips: Nested list of RGB tuples — strips[band][led_index].
        """
        for band_idx, (strip, band) in enumerate(
            zip(strips, config.FREQUENCY_BANDS)
        ):
            # Vertical centre of this strip's row.
            strip_y = config.STRIP_MARGIN_Y + band_idx * config.STRIP_GAP_Y

            # --- Band label + live amplitude/peak metric ---
            if self._band_metrics and band_idx < len(self._band_metrics):
                amp, peak = self._band_metrics[band_idx]
                # Format: "Bass — 0.73 / 1.00"  (amplitude / agc_peak normalised to 1)
                # We show peak as a raw float so the user can see AGC headroom.
                metric_str = f"{band.label} — {amp:.2f} / {peak:.2f}"
            else:
                metric_str = band.label

            label_surf = self._font_label.render(metric_str, True, config.LABEL_COLOR)
            self._screen.blit(label_surf, (config.STRIP_MARGIN_X, strip_y - 22))

            # Draw each LED as a filled circle.
            for led_idx, color in enumerate(strip):
                cx = config.STRIP_MARGIN_X + led_idx * config.LED_SPACING + config.LED_RADIUS
                cy = strip_y

                # Dim radius slightly for dark LEDs — visual depth effect.
                brightness = max(color) / 255.0
                radius = max(3, int(config.LED_RADIUS * (0.4 + 0.6 * brightness)))

                pygame.draw.circle(self._screen, color, (cx, cy), radius)

                # Subtle glow: a larger, semi-transparent circle underneath.
                # We achieve this with a second circle at 40% alpha.
                if brightness > 0.1:
                    glow_color = (
                        min(255, int(color[0] * 0.5)),
                        min(255, int(color[1] * 0.5)),
                        min(255, int(color[2] * 0.5)),
                    )
                    pygame.draw.circle(
                        self._screen, glow_color,
                        (cx, cy), radius + 3
                    )
                    # Re-draw the bright core on top of the glow.
                    pygame.draw.circle(self._screen, color, (cx, cy), radius)

    def _draw_bpm_ui(self) -> None:
        """Render the BPM text input field and the Validate button."""
        ui_y = config.STRIP_MARGIN_Y + config.NUM_STRIPS * config.STRIP_GAP_Y + 10

        # Label
        label = self._font_ui.render("BPM:", True, config.UI_COLOR)
        self._screen.blit(label, (config.STRIP_MARGIN_X, ui_y + 5))

        # Text input box
        input_x = config.STRIP_MARGIN_X + 70
        self._input_rect = pygame.Rect(input_x, ui_y, 100, 32)
        input_color = (
            config.INPUT_ACTIVE_COLOR if self._input_active else config.INPUT_BG_COLOR
        )
        pygame.draw.rect(self._screen, input_color, self._input_rect, border_radius=4)
        pygame.draw.rect(self._screen, config.UI_COLOR, self._input_rect, 1, border_radius=4)

        text_surf = self._font_ui.render(self._bpm_text, True, config.UI_COLOR)
        # Clip text rendering inside the input box with a small margin.
        self._screen.blit(text_surf, (input_x + 6, ui_y + 7))

        # Validate button
        btn_x = input_x + 110
        self._button_rect = pygame.Rect(btn_x, ui_y, 90, 32)
        pygame.draw.rect(self._screen, (50, 80, 50), self._button_rect, border_radius=4)
        pygame.draw.rect(self._screen, config.UI_COLOR, self._button_rect, 1, border_radius=4)
        btn_surf = self._font_ui.render("Valider", True, config.UI_COLOR)
        self._screen.blit(btn_surf, (btn_x + 8, ui_y + 7))

    # ------------------------------------------------------------------
    # Event sub-handlers
    # ------------------------------------------------------------------

    def _handle_mouse_click(self, pos: tuple[int, int], result: dict) -> None:
        """Toggle input focus or trigger BPM validation on mouse click.

        Args:
            pos:    (x, y) pixel coordinates of the click.
            result: Output dict — may be populated with "new_bpm".
        """
        if self._input_rect.collidepoint(pos):
            self._input_active = True
        elif self._button_rect.collidepoint(pos):
            self._submit_bpm(result)
        else:
            self._input_active = False

    def _handle_key(self, event: pygame.event.Event, result: dict) -> None:
        """Handle keyboard input while the BPM text field is focused.

        Args:
            event:  A pygame.KEYDOWN event.
            result: Output dict — may be populated with "new_bpm".
        """
        if event.key == pygame.K_RETURN:
            self._submit_bpm(result)
        elif event.key == pygame.K_BACKSPACE:
            self._bpm_text = self._bpm_text[:-1]
        elif event.unicode.isdigit() or (event.unicode == "." and "." not in self._bpm_text):
            # Allow digits and a single decimal point; cap input length.
            if len(self._bpm_text) < 6:
                self._bpm_text += event.unicode

    def _submit_bpm(self, result: dict) -> None:
        """Parse the current text field content and emit a new_bpm action.

        Args:
            result: Output dict populated with "new_bpm" on success.
        """
        try:
            bpm = float(self._bpm_text)
            # Clamp to valid range and round-trip through config guard.
            bpm = max(config.MIN_BPM, min(bpm, config.MAX_BPM))
            result["new_bpm"] = bpm
            self._bpm_text = str(int(bpm))  # normalise display
            self._input_active = False
        except ValueError:
            # User typed something non-numeric — reset to current default.
            self._bpm_text = str(int(config.DEFAULT_BPM))