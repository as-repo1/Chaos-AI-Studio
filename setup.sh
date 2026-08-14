#!/bin/bash
# ==============================================================================
# Chaos AI Studio — Setup Script
# Installs Python dependencies and compiles llama.cpp with Vulkan support
# Optimized for Intel Arc / AMD / NVIDIA GPUs
# ==============================================================================

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LLAMA_SRC="$REPO_DIR/llama.cpp-src"
LLAMA_BIN="$LLAMA_SRC/build/bin/llama-server"

GREEN='\033[1;32m'
BLUE='\033[1;34m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
NC='\033[0m'

log() { echo -e "${BLUE}[Setup]${NC} $1"; }
ok()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn(){ echo -e "${YELLOW}[!]${NC} $1"; }
err() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo ""
echo -e "  ${GREEN}██████╗██╗  ██╗ █████╗  ██████╗ ███████╗${NC}"
echo -e "  ${GREEN}██╔════╝██║  ██║██╔══██╗██╔═══██╗██╔════╝${NC}"
echo -e "  ${GREEN}██║     ███████║███████║██║   ██║███████╗${NC}"
echo -e "  ${GREEN}██║     ██╔══██║██╔══██║██║   ██║╚════██║${NC}"
echo -e "  ${GREEN}╚██████╗██║  ██║██║  ██║╚██████╔╝███████║${NC}"
echo -e "  ${GREEN}╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝${NC}"
echo -e "  ${YELLOW}AI Studio — Setup v1.0.0${NC}"
echo ""

# ── 1. Python venv ─────────────────────────────────────────────────────────────
log "Setting up Python virtual environment..."
if [ ! -d "$REPO_DIR/venv" ]; then
    python3 -m venv "$REPO_DIR/venv"
    ok "venv created"
else
    ok "venv already exists"
fi

source "$REPO_DIR/venv/bin/activate"
pip install -q --upgrade pip
pip install -q -r "$REPO_DIR/requirements.txt"
ok "Python dependencies installed"

# ── 2. Models directory ────────────────────────────────────────────────────────
log "Creating model directories..."
mkdir -p "$HOME/models/llm-models"
mkdir -p "$HOME/models/audio-models"
mkdir -p "$HOME/models/image-models"
mkdir -p "$HOME/models/video-models"
ok "Model directories ready at ~/models/"

# ── 3. llama.cpp ───────────────────────────────────────────────────────────────
if [ -f "$LLAMA_BIN" ]; then
    ok "llama-server already compiled at: $LLAMA_BIN"
else
    log "Cloning llama.cpp from GitHub..."
    if [ ! -d "$LLAMA_SRC" ]; then
        git clone --depth=1 https://github.com/ggerganov/llama.cpp.git "$LLAMA_SRC"
    fi

    log "Patching GGML_MAX_NAME limit to 128 (required for modern GGUFs)..."
    sed -i 's/#   define GGML_MAX_NAME        64/#   define GGML_MAX_NAME        128/' \
        "$LLAMA_SRC/ggml/include/ggml.h"

    # Detect Vulkan
    VULKAN_FLAG=""
    if command -v vulkaninfo &>/dev/null && vulkaninfo --summary 2>/dev/null | grep -q "Intel.*Arc\|AMD\|NVIDIA"; then
        warn "Vulkan GPU detected — enabling GGML_VULKAN for GPU acceleration"
        VULKAN_FLAG="-DGGML_VULKAN=1"
    else
        warn "No supported Vulkan GPU found — compiling CPU-only"
    fi

    log "Compiling llama-server (this will take a few minutes)..."
    cmake -B "$LLAMA_SRC/build" "$LLAMA_SRC" $VULKAN_FLAG
    cmake --build "$LLAMA_SRC/build" --config Release -j$(nproc) --target llama-server

    if [ -f "$LLAMA_BIN" ]; then
        ok "llama-server compiled successfully!"
    else
        err "Compilation failed. Check build output above."
    fi
fi

# ── 4. Default config ──────────────────────────────────────────────────────────
CONFIG="$REPO_DIR/config.json"
if [ ! -f "$CONFIG" ]; then
    log "Creating default config.json..."
    cat > "$CONFIG" <<'EOF'
{
    "llama": {
        "ctx_size": 4096,
        "ngl": 99,
        "port": 8080,
        "threads": 4,
        "model": ""
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
EOF
    ok "config.json created"
else
    ok "config.json already exists"
fi

echo ""
echo -e "${GREEN}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Setup complete! Run the app with:${NC}"
echo -e "${GREEN}  source venv/bin/activate && python app.py${NC}"
echo -e "${GREEN}  Then visit: http://localhost:5000${NC}"
echo -e "${GREEN}══════════════════════════════════════════════${NC}"
echo ""
