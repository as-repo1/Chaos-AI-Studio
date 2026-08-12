#!/bin/bash
# ==============================================================================
# Llama.cpp + Open-WebUI Installer & Runner
# Optimized for Intel Arc A370M (4GB VRAM)
# ==============================================================================

if [ "$#" -lt 1 ]; then
    echo -e "\033[1;31mError: No model provided.\033[0m"
    echo "Usage: $0 /path/to/model.gguf"
    echo "Example: $0 ~/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
    exit 1
fi

MODEL_PATH="$1"

if [ ! -f "$MODEL_PATH" ]; then
    echo -e "\033[1;31mError: Model file not found at '$MODEL_PATH'\033[0m"
    exit 1
fi

echo -e "\033[1;34m=== [1/3] Checking llama.cpp engine ===\033[0m"
if ! command -v llama-server &> /dev/null; then
    echo "llama-cpp is not installed. Requesting sudo permission to install via pacman..."
    sudo pacman -S --noconfirm llama-cpp
else
    echo "llama-cpp is already installed."
fi

echo -e "\n\033[1;34m=== [2/3] Checking Open-WebUI (Docker) ===\033[0m"
if ! command -v docker &> /dev/null; then
    echo -e "\033[1;31mError: Docker is not installed or not in PATH. Please install Docker first.\033[0m"
    exit 1
fi

if ! sudo docker ps -a --format '{{.Names}}' | grep -Eq "^open-webui\$"; then
    echo "Creating and starting new Open-WebUI container..."
    sudo docker run -d -p 3000:8080 \
      --add-host=host.docker.internal:host-gateway \
      -v open-webui:/app/backend/data \
      --name open-webui \
      --restart always \
      -e OPENAI_API_BASE_URL="http://host.docker.internal:8080/v1" \
      -e OPENAI_API_KEY="llama-cpp-key" \
      -e ENABLE_OLLAMA_API="False" \
      ghcr.io/open-webui/open-webui:main
else
    if ! sudo docker ps --format '{{.Names}}' | grep -Eq "^open-webui\$"; then
        echo "Starting existing Open-WebUI container..."
        sudo docker start open-webui
    else
        echo "Open-WebUI container is already running."
    fi
fi

echo -e "\n\033[1;34m=== [3/3] Starting llama-server Backend ===\033[0m"
echo -e "\033[1;32mEverything is ready! \033[0m"
echo -e "Open your browser and navigate to: \033[1;36mhttp://localhost:3000\033[0m"
echo "Press Ctrl+C to stop the AI server."
echo "------------------------------------------------------------"

# Run the API server with Intel Arc 4GB VRAM optimizations
llama-server \
    -m "$MODEL_PATH" \
    --alias "$(basename "$MODEL_PATH" .gguf)" \
    --port 8080 \
    --host "0.0.0.0" \
    -ngl 99 \
    -c 16384 \
    -t 4
