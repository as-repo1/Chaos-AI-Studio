# 🚑 Troubleshooting Guide

Running local AI on bare-metal hardware (especially non-NVIDIA GPUs) can sometimes be tricky. If you run into issues with Chaos AI Studio, start here.

## 1. Text AI or TTS Crashes Instantly (GGUF Models)

**Symptom:** You click "Start" on Text AI or TTS, the log shows a few lines of `llama.cpp` starting up, and then it instantly crashes (often with a Segmentation Fault or an error about `tensor name too long`).

**Cause:** Modern models (especially those from Hugging Face with long metadata strings) often have tensor names that exceed the default 64-character limit in standard `llama.cpp`.

**Fix:** 
Chaos AI Studio's `setup.sh` script applies a patch automatically, but if you compiled manually, you need to increase `GGML_MAX_NAME` in `ggml.h`:
1. Open `llama.cpp-src/ggml.h`
2. Change `#define GGML_MAX_NAME 64` to `#define GGML_MAX_NAME 128`
3. Recompile the binaries: `make clean && make -j10 GGML_VULKAN=1`

## 2. "Out of Memory" (OOM) Errors

**Symptom:** Image generation fails halfway, or LLM output turns to gibberish / crashes the process.

**Cause:** Your GPU ran out of VRAM. While V2.0 natively manages dynamic VRAM offloading (`--fit on --fit-target 205` for LLMs and `--lowvram` for ComfyUI), running too many models concurrently with high thread counts or extremely large context sizes can still push limits.

**Fix:**
- Stop all other active services via the Dashboard.
- Open the settings for Llama and reduce the **Context Size**.
- The Sentinel File system handles mutual exclusion between ComfyUI and Wan2.2, but if you're running on integrated graphics or low-VRAM dedicated GPUs, make sure the other services are completely stopped (use the Force Stop button if necessary).

## 3. Intel Arc VRAM Not Showing in Telemetry

**Symptom:** GPU VRAM usage shows as `0GB / 0GB` on the Dashboard.

**Cause:** The backend reads from `/sys/class/drm/card0/device/mem_info_vram_used`. Some older Linux kernels do not expose this file for Intel Arc cards, or `card0` is your integrated GPU while the Arc is `card1`.

**Fix:**
- Check which card is which: `ls /sys/class/drm/`
- Ensure your Arch Linux kernel is up to date (`sudo pacman -Syu`).
- You can manually edit `backend/hardware.py` -> `get_gpu_memory()` to point to `card1` if your Arc GPU is not the primary device.

## 4. No Compute Backends Shown in Settings

**Symptom:** The "Compute Backend" dropdown only shows CPU.

**Cause:** Vulkan drivers are missing or not properly initialized.

**Fix:**
- Run `vulkaninfo --summary` in your terminal. If it fails or shows no physical devices, you need to install the Vulkan drivers for your OS.
- Arch Linux: `sudo pacman -S vulkan-intel vulkan-radeon` (depending on your brand).
- Ubuntu: `sudo apt install mesa-vulkan-drivers`.

## 5. Web Interface Not Loading

**Symptom:** Cannot connect to `http://localhost:5000`.

**Cause:** The Python Flask server is not running or crashed.

**Fix:**
1. Check if the port is in use: `lsof -i :5000`
2. Start the server manually to see errors:
   ```bash
   source venv/bin/activate
   python3 run.py
   ```
