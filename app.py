import os
import subprocess
from flask import Flask, render_template, jsonify, request
from pathlib import Path

app = Flask(__name__)

# Paths
HOME_DIR = str(Path.home())
SCRIPTS_DIR = os.path.join(HOME_DIR, "Chaos-AI-Studio", "scripts")
MODELS_DIR = os.path.join(HOME_DIR, "models")

# We no longer store the subprocess objects because we want to query the OS directly!
script_map = {
    "llama": "start_ai_stack.sh",
    "comfyui": "start_comfyui.sh",
    "musicgen": "start_musicgen.sh",
    "xtts": "start_tts_server.sh"
}

CATALOGUE = [
    {
        "id": "llama-3-8b",
        "name": "Llama 3 8B Instruct",
        "type": "Text (GGUF)",
        "description": "State-of-the-art 8B parameter text model. Perfect for coding and conversation.",
        "url": "https://huggingface.co/lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf",
        "filename": "Meta-Llama-3-8B-Instruct-Q4_K_M.gguf",
        "category": "llm-models"
    },
    {
        "id": "sdxl-turbo",
        "name": "SDXL Turbo",
        "type": "Image (Safetensors)",
        "description": "Lightning-fast image generation model. Creates images in 1-2 steps.",
        "url": "https://huggingface.co/stabilityai/sdxl-turbo/resolve/main/sd_xl_turbo_1.0_fp16.safetensors",
        "filename": "sd_xl_turbo_1.0_fp16.safetensors",
        "category": "image-models"
    },
    {
        "id": "openhermes-2.5",
        "name": "OpenHermes 2.5",
        "type": "Text (GGUF)",
        "description": "Highly capable uncensored chat model. Excellent for roleplay and creative writing.",
        "url": "https://huggingface.co/TheBloke/OpenHermes-2.5-Mistral-7B-GGUF/resolve/main/openhermes-2.5-mistral-7b.Q4_K_M.gguf",
        "filename": "openhermes-2.5-mistral-7b.Q4_K_M.gguf",
        "category": "llm-models"
    },
    {
        "id": "animagine-xl",
        "name": "Animagine XL 3.1",
        "type": "Image (Safetensors)",
        "description": "The absolute best anime-style generation model available.",
        "url": "https://huggingface.co/cagliostrolab/animagine-xl-3.1/resolve/main/animagine-xl-3.1.safetensors",
        "filename": "animagine-xl-3.1.safetensors",
        "category": "image-models"
    }
]

# Track active downloads
downloads = {}

def is_running(process_name):
    if process_name == "llama":
        return os.system('pgrep -f "llama-server" > /dev/null') == 0
    elif process_name == "comfyui":
        return os.system('pgrep -f "use-pytorch-cross-attention" > /dev/null') == 0
    elif process_name == "musicgen":
        return os.system('pgrep -f "music_app.py" > /dev/null') == 0
    elif process_name == "xtts":
        return os.system('docker ps | grep "xtts_server" > /dev/null') == 0
    return False

def get_models():
    models = []
    llm_dir = os.path.join(MODELS_DIR, "llm-models")
    if os.path.exists(llm_dir):
        for f in os.listdir(llm_dir):
            if f.endswith(".gguf"):
                size = os.path.getsize(os.path.join(llm_dir, f)) / (1024*1024*1024)
                models.append({"name": f, "type": "Text (GGUF)", "size": f"{size:.2f} GB"})
                
    img_dir = os.path.join(MODELS_DIR, "image-models")
    if os.path.exists(img_dir):
        for f in os.listdir(img_dir):
            if f.endswith(".safetensors"):
                size = os.path.getsize(os.path.join(img_dir, f)) / (1024*1024*1024)
                models.append({"name": f, "type": "Image (Safetensors)", "size": f"{size:.2f} GB"})
    return models

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def status():
    return jsonify({
        name: {"running": is_running(name)} for name in script_map.keys()
    })

@app.route("/api/models")
def list_models():
    return jsonify(get_models())

@app.route("/api/catalogue")
def catalogue():
    # Return catalogue with download status
    for item in CATALOGUE:
        item["is_downloading"] = item["id"] in downloads and downloads[item["id"]].poll() is None
        # Check if already exists
        target_path = os.path.join(MODELS_DIR, item["category"], item["filename"])
        item["is_downloaded"] = os.path.exists(target_path)
    return jsonify(CATALOGUE)

@app.route("/api/download/<model_id>", methods=["POST"])
def download_model(model_id):
    model = next((m for m in CATALOGUE if m["id"] == model_id), None)
    if not model:
        return jsonify({"error": "Model not found"}), 404
        
    target_dir = os.path.join(MODELS_DIR, model["category"])
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, model["filename"])
    
    if os.path.exists(target_path):
        return jsonify({"error": "Model already downloaded!"}), 400
        
    if model_id in downloads and downloads[model_id].poll() is None:
        return jsonify({"error": "Already downloading"}), 400
        
    # Start download in background
    proc = subprocess.Popen(
        ["wget", "-O", target_path, model["url"]],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    downloads[model_id] = proc
    return jsonify({"status": "download started"})

@app.route("/api/start/<service>", methods=["POST"])
def start_service(service):
    if service not in script_map:
        return jsonify({"error": "Invalid service"}), 400
        
    if service == "comfyui" and is_running("llama"):
        return jsonify({"error": "VRAM Limit: Stop Llama (Text AI) before starting ComfyUI."}), 400
    if service == "llama" and is_running("comfyui"):
        return jsonify({"error": "VRAM Limit: Stop ComfyUI before starting Llama."}), 400

    if is_running(service):
        return jsonify({"status": "already running"})
        
    script_path = os.path.join(SCRIPTS_DIR, script_map[service])
    
    cmd = ["bash", script_path]
    if service == "llama":
        llm_dir = os.path.join(MODELS_DIR, "llm-models")
        if os.path.exists(llm_dir):
            models = [f for f in os.listdir(llm_dir) if f.endswith(".gguf")]
            if models:
                cmd.append(os.path.join(llm_dir, models[0]))
            else:
                return jsonify({"error": "No GGUF models found! Please download one from the Catalogue first."}), 400
        else:
            return jsonify({"error": "Model directory not found!"}), 400

    subprocess.Popen(
        cmd,
        cwd=HOME_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return jsonify({"status": "started"})

@app.route("/api/stop/<service>", methods=["POST"])
def stop_service(service):
    if service == "llama":
        os.system("pkill -f llama-server")
    elif service == "comfyui":
        os.system("pkill -f main.py")
    elif service == "musicgen":
        os.system("pkill -f music_app.py")
    elif service == "xtts":
        os.system("docker stop xtts_server")
        
    return jsonify({"status": "stopped"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
