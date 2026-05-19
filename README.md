# PewPy

A high‑performance, low‑latency aimbot application written in Python 3.13, leveraging modern multiprocessing and multithreading for optimal performance. Features real‑time screen capture, GPU‑accelerated target detection, and adaptive resource management.

---

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Project Structure](#project-structure)
- [Usage](#usage)
- [Configuration](#configuration)
- [Additional Information](#additional-information)

---

## Introduction

PewPy is a modular desktop utility built around three core workers:

- **Overlay** – A transparent, click‑through info panel (tkinter).
- **Auto‑Clicker** – Configurable mouse automation.
- **Aimbot** – Real‑time screen capture + GPU‑accelerated target detection + smooth mouse control.

All workers can be toggled on/off independently through a modern `customtkinter` UI. The application dynamically adapts resource usage (FPS, thread pools) based on system load, making it suitable for low‑end hardware as well as high‑end rigs.

---

## Features

- **High‑Performance Screen Capture** – DirectX desktop duplication via `dxcam` for minimal latency.
- **GPU‑Accelerated Detection** – OpenCV with CUDA fallback to CPU when no GPU is available.
- **Adaptive Resource Manager** – Monitors CPU usage and automatically lowers capture FPS to maintain system responsiveness.
- **Python 3.13 No‑GIL Compatible** – Detects free‑threaded builds and optimises execution.
- **Modular Concurrency** – Pluggable executors (thread/process) for CPU‑bound pipeline stages.
- **Configuration Hot‑Reload** – YAML‑based settings with live updates.
- **Clean CustomTkinter UI** – Three‑tab interface with status updates and real‑time control.

---

## Project Structure

```bash
├── config/
│   ├── default.yaml               # core application settings
│   └── performance.yaml           # user‑override / performance tuning
├── docs/
│   └── ToDo.md
├── logs/                          # runtime logs (not tracked)
├── pewpy/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── app_manager.py         # worker coordination + lifecycle
│   │   ├── config.py              # YAML loader with dot‑notation access
│   │   ├── executors.py           # abstract thread/process executor backends
│   │   ├── frame_pipeline.py      # frame processing chain (optional parallelism)
│   │   ├── resource_manager.py    # adaptive CPU/FPS controller
│   │   └── thread_manager.py      # thread lifecycle with stop/pause events
│   ├── ui/
│   │   ├── tabs/
│   │   │   ├── __init__.py
│   │   │   ├── aimbot_tab.py       # Aimbot controls (toggle, HSV, smooth, activation key)
│   │   │   ├── general_tab.py      # Title, placeholders, global status bar
│   │   │   ├── mouse_tab.py        # Auto‑clicker toggle, interval, placeholders
│   │   │   └── overlays_tab.py     # Stats & screen overlay toggles
│   │   ├── utils.py                # shared UI helpers (centered frame)
│   │   ├── __init__.py
│   │   └── main_window.py          # tab container, UI update loop, shutdown
│   ├── utils/
│   │   ├── __init__.py
│   │   └── system_utils.py         # platform checks, priority optimisation
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── aimbot.py               # capture + detect + mouse movement
│   │   ├── auto_clicker.py         # pynput‑based auto‑clicker
│   │   ├── function_worker.py      # abstract worker base class
│   │   ├── overlay.py              # tkinter overlay window
│   │   ├── screen_capturer.py      # dxcam screen capture wrapper
│   │   ├── screen_overlay.py       # full‑screen coloured overlay
│   │   └── target_detector.py      # OpenCV HSV detection (GPU/CPU)
│   ├── __init__.py
│   └── main.py                     # entry point (run with -m pewpy.main)
├── .gitignore
├── README.md                       # (you are here, hi!)
├── requirements.txt
└── setup.py
```

--- 

## Usage

1. **Clone & enter**
   ```bash
   git clone https://github.com/notnatedavis/PewPy1.git && cd PewPy1
   ```

2. **Create virtual environment & activate**
    ```bash
    python -m venv venv
    source venv/bin/activate        # Linux / macOS
        # or
    venv\Scripts\activate           # Windows
    ```

3. **Install dependencies**
    ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
    ```bash
    python -m pewpy.main
    ```

--- 

## Configuration

- `config/default.yaml` – Main settings: worker defaults, pipeline parameters, resource manager thresholds
- `config/performance.yaml` – (optional) User overrides. Merged on top of default.yaml at startup
- The `Config` class supports dot‑notation (`config.get("aimbot.target_fps")`) and a `reload()` method for hot‑reloading during runtime (currently requires manual call, update future)

--- 

## Additional-Information

This portion is for logging or storing notes relevent to the project and its scope. 

### Overlay Architecture

The overlay system (`pewpy/ui/overlays.py`) is completely decoupled from Tkinter. Each overlay is a native Win32 window created with `WS_EX_LAYERED` and `WS_EX_TOPMOST`. A single, shared window procedure handles all overlays: it returns `HTTRANSPARENT` for `WM_NCHITTEST` to guarantee click‑through behaviour, and it dispatches `WM_PAINT` to the respective overlay’s `_on_paint` method.  

Painting uses the standard `BeginPaint`/`EndPaint` cycle together with a GDI memory DC for flicker‑free double‑buffering. All GDI resources are correctly released, and any painting exception is caught and logged without crashing the message pump.  

The pointer‑sized types `WPARAM_T`/`LPARAM_T` are defined explicitly to prevent `OverflowError` on 64‑bit systems, and `DefWindowProcW.argtypes` is set accordingly. The result is a robust, visually clean overlay that never blocks mouse input and remains stable regardless of how often it is shown or hidden.