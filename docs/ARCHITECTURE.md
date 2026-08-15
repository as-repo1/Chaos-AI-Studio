# 🏗 Architecture & Design

Chaos AI Studio is designed to be a lightweight, zero-friction orchestrator for local AI services. Unlike massive cloud-native stacks (Docker/Kubernetes), this project targets bare-metal execution to extract maximum performance from consumer GPUs (like Intel Arc, AMD Radeon, and NVIDIA).

## 1. Process Management & The Watchdog

The core of the studio is driven by the `backend/` Flask module (launched via `run.py`). It does **not** rely on `systemd` or Docker. 

Instead, it uses a background python `threading.Thread` known as the **Watchdog** (found in `backend/process_manager.py`).
- The watchdog wakes up every 8 seconds.
- It iterates over the expected state of each service (`stopped`, `starting`, `ready`).
- It verifies if the underlying binary (e.g., `llama-server`, `ComfyUI`) is actually running using `pgrep` and HTTP health checks.
- If a service dies unexpectedly, the watchdog flags it as `crashed`, allowing the UI to display an immediate warning banner.
- An `atexit` cleanup hook ensures that when the dashboard is closed, all spawned AI processes are safely killed.

## 2. Resource Contention (VRAM Offloading & Sentinels)

Running LLMs, Text-to-Speech, and Image/Video generation concurrently on a single GPU (especially a 4GB or 8GB card) will inevitably cause Out-Of-Memory (OOM) crashes.

To solve this, we enforce **strict memory management**:
- **Dynamic VRAM Scaling**: `llama-server` instances run with `--fit on --fit-target 205`, ensuring the GPU is filled up to 95% capacity, smoothly offloading the rest to the CPU (System RAM) without OOM crashes.
- **Low VRAM Mode**: Image and video diffusion models are forcibly run with `--lowvram` to prevent idle model bloat.
- **Sentinel Files**: When `Video AI (Wan2.2)` starts, it creates a sentinel file `/tmp/wan_video_active`. `Image AI (ComfyUI)` checks for this file. Since both use the underlying ComfyUI engine but require completely different VRAM allocations and model weights, the dashboard knows how to forcefully kill one to allow the other to boot safely.

## 3. Dynamic Model Injection

To avoid hardcoded configs, `start_ai_stack.sh` relies purely on environment variables passed down by `backend/process_manager.py`.
When a user clicks "Start" on Text AI:
1. `backend/config.py` reads `config/config.json` to find the selected model, threads, and Compute Backend (Vulkan device index).
2. It sets `MODEL_PATH=/home/user/models/llm-models/...` and `VULKAN_DEVICE=0`.
3. It spawns `start_ai_stack.sh`, which strictly executes the `llama-server` binary using those variables.

## 4. Frontend & Theming

The UI is built entirely in Vanilla HTML/JS/CSS without heavy frameworks like React or Next.js.
- **Glassmorphism:** CSS `backdrop-filter: blur()` is heavily utilized to give a native desktop feel.
- **Themes:** `static/style.css` defines CSS Variables (`--bg-dark`, `--primary`, `--card-bg`). Changing themes simply swaps out the `:root` variables via JavaScript, instantly repainting the entire UI.
- **Real-Time Data:** Telemetry (CPU/RAM/GPU) is fetched via a simple `setInterval` polling the `/api/telemetry` endpoint. Logs are fetched via a similar mechanism, parsing raw ANSI color codes into HTML spans for the slide-out terminal panel.
