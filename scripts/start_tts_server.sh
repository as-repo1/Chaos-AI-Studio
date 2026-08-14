#!/bin/bash
echo -e "\033[1;34m=== Starting XTTS Voice Cloning Server ===\033[0m"
echo -e "The server will start on port 8020."
echo -e "NOTE: It may download the 1.8GB XTTS model on the very first run."
echo -e "To configure Open WebUI, set the TTS API Base URL to \033[1;36mhttp://localhost:8020/v1\033[0m"

# Idempotency check — don't create a new container if one already exists
if docker ps | grep -q xtts_server; then
    echo -e "\033[1;32mXTTS Server is already running.\033[0m"
    exit 0
fi

if docker ps -a | grep -q xtts_server; then
    echo "Starting existing XTTS container..."
    docker start xtts_server
else
    echo -e "Starting XTTS Server in Docker (Intel XPU Mode)..."
    echo -e "If it's the first run, Docker will download the image which might take a minute."
    docker run -d \
      -p 8020:8020 \
      -v ~/Music/ai-voices:/models \
      --device /dev/dri \
      -e SYCL_PI_LEVEL_ZERO_USE_IMMEDIATE_COMMANDLISTS=1 \
      -e ZES_ENABLE_SYSMAN=1 \
      --name xtts_server \
      --restart unless-stopped \
      ghcr.io/daswer123/xtts-api-server:latest \
      -t "http://localhost:8020"
fi

echo -e "XTTS Server is starting! Open WebUI can now connect."
