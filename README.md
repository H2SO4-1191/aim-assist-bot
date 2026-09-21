# Aim Assist Bot

A real-time computer-vision aim-assist tool built as an accessibility project for FPS games.

## Overview

Aim Assist Bot is a Python application that uses real-time object detection to help a player track and aim at on-screen targets. It was built as an assistive tool for a player with limited mobility, using screen capture and a YOLO-based detection model to identify players/enemies and smoothly guide the cursor toward them. The project is for personal/educational use only and is designed around offline and single-player modes rather than live competitive multiplayer.

## Features

- Real-time screen capture and object detection (player/head classes)
- Sticky target tracking with an engagement radius to avoid erratic target-switching
- Smooth, speed-capped cursor movement with a deceleration zone near the target
- Configurable assist strength, ADS-only mode, and global hotkeys (enable, ADS-only, strength, debug view)
- Lightweight control panel UI for toggling settings on the fly

## Tech Stack

- Core: Python, PyTorch, Ultralytics YOLO, OpenCV
- Capture: dxcam (Windows Desktop Duplication API)
- UI: Tkinter
- Input: Windows SendInput API (via ctypes), multiprocessing for jitter-free delivery
- Config: YAML

## Project Structure

```bash
aim-assist-bot/
├── src/            # Application source code (capture, detection, targeting, actuation, UI)
├── configs/        # config.yaml — capture, model, and targeting settings
├── models/         # Trained/downloaded YOLO weights (not tracked in git)
├── data/           # Training datasets (not tracked in git)
└── README.md
```

## Installation

- `git clone https://github.com/H2SO4-1191/aim-assist-bot.git`
- Create a virtual environment and install dependencies from `requirements.txt`
- Install the CUDA-matched build of PyTorch for your GPU
- Place a trained YOLO model in `models/` and update the path in `configs/config.yaml`
- Run `python src/main_app.py`

## Note

This project only moves the mouse toward detected on-screen targets — it does not read game memory, inject code, or attempt to bypass anti-cheat systems. It's intended for offline practice modes, bot matches, or single-player games, not live matches against other players.

## Author

H2SO4-1191 – Software Engineer
