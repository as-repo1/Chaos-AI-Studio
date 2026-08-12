#!/bin/bash
echo -e "\033[1;34m=== Starting XTTS Voice Cloning Server ===\033[0m"
echo -e "The server will start on port 8020."
echo -e "NOTE: It may download the 1.8GB XTTS model on the very first run."
echo -e "To configure Open WebUI, set the TTS API Base URL to \033[1;36mhttp://localhost:8020/v1\033[0m"
echo -e "Starting XTTS Server in Docker (CPU Mode)..."
echo -e "If it's the first run, Docker will download the image which might take a minute."
sudo docker run --rm -d \
  -p 8020:8020 \
  -v ~/Music/ai-voices:/models \
  --name xtts_server \
  ghcr.io/daswer123/xtts-api-server:latest \
  -t "http://localhost:8020"

echo -e "XTTS Server is starting! Open WebUI can now connect."
