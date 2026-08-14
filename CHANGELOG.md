# Changelog

All notable changes to **Chaos AI Studio** will be documented here.

---

## [1.0.0] — 2026-08-15

### 🎉 Initial Release

**Services managed:**
- **Text AI (Llama)** — Local LLM server via llama.cpp (OpenAI-compatible API on port 8080)
- **Image AI (ComfyUI)** — Stable Diffusion image generation (port 8188)
- **Video AI (Wan2.2)** — Text-to-video generation via ComfyUI (port 8188)
- **Audio AI (MusicGen)** — Music generation (port 7860)
- **TTS (VibeVoice)** — Text-to-speech via llama.cpp GGUF (port 8090)

**Features:**
- Glassmorphic dark UI with vertical navigation sidebar
- Real-time system telemetry (CPU, RAM, Swap, GPU VRAM)
- Split-view log panel with ANSI colour support
- Four themes: Neon Dark, Nord, Gruvbox, Tokyo Night
- VRAM mutual exclusion — prevents OOM on 4GB GPUs
- Service settings modal (context size, GPU layers, threads, port)
- Model Hub with one-click downloads from Hugging Face
- Force stop button (SIGKILL) for stuck services
- Sentinel-file approach to distinguish ComfyUI from Wan2.2
- Custom llama.cpp build with `GGML_MAX_NAME=128` for modern GGUFs
- Vulkan GPU acceleration (Intel Arc / AMD / NVIDIA)

**Hardware Optimised For:**
- Intel Arc A370M (4GB VRAM, DG2) via Vulkan + Mesa
- Arch Linux

**Bug Fixes (pre-release):**
- Fixed `wan_video` cross-killing `comfyui` on stop (shared pgrep pattern)
- Fixed `llama` default ctx_size (was 16384, now 4096)
- Fixed GGML tensor name length limit (64→128) for VibeVoice GGUF
- Fixed duplicate `</div>` in service card template
- Fixed log panel title showing raw service ID instead of friendly name
- Fixed all CSS hardcoded colours to respect theme CSS variables
- Fixed `settings-btn` rotation — only gear icon rotates on hover now
- Silenced `pgrep` stderr noise in service detection
