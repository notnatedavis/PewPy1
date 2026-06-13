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
PewPy/
├── config/
│   ├── default.yaml   # core application settings
│   └── performance.yaml   # user‑override / performance tuning
├── docs/
│   └── ToDo.md
├── logs/   # runtime logs (not tracked)
├── pewpy/
│   ├── capture/
│   │   ├── __init__.py
│   │   └── dxcam_capturer.py
│   ├── common/
│   │   ├── __init__.py
│   │   ├── constants.py
│   │   └── types.py
│   ├── communication/
│   │   ├── __init__.py
│   │   └── overlay_bridge.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── application.py
│   │   ├── config.py
│   │   ├── executors.py
│   │   ├── resource_manager.py
│   │   └── thread_manager.py
│   ├── detection/
│   │   ├── __init__.py
│   │   └── target_detector.py
│   ├── pipeline/
│   │   ├── __init__.py
│   │   └── frame_pipeline.py
│   ├── ui/
│   │   ├── overlays/
│   │   │   ├── __init__.py
│   │   │   ├── base_overlay.py
│   │   │   ├── mask_overlay.py
│   │   │   ├── screen_overlay.py
│   │   │   ├── stats_overlay.py
│   │   │   └── win32_helpers.py
│   │   ├── tabs/
│   │   │   ├── __init__.py
│   │   │   ├── aimbot_tab.py
│   │   │   ├── base_tab.py
│   │   │   ├── debug_window.py
│   │   │   ├── general_tab.py
│   │   │   ├── mouse_tab.py
│   │   │   └── overlays_tab.py
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   └── utils.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── color.py
│   │   ├── logging_setup.py
│   │   └── platform.py
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── aimbot.py
│   │   ├── auto_clicker.py
│   │   └── base.py
│   ├── __init__.py
│   └── main.py
├── .gitignore
├── README.md   # (you are here, hi!)
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