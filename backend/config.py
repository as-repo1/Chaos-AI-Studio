import os
import json
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
HOME_DIR = str(Path.home())
SCRIPTS_DIR = os.path.join(HOME_DIR, "Chaos-AI-Studio", "scripts")
MODELS_DIR = os.path.join(HOME_DIR, "models")
CONFIG_PATH = os.path.join(HOME_DIR, "Chaos-AI-Studio", "config", "config.json")
LLAMA_BIN = os.path.join(
    HOME_DIR, "Chaos-AI-Studio", "llama.cpp-src", "build", "bin", "llama-server"
)


# ── Config ────────────────────────────────────────────────────────────────────
def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "llama": {
            "ctx_size": 4096,
            "ngl": "auto",
            "port": 8080,
            "threads": 4,
            "model": "",
            "vulkan_device": 0,
        },
        "text2speach": {
            "ctx_size": 1024,
            "ngl": "auto",
            "port": 8090,
            "threads": 4,
            "model": "vibevoice-1.5b-q4_k_m.gguf",
            "vulkan_device": 0,
        },
        "comfyui": {"lowvram": True, "normalvram": False},
    }


def save_config(config_data):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config_data, f, indent=4)
