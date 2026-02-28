# PewPy

A high-performance, low-latency aimbot application written in Python 3.13, leveraging modern multiprocessing and multithreading for optimal performance. Features real-time screen capture, GPU-accelerated target detection, and adaptive resource management.

## Table of Contents
- [Introduction](#introduction)
- [Features](#features)
- [Usage](#usage)
- [Configuration](#Configuration)
- [Project-Structure](#Project-Structure)
- [Additional-Information](#Additional-Info)

## Introduction

PewPy is a sophisticated aimbot application built with Python 3.13, designed for maximum performance through advanced concurrency patterns and GPU acceleration. The application uses DirectX screen capture, OpenCV-based target detection, and low-latency input control to provide precise aiming assistance.

## Features

- **High-Performance Screen Capture**: DirectX desktop duplication (dxcam) for minimal latency.
- **GPU-Accelerated Detection**: OpenCV with CUDA support.
- **Adaptive Resource Management**: Dynamically adjusts capture FPS based on CPU load.
- **Python 3.13 No‑GIL Support**: Automatically detects free-threaded builds and optimizes execution.
- **Modular Concurrency**: Pluggable executors (thread/process) for CPU‑bound stages.
- **Configuration Hot-Reload**: YAML-based settings with live updates.

## Usage 

_Windows_
1. git clone repo & cd in
2. create virtual environment `python -m venv venv`
3. activate the virtual environment with `venv\Scripts\activate` , should show `(venv)` if not try killing the terminal and opening a new one
   - upgrade pip (good practice) `python -m pip install --upgrade pip`
   - install dependencies `pip install -r requirements.txt`
   - verify python has `--disable-gil` (experimental free‑threaded mode) important for the project , check with `python -c "import sys; print('t' in sys.abiflags)"` should print `True` if current Python supports parallel threading without GIL
      - In the instance of `False` (solution here)
4. Run the application `python src/main.py`

_macOS_
1. within IDE's terminal create a virtual environment with `python3 -m venv venv`
2. activate the virtual environment with `source venv/bin/activate` , should show `(venv)` if not try killing the terminal and opening a new one
3. launch main locally
   1. install dependencies , `python3 -m pip install -r requirements.txt`
   2.  `python3 src/main.py` to launch main application

## Configuration

- `config/default.yaml` – Main application settings.
- `config/performance.yaml` – User overrides (optional).

## Project-Structure
PewPy/
- logs/
- src/
   - core/
      - `__init__.py`
      - `app_manager.py`
      - `config.py.py`
      - `executors.py.py`
      - `frame_pipeline.py`
      - `resource_manager.py.py`
      - `thread_manager.py`
   - ui/
      - `__init__.py`
      - `main_window.py`
   - utils/
      - `__init__.py`
      - `system_utils.py`
   - workers/
      - `__init__.py`
      - `aimbot.py`
      - `auto_clicker.py`
      - `function_worker.py`
      - `overlay.py`
      - `screen_capturer.py`
      - `target_detector.py`
   - `main.py`
- `.gitignore`
- `ReadMe.md`
- `requirements.txt`
- `setup.py`

## Additional-Info

This portion is for logging or storing notes relevent to the project and its scope.