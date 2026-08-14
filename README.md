<div align="center">

```
██████╗██╗  ██╗ █████╗  ██████╗ ███████╗     █████╗ ██╗
██╔════╝██║  ██║██╔══██╗██╔═══██╗██╔════╝    ██╔══██╗██║
██║     ███████║███████║██║   ██║███████╗    ███████║██║
██║     ██╔══██║██╔══██║██║   ██║╚════██║    ██╔══██║██║
╚██████╗██║  ██║██║  ██║╚██████╔╝███████║    ██║  ██║██║
 ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝    ╚═╝  ╚═╝╚═╝
                    S T U D I O
```

**A self-hosted, GPU-accelerated AI management dashboard for running LLMs, image generation, video AI, music generation, and text-to-speech — entirely offline.**

[![Version](https://img.shields.io/badge/version-1.0.0-a3e635?style=flat-square)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-MIT-f97316?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square)](https://python.org)
[![GPU](https://img.shields.io/badge/GPU-Intel%20Arc%20%2F%20AMD%20%2F%20NVIDIA-88c0d0?style=flat-square)](https://github.com/ggerganov/llama.cpp)

</div>

---

## ✨ Features

- **Unified Dashboard** — Start, stop, and monitor all your AI services from one place
- **Real-time Telemetry** — Live CPU, RAM, Swap, and GPU VRAM usage graphs
- **Split-View Logs** — Coloured ANSI log panel slides in from the right per-service
- **VRAM Guard** — Prevents OOM crashes by enforcing mutual exclusion between heavy services
- **4 Themes** — Neon Dark · Nord · Gruvbox · Tokyo Night
- **Model Hub** — Browse and one-click download models from Hugging Face
- **Force Stop** — SIGKILL button for services that refuse to shut down gracefully
- **Fully Local** — No cloud, no telemetry, no internet required after setup

---

## 🤖 Managed Services

| Service | Technology | Port | What it does |
|---|---|---|---|
| **Text AI (Llama)** | llama.cpp | 8080 | OpenAI-compatible LLM API |
| **Image AI (ComfyUI)** | ComfyUI | 8188 | Stable Diffusion image gen |
| **Video AI (Wan2.2)** | ComfyUI + Wan | 8188 | Text/Image → Video |
| **Audio AI (MusicGen)** | Gradio | 7860 | AI music generation |
| **TTS (VibeVoice)** | llama.cpp GGUF | 8090 | Text-to-speech |

---

## ⚡ Quick Start

### Prerequisites

```bash
# Arch Linux
sudo pacman -S git python cmake vulkan-tools

# Ubuntu / Debian
sudo apt install git python3 python3-venv cmake vulkan-tools
```

### Install & Run

```bash
git clone https://github.com/YOUR_USERNAME/Chaos-AI-Studio.git
cd Chaos-AI-Studio
chmod +x setup.sh
./setup.sh
```

The setup script will:
1. Create a Python virtual environment and install dependencies
2. Create `~/models/{llm,audio,image,video}-models/` directories
3. Clone and compile `llama.cpp` with **Vulkan GPU acceleration** and the `GGML_MAX_NAME=128` patch (required for modern GGUF models)
4. Create a default `config.json`

Then launch the dashboard:

```bash
source venv/bin/activate
python app.py
```

Open **http://localhost:5000** in your browser.

---

## 📁 Project Structure

```
Chaos-AI-Studio/
├── app.py                  # Flask backend — service management, API
├── setup.sh                # One-command installer
├── requirements.txt        # Python dependencies
├── config.json             # Runtime settings (gitignored)
├── scripts/
│   ├── start_ai_stack.sh   # Llama LLM server
│   ├── start_comfyui.sh    # ComfyUI image generation
│   ├── start_musicgen.sh   # MusicGen audio
│   └── start_text2speech.sh # VibeVoice TTS
├── templates/
│   ├── base.html           # Layout, sidebar, log panel, themes
│   ├── dashboard.html      # Service cards, telemetry
│   └── models.html         # Model hub / download manager
└── static/
    └── style.css           # Theme system + all component styles
```

---

## 🛠 Configuration

Settings are stored in `config.json` (auto-created on first run). You can also edit them per-service through the ⚙ gear icon on each service card.

```json
{
    "llama": {
        "ctx_size": 4096,
        "ngl": 99,
        "port": 8080,
        "threads": 4,
        "model": "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
    },
    "text2speach": {
        "ctx_size": 1024,
        "ngl": 99,
        "port": 8090,
        "threads": 4,
        "model": "vibevoice-1.5b-q4_k_m.gguf"
    },
    "comfyui": {
        "lowvram": true,
        "normalvram": false
    }
}
```

---

## 🎮 GPU Support

| GPU Family | Backend | Notes |
|---|---|---|
| Intel Arc (DG2+) | Vulkan (Mesa) | Tested on A370M 4GB |
| AMD Radeon (RDNA2+) | Vulkan (Mesa/AMDVLK) | |
| NVIDIA | Vulkan or CUDA | Use CUDA build for best perf |
| CPU only | AVX2 | Falls back automatically |

The `setup.sh` script automatically detects Vulkan and enables it at compile time.

---

## 📦 Adding Models

Drop model files into the appropriate subdirectory under `~/models/`:

```
~/models/
├── llm-models/       ← .gguf files for Llama, Qwen, Phi, etc.
├── audio-models/     ← .gguf files for TTS (VibeVoice)
├── image-models/     ← .safetensors for ComfyUI
└── video-models/     ← .gguf or .safetensors for Wan2.2
```

Or use the **Model Hub** tab in the dashboard to download directly.

---

## 🐛 Known Issues

- **ComfyUI / Wan2.2** share the same process (ComfyUI backend) — the studio uses a sentinel file (`/tmp/wan_video_active`) to tell them apart
- **VibeVoice GGUF** requires the patched `llama.cpp` (tensor name limit ≥128). The `setup.sh` applies this automatically
- **Intel Arc VRAM reporting** requires kernel support for `/sys/class/drm/card0/device/mem_info_vram_*`

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

<div align="center">
Built with 🔥 for local-first AI
</div>
