#!/bin/bash
# ==============================================================================
# Llama.cpp VibeVoice TTS Runner
# Optimized for Intel Arc A370M (4GB VRAM)
# ==============================================================================

MODELS_DIR="$HOME/models/audio-models"
MODEL_PATH="${MODEL_PATH:-$MODELS_DIR/vibevoice-1.5b-q4_k_m.gguf}"

if [ ! -f "$MODEL_PATH" ]; then
    echo -e "\033[1;31mError: VibeVoice model not found at '$MODEL_PATH'\033[0m"
    exit 1
fi

echo -e "\n\033[1;34m=== Starting VibeVoice TTS Backend ===\033[0m"
echo -e "\033[1;32mEverything is ready! \033[0m"
echo -e "Open WebUI can now connect to \033[1;36mhttp://localhost:8090/v1\033[0m for Audio generation."
echo "Press Ctrl+C to stop the AI server."
echo "------------------------------------------------------------"

# Dynamic variables loaded from config (defaults match app.py safe defaults)
CTX_SIZE="${CTX_SIZE:-1024}"
NGL="${NGL:-99}"
PORT="${TTS_PORT:-8090}"
THREADS="${THREADS:-4}"
VULKAN_DEVICE="${VULKAN_DEVICE:-0}"

# Run the API server with Intel Arc 4GB VRAM optimizations
/home/chaos/Chaos-AI-Studio/llama.cpp-src/build/bin/llama-server \
    -m "$MODEL_PATH" \
    --port "$PORT" \
    --host "0.0.0.0" \
    -ngl "$NGL" \
    --fit on \
    --fit-target 205 \
    -c "$CTX_SIZE" \
    -mg "$VULKAN_DEVICE" \
    -sm none \
    -t "$THREADS"
