"""
main.py — LuminaSnake V1

Entry point. Wires AudioAnalyzer, SnakeEngine, and PygameRenderer together
into the main loop.

Loop structure:
    ┌─────────────────────────────────────────────────┐
    │  60 Hz Pygame loop                              │
    │  ┌────────────────────────────────────────────┐ │
    │  │ 1. handle_events() → check quit / new BPM  │ │
    │  │ 2. get_latest_frame() from AudioAnalyzer   │ │
    │  │ 3. engine.update(frame) → maybe tick snake │ │
    │  │ 4. renderer.render(strips)                 │ │
    │  └────────────────────────────────────────────┘ │
    └─────────────────────────────────────────────────┘

The audio capture runs on PortAudio's background thread (started by
AudioAnalyzer.start()) and is completely decoupled from the Pygame loop.
"""

from __future__ import annotations

import logging
import sys

from audio_analyzer import AudioAnalyzer
from display import PygameRenderer
from snake_engine import SnakeEngine

# Configure root logger — INFO level prints startup messages and warnings.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Initialise all subsystems and run the main loop until the user quits."""

    # --- Setup ---
    analyzer = AudioAnalyzer()
    engine   = SnakeEngine()
    renderer = PygameRenderer()

    try:
        analyzer.start()
    except RuntimeError as exc:
        logger.error("Could not start audio: %s", exc)
        logger.warning("Continuing without audio — snake will render silence colours.")
        # We deliberately don't exit: the visualiser still runs (useful for
        # testing the UI on a machine with no microphone).

    logger.info("LuminaSnake V1 started. Close the window or press Ctrl-C to quit.")

    # --- Main loop ---
    running = True
    while running:
        # 1. Process Pygame events (input, window close, BPM changes).
        events = renderer.handle_events()

        if events.get("quit"):
            running = False
            continue

        if "new_bpm" in events:
            engine.set_bpm(events["new_bpm"])
            logger.info("BPM updated to %.1f (tick interval = %.1f ms)",
                        engine.bpm, engine.tick_interval_ms)

        # 2. Fetch the latest audio frame (non-blocking — may be None).
        frame = analyzer.get_latest_frame()

        # 3. Advance the snake (ticks only when the BPM interval has elapsed).
        engine.update(frame)

        # 4. Render the current strip state.
        renderer.render(engine.get_strips())

    # --- Teardown ---
    logger.info("Shutting down...")
    analyzer.stop()
    renderer.teardown()
    sys.exit(0)


if __name__ == "__main__":
    main()
