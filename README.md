# LuminaSnake — Global Project Specifications

> **Last updated:** 2026-05  
> **Status:** V1 in progress — V2 through V6 planned (V3 optional)

---

## Table of Contents

1. [Project Vision](#1-project-vision)
2. [Architecture Decisions](#2-architecture-decisions)
3. [Hardware Stack](#3-hardware-stack)
4. [Audio Specification](#4-audio-specification)
5. [The Snake Algorithm](#5-the-snake-algorithm)
6. [Frequency Bands](#6-frequency-bands)
7. [Version Roadmap](#7-version-roadmap)
8. [Per-Version Specifications](#8-per-version-specifications)
9. [Development Environment](#9-development-environment)

---

## 1. Project Vision

**LuminaSnake** is a real-time audio visualiser that transforms a continuous microphone input into a dynamic light show across four LED strips.

The core visual effect is a **snake propagation**: at each tick, every LED inherits the colour of its left neighbour, and the head LED (index 0) is freshly generated from the current audio analysis. This creates a fluid, music-reactive stream of colour that flows along each strip.

Each strip is dedicated to a specific frequency band (Bass, Mids, High-Mids, Highs), so the visual output directly mirrors the spectral content of the audio in real time.

---

## 2. Architecture Decisions

This section documents key technical choices made during the project, including the reasoning behind them.

### 2.1 Language & Platform Evolution

| Phase | Platform | Language | Reason |
|-------|----------|----------|--------|
| Concept & algo validation | PC (macOS) | Python 3.13 | Fast iteration, rich audio/FFT libraries, no hardware required |
| Physical hardware target | STM32H750 | C / C++ | Obtained a STM32H750 Discovery Kit — better DSP, CMSIS-DSP, LTDC display |
| ESP32 | _(set aside)_ | — | Originally considered for WiFi + WS2812B RMT; replaced by STM32H750 once the kit was acquired |

> **Note:** ESP32 was initially set aside in favour of STM32H750, but is reintegrated from V2 onward as a **dedicated LED driver** (WS2812B via RMT peripheral), working alongside the STM32 rather than replacing it.

### 2.2 Why STM32H750 over ESP32

| Criterion | ESP32 | STM32H750 | Decision |
|-----------|-------|-----------|----------|
| CPU | Xtensa LX6 dual-core 240MHz | Cortex-M7 480MHz | ✅ STM32 |
| FPU | Basic | Double-precision + DSP instructions | ✅ STM32 |
| FFT library | Manual / ESP-DSP | CMSIS-DSP (ARM-optimised) | ✅ STM32 |
| WiFi | ✅ Native | ❌ Requires external module | ESP32 |
| WS2812B driving | ✅ RMT peripheral | Via TIM + DMA PWM | ESP32 |
| Display | SPI only (slow) | LTDC + DMA2D (fast, hardware-accelerated) | ✅ STM32 |
| Audio input quality | ADC noisy, I2S ok | SAI / I2S high quality | ✅ STM32 |
| Kit availability | — | ✅ STM32H750B-DK in hand | ✅ STM32 |

**Conclusion:** STM32H750 wins on raw compute, audio quality, and display capability. The lack of native WiFi is acceptable since the system is designed to be standalone from V2 onward.

### 2.3 Microphone Choice: INMP441

The INMP441 is an I2S MEMS digital microphone selected for the following reasons:

| Property | Value |
|----------|-------|
| Interface | I2S (digital — no ADC noise) |
| Frequency response | 60 Hz – 15 kHz (±3 dB) |
| SNR | 61 dB |
| Sensitivity | −26 dBFS |
| Supply voltage | 1.8 – 3.3V |

The flat frequency response from 60 Hz ensures that bass frequencies are captured faithfully — a known weakness of laptop built-in microphones (used temporarily during V1 testing).

### 2.4 Why Python for V1

- Numpy FFT and PyAudio allow the full audio pipeline to be prototyped in hours.
- Pygame provides an immediate visual feedback loop without any hardware setup.
- The modular architecture (AudioAnalyzer / SnakeEngine / Mapper / Display) maps directly to the C modules that will be written for V2, making the Python code a functional specification rather than throwaway work.
- Abstract base classes (`BaseRenderer`) were written from day one to anticipate the renderer swap in V2+.

---

## 3. Hardware Stack

### V1 (PC simulation)

| Component | Detail |
|-----------|--------|
| Host machine | MacBook Air M1 (2020) |
| Microphone | Built-in laptop mic _(temporary — limited bass response below ~200Hz)_ |
| Audio source (testing) | iPhone 13 speaker, ~5–10 cm from mic |
| Display | Pygame window (virtual LEDs) |

### V2+ (Embedded)

| Component | Detail |
|-----------|--------|
| MCU board | STM32H750B Discovery Kit |
| MCU | STM32H750VBT6 — Cortex-M7 @ 480MHz |
| RAM | 1MB SRAM + 16MB SDRAM (on-board) |
| Flash | 128KB internal + 16MB QSPI NOR Flash |
| Display | On-board 4" TFT LCD (480×272) via LTDC + DMA2D |
| Microphone | INMP441 (I2S MEMS) |
| LED driver | ESP32 (dedicated) — receives RGB frames from STM32 via UART/SPI, drives WS2812B via RMT peripheral |
| LED strips | 4× WS2812B strips, 60 LEDs each |
| Dev environment | VS Code + PlatformIO |

> **V3 optional only — additional audio I/O:**
>
> | Component | Detail |
> |-----------|--------|
> | Audio input | 3.5mm line-in jack → WM8994 codec (on-board STM32H750B-DK) |
> | Audio output | 3.5mm line-out → WM8994 codec → powered speakers |
> | Codec interface | I2S via SAI peripheral + DMA |

---

## 4. Audio Specification

| Parameter | Value |
|-----------|-------|
| Sample rate | 44 100 Hz |
| Channels | Mono |
| Bit depth | 16-bit signed integer (int16) |
| Chunk size | 1 024 samples (~23ms per frame) |
| FFT type | Real FFT (numpy.fft.rfft / CMSIS-DSP arm_rfft) |
| Window function | Hanning (applied before FFT to reduce spectral leakage) |
| Capture mode | Non-blocking callback (PortAudio thread in V1, SAI DMA in V2+) |

### Auto-Gain Control (AGC)

The AGC normalises amplitude to [0.0, 1.0] so that the LED strips remain reactive at any input volume level.

| Parameter | Value | Effect |
|-----------|-------|--------|
| Attack | 0.1 | Peak estimate rises quickly when signal is loud |
| Decay | 0.005 | Peak estimate falls slowly during quiet passages |
| Floor | 1×10⁻⁸ | Prevents division by zero on silence |

The asymmetric attack/decay prevents the gain from "pumping" during brief silent gaps while still reacting dynamically to loud transients.

---

## 5. The Snake Algorithm

```
At each tick:
    for each strip:
        strip[i] ← strip[i-1]    for i in [1, N_LEDS)
        strip[0] ← map(audio_analysis)
```

- **Implementation:** `collections.deque(maxlen=60)` + `appendleft()` — O(1), no explicit shift loop.
- **Tick rate:** driven by BPM × multiplier, completely decoupled from the display framerate.
- **Default multiplier:** ×8 (8 ticks per beat → 16 ticks/sec at 120 BPM → ~62.5ms per tick).

### Colour Generation (LED 0)

| HSV channel | Source | Notes |
|-------------|--------|-------|
| **Hue** | Dominant frequency within the band | Linearly interpolated across the band's hue range |
| **Saturation** | Amplitude | `0.6 + 0.4 × amplitude` — desaturates toward grey at low levels |
| **Value** | Amplitude | `amplitude ^ 0.7` — gamma < 1 brightens mid-range levels |

---

## 6. Frequency Bands

| # | Name | Range | Hue range (HSV) | Perceived colour |
|---|------|-------|-----------------|-----------------|
| 0 | Bass | 20 – 250 Hz | 0.62 – 0.72 | Deep blue |
| 1 | Mids | 250 – 2 000 Hz | 0.75 – 0.90 | Violet / Magenta |
| 2 | High-Mids | 2 000 – 6 000 Hz | 0.40 – 0.55 | Green / Cyan |
| 3 | Highs | 6 000 – 20 000 Hz | 0.45 – 0.52 | Turquoise / White |

> **Note on Bass in V1:** The built-in laptop microphone and iPhone 13 speaker both roll off significantly below ~200Hz, causing weak bass response during PC testing. This is a hardware limitation that disappears with the INMP441 in V2.

---

## 7. Version Roadmap

| Version | Name | Platform | Language | Status |
|---------|------|----------|----------|--------|
| **V1** | Python Simulation | PC (macOS) | Python 3.13 | 🟡 In progress |
| **V2** | STM32 + ESP32 Embedded | STM32H750B-DK + ESP32 | C | 🔵 Planned |
| **V3** _(optional)_ | A/V Sync — Latency Compensation | STM32H750B-DK + ESP32 | C | 🔵 Planned |
| **V4** | Automatic BPM Detection | STM32H750B-DK + ESP32 | C | 🔵 Planned |
| **V5** | AI Source Separation (Stemming) | PC + STM32 + ESP32 | Python + C | 🔵 Planned |
| **V6** | Fully Autonomous Embedded System | STM32H750B-DK + ESP32 | C | 🔵 Planned |

---

## 8. Per-Version Specifications

### V1 — Python Simulation
**Goal:** Validate the full audio→visual pipeline on PC with virtual LEDs.

| Item | Detail |
|------|--------|
| Status | 🟡 In progress |
| Platform | macOS / PC |
| Language | Python 3.13 |
| Dependencies | `numpy`, `pyaudio`, `pygame`, `scipy` |
| Display | Pygame window — 4 strips × 60 virtual LED circles |
| Audio input | System microphone (PyAudio callback) |
| Framerate | 60 FPS (Pygame) — independent of tick rate |
| Tick rate | BPM × 8 multiplier (default 120 BPM → ~16 ticks/sec) |
| BPM control | In-window text input + Validate button |
| Live metrics | Amplitude / AGC peak displayed per band label |

**Module structure:**

| File | Role |
|------|------|
| `config.py` | All global constants — single source of truth |
| `audio_analyzer.py` | PyAudio capture, Hanning window, FFT, AGC |
| `snake_engine.py` | deque buffers, tick management, snake propagation |
| `mapper.py` | (amplitude, dominant_hz) → HSV → RGB |
| `display.py` | `BaseRenderer` ABC + `PygameRenderer` implementation |
| `main.py` | Entry point — wires all modules, main loop |

**Key design choices for V2 compatibility:**
- `BaseRenderer` ABC allows swapping Pygame for any output (LTDC, UART, etc.) without touching the engine.
- All constants in `config.py` map directly to `#define` / `const` in future C code.
- Module boundaries (Analyzer / Engine / Mapper / Display) will become C translation units in V2.

---

### V2 — STM32 + ESP32 Embedded
**Goal:** Port the full pipeline to hardware. STM32H750 handles all compute; ESP32 drives the WS2812B strips via its RMT peripheral.

| Item | Detail |
|------|--------|
| Status | 🔵 Planned |
| Platform | STM32H750B-DK + ESP32 |
| Language | C (C99 or C11) |
| Toolchain | VS Code + PlatformIO |
| Audio input | INMP441 → SAI peripheral + DMA |
| FFT | CMSIS-DSP `arm_rfft_fast_f32` |
| AGC | Ported from Python — same asymmetric attack/decay logic |
| LED output | STM32 → UART/SPI → ESP32 → WS2812B (RMT peripheral) |
| Display | STM32H750B-DK on-board 4" TFT (LTDC + DMA2D) |
| BPM control | On-board buttons or touchscreen (TBD) |

**STM32 / ESP32 role split:**

| Responsibility | STM32H750 | ESP32 |
|----------------|-----------|-------|
| Audio capture | ✅ SAI + DMA | ❌ |
| FFT + AGC | ✅ CMSIS-DSP | ❌ |
| Snake engine | ✅ | ❌ |
| Colour mapping | ✅ | ❌ |
| RGB frame transmission | ✅ sends | ✅ receives |
| WS2812B driving | ❌ | ✅ RMT peripheral |
| Display (debug) | ✅ LTDC | ❌ |

**V1 → V2 module mapping:**

| Python module | C equivalent |
|---------------|-------------|
| `audio_analyzer.py` | `audio_analyzer.c` — SAI DMA callback + CMSIS-DSP FFT |
| `snake_engine.py` | `snake_engine.c` — circular buffer + TIM tick interrupt |
| `mapper.py` | `mapper.c` — integer HSV→RGB, lookup tables for speed |
| `display.py` | `display.c` — LTDC framebuffer writes + DMA2D fills |
| `config.py` | `config.h` — `#define` constants |

---

### V3 _(optional)_ — A/V Sync: Latency Compensation
**Goal:** Achieve perfect synchronisation between LED display and audio playback by introducing a calibrated audio delay that matches the LED processing latency.

> ⚠️ This version is **optional** and independent from V4–V6. Its features do not carry over — V4+ continues from V2's architecture.

**Concept:** The STM32 processes the incoming audio and generates LED frames. By the time a frame reaches the LEDs (FFT + snake engine + UART transfer + ESP32 RMT), a measurable latency has accumulated (~20–50ms). This version buffers the audio by exactly that delay before playing it back, so the sound and the light are perceived as perfectly simultaneous.

```
3.5mm line-in → WM8994 codec (I2S in)
                      │
                      ▼
              STM32H750 — audio buffer (circular, N ms deep)
                      │
          ┌───────────┴────────────┐
          ▼                        ▼
    FFT + Snake Engine       Audio delay buffer
    → RGB frames                   │ (delay = measured LED latency)
          │                        │
          ▼                        ▼
   UART/SPI → ESP32          WM8994 codec (I2S out)
   → WS2812B (RMT)           → powered speakers
          │                        │
          └──────── sync ──────────┘
               (same timestamp)
```

| Item | Detail |
|------|--------|
| Status | 🔵 Planned (optional) |
| Platform | STM32H750B-DK + ESP32 |
| Language | C |
| Audio input | 3.5mm line-in → WM8994 codec (on-board) via SAI + DMA |
| Audio output | WM8994 codec → 3.5mm line-out → powered speakers |
| Delay mechanism | Circular audio buffer in SDRAM — depth = measured pipeline latency |
| Latency measurement | One-time calibration at startup (or hardcoded after measurement) |
| Sync mechanism | LED frame and audio chunk share the same timestamp counter |
| Microphone | Not used in this version — line-in replaces INMP441 |

**Why line-in instead of INMP441:**
The INMP441 introduces its own capture latency and cannot reproduce the original audio signal for playback. A line-in source (phone, PC, instrument) provides a clean copy of the audio that can be both analysed and played back with a controlled delay.

---

### V4 — Automatic BPM Detection
**Goal:** Remove manual BPM input — detect tempo from the audio signal directly.

| Item | Detail |
|------|--------|
| Status | 🔵 Planned |
| Platform | STM32H750B-DK + ESP32 |
| Language | C |
| Approach | Onset detection (energy flux) + inter-onset interval histogram |
| Input | Same audio pipeline as V2 (INMP441) |
| Output | Auto-updated `tick_rate` fed into the snake engine |
| Fallback | Manual BPM override retained as a backup |

---

### V5 — AI Source Separation (Stemming)
**Goal:** Use AI to separate audio into stems (drums, bass, vocals, other) before analysis, for cleaner per-band reactivity.

| Item | Detail |
|------|--------|
| Status | 🔵 Planned |
| Platform | PC (preprocessing) + STM32H750B-DK + ESP32 |
| Language | Python (PC) + C (embedded) |
| Libraries | Spleeter or Demucs (PC-side) |
| Architecture | PC runs stemming in real time → sends separated stems over USB/UART to STM32 |
| Constraint | Too computationally heavy for STM32 — stays on PC |

---

### V6 — Fully Autonomous Embedded System
**Goal:** The system runs entirely standalone — no PC required.

| Item | Detail |
|------|--------|
| Status | 🔵 Planned |
| Platform | STM32H750B-DK + ESP32 |
| Language | C |
| Audio | INMP441 → SAI DMA → on-chip FFT |
| BPM | Auto-detection from V4 |
| LED output | ESP32 → WS2812B (RMT) |
| Display | Optional — on-board TFT for status/debug |
| Power | USB or 5V DC barrel jack |
| No PC dependency | All processing on-chip |

---

## 9. Development Environment

| Tool | Purpose | Version |
|------|---------|---------|
| VS Code | Primary editor | Latest |
| PlatformIO | Embedded build system (V2+) | Latest |
| Python | V1 runtime | 3.13+ |
| uv | Python package & venv manager | Latest |
| numpy | FFT + array math (V1) | ≥1.26 |
| pyaudio | Microphone capture (V1) | ≥0.2.14 |
| pygame | Visual simulation (V1) | ≥2.5 |
| CMSIS-DSP | ARM-optimised DSP library (V2+) | Bundled with STM32Cube |
| STM32CubeMX | Pin/clock config code generation (V2+) | Latest |

### Repository Structure (target)

```
lumina_snake/
├── specs.md                      ← this file
├── copilot-instructions.md       ← AI assistant guidelines
├── agents.md                     ← V1 mission brief
│
├── v1_python/                    ← V1 source
│   ├── config.py
│   ├── audio_analyzer.py
│   ├── snake_engine.py
│   ├── mapper.py
│   ├── display.py
│   ├── main.py
│   └── requirements.txt
│
├── v2_stm32/                     ← V2+ source (STM32 side)
│   ├── src/
│   │   ├── config.h
│   │   ├── audio_analyzer.c / .h
│   │   ├── snake_engine.c / .h
│   │   ├── mapper.c / .h
│   │   └── display.c / .h
│   └── platformio.ini
│
├── v2_esp32/                     ← V2+ source (ESP32 LED driver side)
│   ├── src/
│   │   ├── main.c
│   │   └── led_driver.c / .h    ← WS2812B via RMT
│   └── platformio.ini
│
└── v3_optional_avsync/           ← V3 optional — A/V sync (isolated)
    └── src/
        └── audio_buffer.c / .h  ← circular delay buffer
```