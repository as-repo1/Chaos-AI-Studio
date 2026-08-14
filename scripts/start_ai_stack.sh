#!/bin/bash
# ==============================================================================
# Llama.cpp + Open-WebUI Installer & Runner
# Optimized for Intel Arc A370M (4GB VRAM)
# ==============================================================================

# No model required as an argument since we use Router Mode
MODELS_DIR="$HOME/models/llm-models"

if [ ! -d "$MODELS_DIR" ]; then
    echo -e "\033[1;31mError: Models directory not found at '$MODELS_DIR'\033[0m"
    exit 1
fi

# Warn if no models are present
if [ -z "$(ls -A "$MODELS_DIR"/*.gguf 2>/dev/null)" ]; then
    echo -e "\033[1;33mWarning: No .gguf model files found in '$MODELS_DIR'. Add models before sending requests.\033[0m"
fi

echo -e "\033[1;34m=== [1/3] Checking llama.cpp engine ===\033[0m"
if ! command -v llama-server &> /dev/null; then
    echo -e "\033[1;31mError: llama-server is not installed. Please install llama-cpp first.\033[0m"
    exit 1
else
    echo "llama-cpp is already installed."
fi

echo -e "\n\033[1;34m=== [2/3] Checking Open-WebUI (Docker) ===\033[0m"
if ! command -v docker &> /dev/null; then
    echo -e "\033[1;31mError: Docker is not installed or not in PATH. Please install Docker first.\033[0m"
    exit 1
fi

if ! docker ps | grep -q open-webui; then
    if ! docker ps -a | grep -q open-webui; then
        echo "Creating and starting new Open-WebUI container..."
        docker run -d -p 3000:8080 \
          --add-host=host.docker.internal:host-gateway \
          -v open-webui:/app/backend/data \
          --name open-webui \
          --restart always \
          -e OPENAI_API_BASE_URL="http://host.docker.internal:8080/v1" \
          -e OPENAI_API_KEY="llama-cpp-key" \
          -e ENABLE_OLLAMA_API="False" \
          ghcr.io/open-webui/open-webui:main
    else
        echo "Starting existing Open-WebUI container..."
        docker start open-webui
    fi
else
    echo "Open-WebUI container is already running."
fi

echo -e "\n\033[1;34m=== [3/3] Starting llama-server Backend ===\033[0m"
echo -e "\033[1;32mEverything is ready! \033[0m"
echo -e "Open your browser and navigate to: \033[1;36mhttp://localhost:3000\033[0m"
echo "Press Ctrl+C to stop the AI server."
echo "------------------------------------------------------------"

# Dynamic variables loaded from config (defaults match app.py safe defaults)
CTX_SIZE="${CTX_SIZE:-4096}"
NGL="${NGL:-99}"
PORT="${LLAMA_PORT:-8080}"
THREADS="${THREADS:-4}"

# Run the API server with Intel Arc 4GB VRAM optimizations in Router Mode
llama-server \
    --models-dir "$MODELS_DIR" \
    --models-max 1 \
    --port "$PORT" \
    --host "0.0.0.0" \
    -ngl "$NGL" \
    -c "$CTX_SIZE" \
    -t "$THREADS"
