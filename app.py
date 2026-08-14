import os
import subprocess
import psutil
import json
import threading
import time
import urllib.request
from flask import Flask, render_template, jsonify, request, Response, stream_with_context
from pathlib import Path

app = Flask(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
HOME_DIR        = str(Path.home())
SCRIPTS_DIR     = os.path.join(HOME_DIR, "Chaos-AI-Studio", "scripts")
MODELS_DIR      = os.path.join(HOME_DIR, "models")
CONFIG_PATH     = os.path.join(HOME_DIR, "Chaos-AI-Studio", "config.json")
LLAMA_BIN       = os.path.join(HOME_DIR, "Chaos-AI-Studio", "llama.cpp-src", "build", "bin", "llama-server")

# ── Config ────────────────────────────────────────────────────────────────────
def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "llama":       {"ctx_size": 4096, "ngl": 99, "port": 8080, "threads": 4, "model": "", "vulkan_device": 0},
        "text2speach": {"ctx_size": 1024, "ngl": 99, "port": 8090, "threads": 4, "model": "vibevoice-1.5b-q4_k_m.gguf", "vulkan_device": 0},
        "comfyui":     {"lowvram": True,  "normalvram": False}
    }

def save_config(config_data):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config_data, f, indent=4)

# ── Service map ───────────────────────────────────────────────────────────────
script_map = {
    "llama":       "start_ai_stack.sh",
    "comfyui":     "start_comfyui.sh",
    "wan_video":   "start_comfyui.sh",
    "musicgen":    "start_musicgen.sh",
    "xtts":        "start_tts_server.sh",
    "text2speach": "start_text2speech.sh"
}

# Service health-check endpoints
HEALTH_URLS = {
    "llama":       "http://localhost:8080/health",
    "text2speach": "http://localhost:8090/health",
    "comfyui":     "http://localhost:8188/",
    "musicgen":    "http://localhost:7860/",
}

# ── Watchdog state ────────────────────────────────────────────────────────────
# { service_id: "stopped" | "starting" | "ready" | "crashed" }
service_state   = {s: "stopped" for s in script_map}
_was_running    = {s: False     for s in script_map}
_watchdog_lock  = threading.Lock()

def check_health(service):
    """Returns True if the service's HTTP endpoint responds OK."""
    url = HEALTH_URLS.get(service)
    if not url:
        return is_running(service)   # no health URL → fall back to process check
    try:
        req = urllib.request.urlopen(url, timeout=2)
        return req.status < 500
    except Exception:
        return False

def _watchdog_loop():
    """Background thread: detects crashes and upgrades starting→ready."""
    while True:
        time.sleep(8)
        with _watchdog_lock:
            for svc in list(script_map.keys()):
                proc_alive = is_running(svc)
                state      = service_state.get(svc, "stopped")

                if state == "starting":
                    if not proc_alive:
                        # process died before becoming ready
                        service_state[svc] = "crashed"
                    elif check_health(svc):
                        service_state[svc] = "ready"

                elif state == "ready":
                    if not proc_alive:
                        service_state[svc] = "crashed"

                elif state == "stopped":
                    # sanity: if something started externally
                    if proc_alive:
                        service_state[svc] = "ready"

_watchdog_thread = threading.Thread(target=_watchdog_loop, daemon=True)
_watchdog_thread.start()

# ── Process detection ─────────────────────────────────────────────────────────
def is_running(process_name):
    if process_name == "llama":
        return os.system('pgrep -f "[l]lama-server.*llm-models" > /dev/null 2>&1') == 0
    elif process_name == "text2speach":
        return os.system('pgrep -f "[l]lama-server.*audio-models" > /dev/null 2>&1') == 0
    elif process_name == "comfyui":
        is_comfy = os.system('pgrep -f "ComfyUI/[m]ain.py" > /dev/null 2>&1') == 0
        return is_comfy and not os.path.exists('/tmp/wan_video_active')
    elif process_name == "wan_video":
        is_comfy = os.system('pgrep -f "ComfyUI/[m]ain.py" > /dev/null 2>&1') == 0
        return is_comfy and os.path.exists('/tmp/wan_video_active')
    elif process_name == "musicgen":
        return os.system('pgrep -f "[m]usic_app.py" > /dev/null 2>&1') == 0
    elif process_name == "xtts":
        return os.system('docker ps 2>/dev/null | grep -q "[x]tts_server"') == 0
    return False

# ── Model helpers ─────────────────────────────────────────────────────────────
def list_gguf(subdir):
    d = os.path.join(MODELS_DIR, subdir)
    if not os.path.exists(d):
        return []
    return sorted(f for f in os.listdir(d) if f.endswith(".gguf"))

def get_models():
    models = []
    for subdir, mtype in [("llm-models","Text (GGUF)"), ("image-models","Image (Safetensors)"), ("video-models","Video (GGUF)")]:
        d = os.path.join(MODELS_DIR, subdir)
        if not os.path.exists(d): continue
        for f in os.listdir(d):
            if f.endswith((".gguf", ".safetensors")):
                size = os.path.getsize(os.path.join(d, f)) / (1024**3)
                models.append({"name": f, "type": mtype, "size": f"{size:.2f} GB"})
    return models

# ── Catalogue ─────────────────────────────────────────────────────────────────
CATALOGUE = [
    {"id":"llama-3-8b",    "name":"Llama 3 8B Instruct",    "type":"Text (GGUF)",       "description":"State-of-the-art 8B model. Perfect for coding and conversation.",              "url":"https://huggingface.co/lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf",          "filename":"Meta-Llama-3-8B-Instruct-Q4_K_M.gguf",        "category":"llm-models",   "size_gb": 4.9},
    {"id":"sdxl-turbo",    "name":"SDXL Turbo",              "type":"Image (Safetensors)","description":"Lightning-fast image generation. Creates images in 1-2 steps.",               "url":"https://huggingface.co/stabilityai/sdxl-turbo/resolve/main/sd_xl_turbo_1.0_fp16.safetensors",                                         "filename":"sd_xl_turbo_1.0_fp16.safetensors",             "category":"image-models", "size_gb": 6.9},
    {"id":"openhermes-2.5","name":"OpenHermes 2.5",          "type":"Text (GGUF)",       "description":"Capable uncensored chat model. Excellent for roleplay and creative writing.", "url":"https://huggingface.co/TheBloke/OpenHermes-2.5-Mistral-7B-GGUF/resolve/main/openhermes-2.5-mistral-7b.Q4_K_M.gguf",                   "filename":"openhermes-2.5-mistral-7b.Q4_K_M.gguf",        "category":"llm-models",   "size_gb": 4.4},
    {"id":"animagine-xl",  "name":"Animagine XL 3.1",        "type":"Image (Safetensors)","description":"Best anime-style generation model available.",                               "url":"https://huggingface.co/cagliostrolab/animagine-xl-3.1/resolve/main/animagine-xl-3.1.safetensors",                                      "filename":"animagine-xl-3.1.safetensors",                 "category":"image-models", "size_gb": 6.6},
    {"id":"wan-video-1.3b","name":"Wan2.1 (1.3B)",           "type":"Video (Safetensors)","description":"Text-to-video model. Requires ComfyUI.",                                    "url":"https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B/resolve/main/models_t2v_1.3B/diffusion_pytorch_model.safetensors",                      "filename":"wan2.1_t2v_1.3b.safetensors",                  "category":"video-models", "size_gb": 2.8},
    {"id":"qwen2.5-1.5b",  "name":"Qwen 2.5 (1.5B)",         "type":"Text (GGUF)",       "description":"Smart SLM — easily runs on 4GB VRAM.",                                      "url":"https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",                             "filename":"qwen2.5-1.5b-instruct-q4_k_m.gguf",            "category":"llm-models",   "size_gb": 1.0},
    {"id":"deepseek-r1-7b","name":"DeepSeek R1 (7B)",         "type":"Text (GGUF)",       "description":"Excellent reasoning model for code and complex queries.",                    "url":"https://huggingface.co/TheBloke/deepseek-coder-6.7B-instruct-GGUF/resolve/main/deepseek-coder-6.7b-instruct.Q4_K_M.gguf",             "filename":"deepseek-coder-6.7b-instruct.Q4_K_M.gguf",     "category":"llm-models",   "size_gb": 4.1},
    {"id":"llava-1.5-7b",  "name":"LLaVA 1.5 (7B)",          "type":"Multimodal (GGUF)", "description":"Vision-language model. Upload an image and chat about its contents.",        "url":"https://huggingface.co/mys/ggml_llava-v1.5-7b/resolve/main/ggml-model-q4_k.gguf",                                                     "filename":"ggml-model-q4_k.gguf",                         "category":"llm-models",   "size_gb": 4.1},
    {"id":"nomic-embed",   "name":"Nomic Embed Text v1.5",    "type":"Embedding (GGUF)",  "description":"High-performance embedding model for RAG.",                                  "url":"https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF/resolve/main/nomic-embed-text-v1.5.Q4_K_M.gguf",                          "filename":"nomic-embed-text-v1.5.Q4_K_M.gguf",            "category":"llm-models",   "size_gb": 0.3},
    {"id":"bark-small",    "name":"Suno Bark (Small)",        "type":"Audio (PyTorch)",   "description":"Expressive TTS capable of non-speech sounds.",                              "url":"https://huggingface.co/suno/bark-small/resolve/main/pytorch_model.bin",                                                                 "filename":"pytorch_model.bin",                            "category":"audio-models", "size_gb": 0.9},
]

# Track active downloads: { model_id: { proc, target_path, total_bytes } }
downloads = {}

# ── GPU helpers ───────────────────────────────────────────────────────────────
def get_gpu_info():
    info = {"gpu_percent": 0, "vram_percent": 0, "vram_used_gb": 0.0, "vram_total_gb": 4.0}
    try:
        base = "/sys/class/drm/card0/device"
        used_p = os.path.join(base, "mem_info_vram_used")
        total_p = os.path.join(base, "mem_info_vram_total")
        if os.path.exists(used_p) and os.path.exists(total_p):
            with open(used_p) as f: used  = int(f.read().strip())
            with open(total_p) as f: total = int(f.read().strip())
            info["vram_used_gb"]  = round(used  / (1024**3), 2)
            info["vram_total_gb"] = round(total / (1024**3), 2)
            if total > 0:
                info["vram_percent"] = round((used / total) * 100, 1)
        busy_p = os.path.join(base, "gpu_busy_percent")
        if os.path.exists(busy_p):
            with open(busy_p) as f: info["gpu_percent"] = int(f.read().strip())
    except Exception:
        pass
    return info

def get_vulkan_devices():
    """Parse vulkaninfo --summary to list GPU devices."""
    devices = []
    try:
        out = subprocess.check_output(["vulkaninfo", "--summary"], stderr=subprocess.DEVNULL, timeout=5).decode()
        idx = 0
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("deviceName"):
                name = line.split("=")[-1].strip()
                devices.append({"index": idx, "name": name})
                idx += 1
    except Exception:
        pass
    return devices

# ── Routes — Pages ────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/models")
def models_page():
    return render_template("models.html")

@app.route("/chat")
def chat_page():
    return render_template("chat.html")

@app.route("/tts")
def tts_page():
    return render_template("tts.html")

# ── Routes — API ──────────────────────────────────────────────────────────────
@app.route("/api/status")
def status():
    result = {}
    for name in script_map:
        proc_alive = is_running(name)
        state = service_state.get(name, "stopped")
        # Sync state with reality
        if not proc_alive and state not in ("stopped", "crashed"):
            with _watchdog_lock:
                service_state[name] = "stopped"
                state = "stopped"
        result[name] = {
            "running": proc_alive,
            "state":   state,     # stopped | starting | ready | crashed
        }
    return jsonify(result)

@app.route("/api/models")
def list_models():
    return jsonify(get_models())

@app.route("/api/models/text")
def get_text_models():
    return jsonify(list_gguf("llm-models"))

@app.route("/api/models/audio")
def get_audio_models():
    return jsonify(list_gguf("audio-models"))

@app.route("/api/gpu/devices")
def gpu_devices():
    return jsonify(get_vulkan_devices())

@app.route("/api/catalogue")
def catalogue():
    result = []
    for item in CATALOGUE:
        target_path = os.path.join(MODELS_DIR, item["category"], item["filename"])
        dl = downloads.get(item["id"])
        is_dl = dl is not None and dl["proc"].poll() is None
        percent = 0
        if is_dl:
            try:
                got = os.path.getsize(target_path) if os.path.exists(target_path) else 0
                total = dl.get("total_bytes", 0)
                percent = round((got / total * 100), 1) if total else 0
            except Exception:
                pass
        result.append({
            **item,
            "is_downloading": is_dl,
            "is_downloaded":  os.path.exists(target_path),
            "dl_percent":     percent,
        })
    return jsonify(result)

@app.route("/api/download/<model_id>", methods=["POST"])
def download_model(model_id):
    model = next((m for m in CATALOGUE if m["id"] == model_id), None)
    if not model:
        return jsonify({"error": "Model not found"}), 404
    target_dir  = os.path.join(MODELS_DIR, model["category"])
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, model["filename"])
    if os.path.exists(target_path):
        return jsonify({"error": "Already downloaded"}), 400
    dl = downloads.get(model_id)
    if dl and dl["proc"].poll() is None:
        return jsonify({"error": "Already downloading"}), 400
    # Use wget with content-length for progress tracking
    proc = subprocess.Popen(
        ["wget", "--quiet", "-O", target_path, model["url"]],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    downloads[model_id] = {
        "proc":        proc,
        "target_path": target_path,
        "total_bytes": int(model.get("size_gb", 0) * 1024**3),
    }
    return jsonify({"status": "started"})

@app.route("/api/system")
def get_system():
    ram  = psutil.virtual_memory()
    swap = psutil.swap_memory()
    gpu  = get_gpu_info()
    return jsonify({
        "cpu_percent":    psutil.cpu_percent(interval=0.1),
        "ram_percent":    ram.percent,
        "ram_used_gb":    round(ram.used  / (1024**3), 2),
        "ram_total_gb":   round(ram.total / (1024**3), 2),
        "swap_percent":   swap.percent,
        "swap_used_gb":   round(swap.used  / (1024**3), 2),
        "swap_total_gb":  round(swap.total / (1024**3), 2),
        "gpu_percent":    gpu["gpu_percent"],
        "gpu_used_gb":    gpu["vram_used_gb"],
        "gpu_total_gb":   gpu["vram_total_gb"],
        "gpu_vram_percent": gpu["vram_percent"],
    })

@app.route("/api/start/<service>", methods=["POST"])
def start_service(service):
    if service not in script_map:
        return jsonify({"error": "Invalid service"}), 400

    heavy = ["llama", "comfyui", "wan_video", "text2speach"]
    if service in heavy:
        running_heavy = [s for s in heavy if s != service and is_running(s)]
        if running_heavy:
            names = {"llama":"Text AI","comfyui":"Image AI","wan_video":"Video AI","text2speach":"TTS"}
            return jsonify({"error": f"VRAM conflict: stop {names.get(running_heavy[0], running_heavy[0])} first."}), 400

    if is_running(service):
        return jsonify({"status": "already running"})

    config      = load_config()
    script_env  = os.environ.copy()
    script_path = os.path.join(SCRIPTS_DIR, script_map[service])

    if service == "llama":
        cfg = config.get("llama", {})
        # Auto-pick first model if none configured
        model = cfg.get("model", "")
        if not model:
            available = list_gguf("llm-models")
            model = available[0] if available else ""
        if not model:
            return jsonify({"error": "No LLM model found in ~/models/llm-models/"}), 400
        script_env["MODEL_PATH"]    = os.path.join(MODELS_DIR, "llm-models", model)
        script_env["CTX_SIZE"]      = str(cfg.get("ctx_size", 4096))
        script_env["NGL"]           = str(cfg.get("ngl", 99))
        script_env["LLAMA_PORT"]    = str(cfg.get("port", 8080))
        script_env["THREADS"]       = str(cfg.get("threads", 4))
        script_env["VULKAN_DEVICE"] = str(cfg.get("vulkan_device", 0))

    elif service == "text2speach":
        cfg   = config.get("text2speach", {})
        model = cfg.get("model", "vibevoice-1.5b-q4_k_m.gguf")
        script_env["MODEL_PATH"]    = os.path.join(MODELS_DIR, "audio-models", model)
        script_env["CTX_SIZE"]      = str(cfg.get("ctx_size", 1024))
        script_env["NGL"]           = str(cfg.get("ngl", 99))
        script_env["TTS_PORT"]      = str(cfg.get("port", 8090))
        script_env["THREADS"]       = str(cfg.get("threads", 4))
        script_env["VULKAN_DEVICE"] = str(cfg.get("vulkan_device", 0))

    elif service == "comfyui":
        try: os.remove('/tmp/wan_video_active')
        except FileNotFoundError: pass
        cfg = config.get("comfyui", {})
        script_env["COMFYUI_ARGS"] = "--lowvram" if cfg.get("lowvram", True) else ("--normalvram" if cfg.get("normalvram") else "")

    elif service == "wan_video":
        open('/tmp/wan_video_active', 'w').close()
        script_env["COMFYUI_ARGS"] = "--lowvram --fp16-vae --fp8_e4m3fn-text-enc"

    # Mark as starting before launching
    with _watchdog_lock:
        service_state[service] = "starting"

    log_path = f"/tmp/{service}_spawn.log"
    with open(log_path, "w") as lf:
        lf.write(f"Starting {service} with cmd: ['bash', '{script_path}']\n")
        lf.flush()
        subprocess.Popen(["bash", script_path], cwd=HOME_DIR,
                         stdout=lf, stderr=subprocess.STDOUT,
                         env=script_env, close_fds=True)
    return jsonify({"status": "started"})

@app.route("/api/stop/<service>", methods=["POST"])
def stop_service(service):
    kill_map = {
        "llama":       "pkill -f 'llama-server.*llm-models'",
        "text2speach": "pkill -f 'llama-server.*audio-models'",
        "comfyui":     "pkill -f 'ComfyUI/[m]ain.py'",
        "wan_video":   "pkill -f 'ComfyUI/[m]ain.py'",
        "musicgen":    "pkill -f '[m]usic_app.py'",
        "xtts":        "docker stop xtts_server 2>/dev/null || true",
    }
    if service not in kill_map:
        return jsonify({"error": "Unknown service"}), 400
    # Clean sentinel for wan_video / comfyui
    if service in ("wan_video", "comfyui"):
        try: os.remove('/tmp/wan_video_active')
        except FileNotFoundError: pass
    os.system(kill_map[service])
    with _watchdog_lock:
        service_state[service] = "stopped"
    return jsonify({"status": "stopped"})

@app.route("/api/logs/<service>")
def get_logs(service):
    log_path = f"/tmp/{service}_spawn.log"
    if not os.path.exists(log_path):
        return jsonify({"logs": ""})
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return jsonify({"logs": "".join(lines[-200:])})
    except Exception as e:
        return jsonify({"logs": f"Error reading logs: {e}"})

@app.route("/api/config", methods=["GET", "POST"])
def config_api():
    if request.method == "POST":
        if request.is_json:
            save_config(request.get_json())
            return jsonify({"status": "saved"})
        return jsonify({"error": "Invalid format"}), 400
    return jsonify(load_config())

# ── Chat proxy (streaming SSE) ─────────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def chat():
    if not request.is_json:
        return jsonify({"error": "JSON required"}), 400
    payload = request.get_json()
    cfg     = load_config().get("llama", {})
    port    = cfg.get("port", 8080)
    url     = f"http://localhost:{port}/v1/chat/completions"

    # Always stream
    payload["stream"] = True

    data_bytes = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data_bytes,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    def generate():
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                for chunk in resp:
                    yield chunk
        except Exception as e:
            yield f"data: {{\"error\": \"{e}\"}}\n\n".encode()

    return Response(stream_with_context(generate()),
                    content_type="text/event-stream",
                    headers={"X-Accel-Buffering": "no"})

# ── TTS proxy ─────────────────────────────────────────────────────────────────
@app.route("/api/tts/speak", methods=["POST"])
def tts_speak():
    if not request.is_json:
        return jsonify({"error": "JSON required"}), 400
    payload = request.get_json()
    cfg  = load_config().get("text2speach", {})
    port = cfg.get("port", 8090)
    # llama.cpp TTS endpoint
    url  = f"http://localhost:{port}/tts/speech"
    body = json.dumps({"input": payload.get("text", ""), "voice": payload.get("voice", "")}).encode()
    req  = urllib.request.Request(url, data=body,
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            audio_data = resp.read()
        return Response(audio_data, content_type="audio/wav")
    except Exception as e:
        return jsonify({"error": str(e)}), 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
