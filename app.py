import os
import subprocess
import psutil
import json
import urllib.request
from flask import Flask, render_template, jsonify, request
from pathlib import Path

app = Flask(__name__)

# Paths
HOME_DIR = str(Path.home())
SCRIPTS_DIR = os.path.join(HOME_DIR, "Chaos-AI-Studio", "scripts")
MODELS_DIR = os.path.join(HOME_DIR, "models")
CONFIG_PATH = os.path.join(HOME_DIR, "Chaos-AI-Studio", "config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "llama": {"ctx_size": 8192, "ngl": 99, "port": 8080, "threads": 4},
        "comfyui": {"lowvram": True, "normalvram": False}
    }

def save_config(config_data):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config_data, f, indent=4)

# We no longer store the subprocess objects because we want to query the OS directly!
script_map = {
    "llama": "start_ai_stack.sh",
    "comfyui": "start_comfyui.sh",
    "wan_video": "start_comfyui.sh",
    "musicgen": "start_musicgen.sh",
    "xtts": "start_tts_server.sh",
    "text2speach": "start_text2speech.sh"
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
    },
    {
        "id": "wan-video-1.3b",
        "name": "Wan2.1 (1.3B)",
        "type": "Video (Safetensors)",
        "description": "State-of-the-art text-to-video model. Requires ComfyUI to run on low VRAM.",
        "url": "https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B/resolve/main/models_t2v_1.3B/diffusion_pytorch_model.safetensors",
        "filename": "wan2.1_t2v_1.3b.safetensors",
        "category": "video-models"
    },
    {
        "id": "deepseek-r1-7b",
        "name": "DeepSeek R1 (7B)",
        "type": "Text (GGUF)",
        "description": "Excellent reasoning model optimized for code and complex queries.",
        "url": "https://huggingface.co/TheBloke/deepseek-coder-6.7B-instruct-GGUF/resolve/main/deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
        "filename": "deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
        "category": "llm-models"
    },
    {
        "id": "qwen2.5-1.5b",
        "name": "Qwen 2.5 (1.5B)",
        "type": "Text (GGUF)",
        "description": "Incredibly smart but tiny Small Language Model (SLM). Easily runs on 4GB VRAM.",
        "url": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "category": "llm-models"
    },
    {
        "id": "llava-1.5-7b",
        "name": "LLaVA 1.5 (7B)",
        "type": "Multimodal (GGUF)",
        "description": "Vision-language model. Upload an image and chat about its contents.",
        "url": "https://huggingface.co/mys/ggml_llava-v1.5-7b/resolve/main/ggml-model-q4_k.gguf",
        "filename": "ggml-model-q4_k.gguf",
        "category": "llm-models"
    },
    {
        "id": "nomic-embed-text",
        "name": "Nomic Embed Text v1.5",
        "type": "Embedding (GGUF)",
        "description": "High-performance embedding model for local document search and RAG.",
        "url": "https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF/resolve/main/nomic-embed-text-v1.5.Q4_K_M.gguf",
        "filename": "nomic-embed-text-v1.5.Q4_K_M.gguf",
        "category": "llm-models"
    },
    {
        "id": "bark-small",
        "name": "Suno Bark (Small)",
        "type": "Audio (PyTorch)",
        "description": "Highly expressive text-to-speech model capable of generating non-speech sounds.",
        "url": "https://huggingface.co/suno/bark-small/resolve/main/pytorch_model.bin",
        "filename": "pytorch_model.bin",
        "category": "audio-models"
    }
]

# Track active downloads
downloads = {}

def is_running(process_name):
    if process_name == "llama":
        return os.system('pgrep -f "[l]lama-server.*llm-models" > /dev/null 2>&1') == 0
    elif process_name == "text2speach":
        return os.system('pgrep -f "[l]lama-server.*audio-models" > /dev/null 2>&1') == 0
    elif process_name == "comfyui":
        # ComfyUI without wan_video sentinel file
        is_comfy = os.system('pgrep -f "ComfyUI/[m]ain.py" > /dev/null 2>&1') == 0
        is_wan = os.path.exists('/tmp/wan_video_active')
        return is_comfy and not is_wan
    elif process_name == "wan_video":
        # We create a sentinel file when starting wan_video to distinguish from comfyui
        is_comfy = os.system('pgrep -f "ComfyUI/[m]ain.py" > /dev/null 2>&1') == 0
        return is_comfy and os.path.exists('/tmp/wan_video_active')
    elif process_name == "musicgen":
        return os.system('pgrep -f "[m]usic_app.py" > /dev/null 2>&1') == 0
    elif process_name == "xtts":
        return os.system('docker ps 2>/dev/null | grep -q "[x]tts_server"') == 0
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
                
    vid_dir = os.path.join(MODELS_DIR, "video-models")
    if os.path.exists(vid_dir):
        for f in os.listdir(vid_dir):
            if f.endswith(".safetensors"):
                size = os.path.getsize(os.path.join(vid_dir, f)) / (1024*1024*1024)
                models.append({"name": f, "type": "Video (Safetensors)", "size": f"{size:.2f} GB"})
                
    return models

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/models")
def models_page():
    return render_template("models.html")

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
    # Return copies — never mutate the global CATALOGUE list in-place
    result = []
    for item in CATALOGUE:
        target_path = os.path.join(MODELS_DIR, item["category"], item["filename"])
        result.append({
            **item,
            "is_downloading": item["id"] in downloads and downloads[item["id"]].poll() is None,
            "is_downloaded": os.path.exists(target_path)
        })
    return jsonify(result)

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

def get_gpu_info():
    info = {
        "gpu_percent": 0,
        "vram_percent": 0,
        "vram_used_gb": 0.0,
        "vram_total_gb": 4.0 # Default for A370M
    }
    try:
        base_path = "/sys/class/drm/card0/device"
        
        # Try to get VRAM usage (common for AMD and newer Intel drivers)
        used_path = os.path.join(base_path, "mem_info_vram_used")
        total_path = os.path.join(base_path, "mem_info_vram_total")
        
        if os.path.exists(used_path) and os.path.exists(total_path):
            with open(used_path) as f:
                used = int(f.read().strip())
            with open(total_path) as f:
                total = int(f.read().strip())
            info["vram_used_gb"] = round(used / (1024**3), 2)
            info["vram_total_gb"] = round(total / (1024**3), 2)
            if total > 0:
                info["vram_percent"] = round((used / total) * 100, 1)
                
        # Try to get GPU busy percent
        busy_path = os.path.join(base_path, "gpu_busy_percent")
        if os.path.exists(busy_path):
            with open(busy_path) as f:
                info["gpu_percent"] = int(f.read().strip())
    except Exception:
        pass
        
    return info

@app.route('/api/system')
def get_system():
    ram = psutil.virtual_memory()
    swap = psutil.swap_memory()
    gpu = get_gpu_info()
    return jsonify({
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "ram_percent": ram.percent,
        "ram_used_gb": round(ram.used / (1024**3), 2),
        "ram_total_gb": round(ram.total / (1024**3), 2),
        "swap_percent": swap.percent,
        "swap_used_gb": round(swap.used / (1024**3), 2),
        "swap_total_gb": round(swap.total / (1024**3), 2),
        "gpu_percent": gpu["gpu_percent"],
        "gpu_used_gb": gpu["vram_used_gb"],
        "gpu_total_gb": gpu["vram_total_gb"],
        "gpu_vram_percent": gpu["vram_percent"]
    })

@app.route('/api/models/text')
def get_text_models():
    models_list = []
    
    # Check both llm-models and root models dir
    dirs_to_check = [os.path.join(MODELS_DIR, "llm-models"), MODELS_DIR]
    
    for d in dirs_to_check:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.endswith(".gguf") and f not in models_list:
                    models_list.append(f)
                    
    return jsonify(models_list)

@app.route("/api/start/<service>", methods=["POST"])
def start_service(service):
    if service not in script_map:
        return jsonify({"error": "Invalid service"}), 400
        
    heavy_models = ["llama", "comfyui", "wan_video", "text2speach"]
    if service in heavy_models:
        running_heavy = [s for s in heavy_models if s != service and is_running(s)]
        if running_heavy:
            return jsonify({"error": f"VRAM Limit: Stop {running_heavy[0]} before starting {service}."}), 400

    if is_running(service):
        return jsonify({"status": "already running"})
        
    config = load_config()
    script_env = os.environ.copy()
    
    script_path = os.path.join(SCRIPTS_DIR, script_map[service])
    
    cmd = ["bash", script_path]
    if service == "llama":
        llama_conf = config.get("llama", {})
        script_env["CTX_SIZE"] = str(llama_conf.get("ctx_size", 4096))
        script_env["NGL"] = str(llama_conf.get("ngl", 99))
        script_env["LLAMA_PORT"] = str(llama_conf.get("port", 8080))
        script_env["THREADS"] = str(llama_conf.get("threads", 4))

    if service == "text2speach":
        tts_conf = config.get("text2speach", {})
        script_env["CTX_SIZE"] = str(tts_conf.get("ctx_size", 1024))
        script_env["NGL"] = str(tts_conf.get("ngl", 99))
        script_env["TTS_PORT"] = str(tts_conf.get("port", 8090))
        script_env["THREADS"] = str(tts_conf.get("threads", 4))
        # Explicitly pass model path for audio-models subfolder detection
        script_env["MODEL_PATH"] = str(os.path.join(MODELS_DIR, "audio-models", tts_conf.get("model", "vibevoice-1.5b-q4_k_m.gguf")))

    if service == "comfyui":
        # Remove wan_video sentinel in case it was left over
        try:
            os.remove('/tmp/wan_video_active')
        except FileNotFoundError:
            pass
        comfy_conf = config.get("comfyui", {})
        if comfy_conf.get("lowvram", True):
            script_env["COMFYUI_ARGS"] = "--lowvram"
        elif comfy_conf.get("normalvram", False):
            script_env["COMFYUI_ARGS"] = "--normalvram"

    if service == "wan_video":
        # Create sentinel file to distinguish wan_video from comfyui
        open('/tmp/wan_video_active', 'w').close()
        # EXTREME VRAM optimization for Wan2.2 on Intel Arc 4GB
        script_env["COMFYUI_ARGS"] = "--lowvram --fp16-vae --fp8_e4m3fn-text-enc"

    # Write to log file; use a detached Popen so the child inherits the fd
    # but we close our handle immediately to avoid a file descriptor leak.
    log_path = f"/tmp/{service}_spawn.log"
    with open(log_path, "w") as log_file: # 'w' to clear previous logs on start
        log_file.write(f"Starting {service} with cmd: {cmd}\n")
        log_file.flush()
        # Pass the numeric fd so Popen can inherit it, then close ours.
        subprocess.Popen(
            cmd,
            cwd=HOME_DIR,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=script_env,
            close_fds=True
        )
    return jsonify({"status": "started"})

@app.route("/api/stop/<service>", methods=["POST"])
def stop_service(service):
    if service == "llama":
        os.system("pkill -f 'llama-server.*llm-models'")
    elif service == "text2speach":
        os.system("pkill -f 'llama-server.*audio-models'")
    elif service == "comfyui":
        # Only kill if NOT a wan_video session
        try:
            os.remove('/tmp/wan_video_active')
        except FileNotFoundError:
            pass
        os.system("pkill -f 'ComfyUI/[m]ain.py'")
    elif service == "wan_video":
        # Remove sentinel and kill the process
        try:
            os.remove('/tmp/wan_video_active')
        except FileNotFoundError:
            pass
        os.system("pkill -f 'ComfyUI/[m]ain.py'")
    elif service == "musicgen":
        os.system("pkill -f '[m]usic_app.py'")
    elif service == "xtts":
        os.system("docker stop xtts_server 2>/dev/null || true")
    else:
        return jsonify({"error": "Unknown service"}), 400

    return jsonify({"status": "stopped"})

@app.route("/api/logs/<service>")
def get_logs(service):
    log_path = f"/tmp/{service}_spawn.log"
    if not os.path.exists(log_path):
        return jsonify({"logs": ""})
    try:
        # Read the last 200 lines to avoid massive payloads
        # We can use tail for simplicity via subprocess, or readlines.
        # Reading lines in python is safer.
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return jsonify({"logs": "".join(lines[-200:])})
    except Exception as e:
        return jsonify({"logs": f"Error reading logs: {str(e)}"})

@app.route("/api/config", methods=["GET", "POST"])
def config_api():
    if request.method == "POST":
        if request.is_json:
            save_config(request.get_json())
            return jsonify({"status": "saved"})
        return jsonify({"error": "Invalid format"}), 400
    return jsonify(load_config())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
