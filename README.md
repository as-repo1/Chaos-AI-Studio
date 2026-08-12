# Chaos AI Studio

Chaos AI Studio is a unified management dashboard for your local AI suite. It allows you to effortlessly start, stop, and monitor Text (Llama), Image (ComfyUI), Audio (MusicGen), and Voice (XTTS) AI systems from one modern web interface.

It was custom-built to automatically enforce a 4GB VRAM limit (Intel Arc A370M) to prevent Out of Memory crashes when trying to run multiple heavy models at once.

## Migration Guide

To migrate this exact setup to a new computer:

1. **Copy the App**: Zip up the entire `~/Chaos-AI-Studio` folder and move it to the new PC.
2. **Move the Models**: Copy your `~/models` folder to the new PC.
3. **Move ComfyUI**: Copy `~/ComfyUI` to the new PC.
4. **Setup**:
   ```bash
   cd ~/Chaos-AI-Studio
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python app.py
   ```
5. Open your browser to `http://localhost:5000`.

## Architecture
- **Flask (Backend)**: Monitors processes, enforces VRAM limits, and aggregates model data.
- **Vanilla JS & CSS (Frontend)**: A modern, glassmorphism UI that requires no build tools.

*Built by your Antigravity Assistant.*
