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

- High-Performance Screen Capture: DirectX desktop duplication API for minimal latency
- GPU-Accelerated Detection: OpenCV with CUDA support for real-time target detection
- Adaptive Resource Management: Dynamic CPU/GPU utilization based on system load
- Real-time Overlay: Tkinter-based overlay with performance metrics and controls
- Configuration Hot-Reload: Live configuration updates without restart
- Python 3.13 Optimized: Leverages new multiprocessing and GIL improvements

## Usage 
_Windows_
1. within IDE's terminal create a virtual environment `python -m venv venv`
2. activate the virtual environment with `venv\Scripts\activate` , should show `(venv)` if not try killing the terminal and opening a new one
3. launch main locally
   1. install dependencies , `pip install -r requirements.txt`
   2.  `python src/main.py` to launch main application


_macOS_
1. within IDE's terminal create a virtual environment with `python3 -m venv venv`
2. activate the virtual environment with `source venv/bin/activate` , should show `(venv)` if not try killing the terminal and opening a new one
3. launch main locally
   1. install dependencies , `python3 -m pip install -r requirements.txt`
   2.  `python3 src/main.py` to launch main application

## Configuration
- config/default.yaml: Main application settings
- config/performance.yaml: Performance and optimization settings

## Project-Structure
PewPy/
- logs/
- src/
   - core/
      - `__init__.py`
      - `app_manager.py`
      - `frame_pipeline.py`
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