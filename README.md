# PewPy

A high-performance, low-latency aimbot application written in Python 3.13, leveraging modern multiprocessing and multithreading for optimal performance. Features real-time screen capture, GPU-accelerated target detection, and adaptive resource management.

## Table of Contents
- [Introduction](#introduction)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#Installation)
- [Usage](#usage)
- [Configuration](#Configuration)
- [Project-Structure](#Project-Structure)
- [Additional-Information](#Additional-Info)

## Introduction

PewPy is a sophisticated aimbot application built with Python 3.13, designed for maximum performance through advanced concurrency patterns and GPU acceleration. The application uses DirectX screen capture, OpenCV-based target detection, and low-latency input control to provide precise aiming assistance.

### Order of Operations :  
1. **Initialization** : 
- Load configuration from YAML files
- Initialize DirectX screen capture
- Set up GPU-accelerated target detection
- Start safety monitoring and hotkey handlers
- Launch performance overlay

2. **Main Loop** : 
- Monitor safety state and hotkeys
- Capture screen frames at high FPS
- Process frames for target detection
- Calculate smooth mouse movements
- Update real-time performance statistics
- Apply adaptive resource optimization

## Features

- High-Performance Screen Capture: DirectX desktop duplication API for minimal latency
- GPU-Accelerated Detection: OpenCV with CUDA support for real-time target detection
- Adaptive Resource Management: Dynamic CPU/GPU utilization based on system load
- Real-time Overlay: Tkinter-based overlay with performance metrics and controls
- Safety First: Emergency stop hotkeys and comprehensive safety monitoring
- Configuration Hot-Reload: Live configuration updates without restart
- Python 3.13 Optimized: Leverages new multiprocessing and GIL improvements

## Prerequisites

_Asahi Linux (Fedora)_
- ...update

_Windows_
- Windows 10/11 (64-bit)
- Python 3.13=+
- NVIDIA GPU with CUDA support (optional, for GPU acceleration)
- DirectX 11 compatible graphics card

_MacOS_
- ...update

## Installation
1. clone the repo & cd in
2. run setup script `python setup.py`

## Usage 
1. launch with `python src/main.py`
2. Control with Hotkeys :
- F2 : Toggle on/off
- F10 : Emergency stop
- F12 : Graceful Exit
- Ctrl + Alt + O : Toggle overlay visibility
- Ctrl + Alt + P : Cycle performance modes
3. Moniter Performance with overlay

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
      - `thread_manager.py`
   - ui/
      - `__init__.py`
      - `main_window.py`
   - utils/
      - `__init__.py`
      - `system_utils.py`
   - workers/
      - `__init__.py`
      - `auto_clicker.py`
      - `function_worker.py`
   - `main.py`
- `.gitignore`
- `ReadMe.md`
- `requirements.txt`

## Additional-Info

This portion is for logging or storing notes relevent to the project and its scope.

## Current Focus (delete as I go)

Performance Optimizations

1. Capture Pipeline

- ROI cropping during texture mapping (avoid full-screen conversion)
- Direct BGRA→HSV conversion (eliminate intermediate BGR step)
- DXGI desktop duplication with partial framebuffer updates

2. Detection System

- Dynamic downscaling (adjust based on FPS: 0.5x → 0.8x)
- CUDA-accelerated contour detection (cv::cuda::findContours)
- Background subtraction for moving targets
- Temporal coherence (reuse previous frame's mask)

3. Input Pipeline

- Replace Sleep() with high-precision timers (std::chrono)
- Mouse movement prediction (linear extrapolation)
- Configurable smoothing curves (easing functions)

Core Features

1. Dynamic Targeting

- Kalman filtering for target trajectory prediction
- Multi-contour analysis (closest to crosshair, largest area)
- HSV range auto-calibration (F3 to sample target area)

2. Adaptive ROI

- ROI centering around last detection
- Dynamic sizing based on target velocity
- Manual ROI adjustment via config

3. Input Modes

- Raw input API support (for protected games)
- Absolute/relative mouse mode toggle
- Humanizer module (randomized movement curves) ?

Configuration & Usability

1. Config System

- INI/JSON configuration (color ranges, ROI, hotkeys, smoothing)
- Runtime reloading (F5 to refresh config)
- CLI argument parsing

2. Diagnostic UI

- DirectX overlay (ROI boundaries, target lock indicator)
- Performance metrics (FPS, processing time)
- Detection preview window (debug mode)

3. Calibration Tools

- HSV range tester with sliders
- ROI visual positioning tool
- Mouse sensitivity profiler

Code Quality & Maintenance

1. Platform Abstraction

- Interface classes for input/capture (enable Linux/Wine support)
- CMake options for CUDA/DirectX
- Error code standardization

2. Build System

- Fix target names (cAimbot vs AimTrainer)
- OpenCV CUDA conditional compilation
- CI/CD pipeline (GitHub Actions)

3. Testing

- Unit tests for coordinate transformations
- Capture simulation framework
- Performance benchmarking suite

Anti-Cheat Mitigations

1. Obfuscation

- Randomize window titles/class names
- DirectX hook masking
- Mouse event spoofing (hardware IDs)

2. Behavioral

- Variable activation delays
- "Human" jitter simulation
- Process hollowing techniques

Roadmap

Phase 1 (Stability): Resource leaks, thread safety, config system  
Phase 2 (Performance): CUDA optimization, pipeline refactoring  
Phase 3 (Features): Prediction algorithms, diagnostic UI  
Phase 4 (Stealth): Anti-cheat evasions, driver-level input  
