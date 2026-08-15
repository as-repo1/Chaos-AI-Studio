#!/bin/bash
# ==============================================================================
# Chaos AI Studio — LLM Service (llama.cpp)
# GPU-accelerated via Vulkan | Intel Arc A370M optimised
# Model + config injected as env vars from app.py
# ==============================================================================

set -e

STUDIO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LLAMA_BIN="$STUDIO_DIR/llama.cpp-src/build/bin/llama-server"

# Fall back to system llama-server if custom build not found
if [ ! -f "$LLAMA_BIN" ]; then
    LLAMA_BIN="$(command -v llama-server 2>/dev/null || true)"
fi

if [ -z "$LLAMA_BIN" ] || [ ! -f "$LLAMA_BIN" ]; then
    echo -e "\033[1;31m[Error] llama-server binary not found."
    echo -e "Run ./setup.sh to compile it.\033[0m"
    exit 1
fi

# Config from env (set by app.py) or defaults
MODEL_PATH="${MODEL_PATH:-}"
CTX_SIZE="${CTX_SIZE:-4096}"
NGL="${NGL:-99}"
LLAMA_PORT="${LLAMA_PORT:-8080}"
THREADS="${THREADS:-4}"
VULKAN_DEVICE="${VULKAN_DEVICE:-0}"

if [ -z "$MODEL_PATH" ] || [ ! -f "$MODEL_PATH" ]; then
    echo -e "\033[1;31m[Error] MODEL_PATH not set or file not found: '$MODEL_PATH'\033[0m"
    exit 1
fi

MODEL_NAME=$(basename "$MODEL_PATH")

echo -e "\033[1;34m╔══════════════════════════════════════╗\033[0m"
echo -e "\033[1;34m║   Chaos AI Studio — LLM Service     ║\033[0m"
echo -e "\033[1;34m╚══════════════════════════════════════╝\033[0m"
echo -e "  Binary  : \033[1;32m$LLAMA_BIN\033[0m"
echo -e "  Model   : \033[1;36m$MODEL_NAME\033[0m"
echo -e "  Port    : \033[1;33m$LLAMA_PORT\033[0m"
echo -e "  Context : \033[1;33m$CTX_SIZE tokens\033[0m"
echo -e "  GPU Layers: \033[1;33m$NGL\033[0m"
echo -e "  Vulkan  : \033[1;32mDevice $VULKAN_DEVICE\033[0m"
echo ""

exec "$LLAMA_BIN" \
    -m "$MODEL_PATH" \
    --port "$LLAMA_PORT" \
    --host "0.0.0.0" \
    -ngl "$NGL" \
    --fit on \
    --fit-target 205 \
    -c "$CTX_SIZE" \
    -t "$THREADS" \
    -mg "$VULKAN_DEVICE" \
    -sm none
