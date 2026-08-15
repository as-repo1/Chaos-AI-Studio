import os
import json
import urllib.request
import urllib.parse
from flask import Blueprint, jsonify, request, Response, stream_with_context
from backend.config import load_config, save_config, MODELS_DIR
from backend.hardware import get_gpu_info, get_vulkan_devices
from backend.models_manager import get_models, list_gguf, CATALOGUE, downloads
from backend.process_manager import (
    script_map,
    service_state,
    is_running,
    _watchdog_lock,
    start_service_logic,
    stop_service_logic,
)
import psutil

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/status")
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
            "state": state,  # stopped | starting | ready | crashed
        }
    return jsonify(result)

@api_bp.route("/models")
def list_models_route():
    return jsonify(get_models())

@api_bp.route("/models/text")
def get_text_models():
    return jsonify(list_gguf("llm-models"))

@api_bp.route("/models/audio")
def get_audio_models():
    return jsonify(list_gguf("audio-models"))

@api_bp.route("/gpu/devices")
def gpu_devices():
    return jsonify(get_vulkan_devices())

@api_bp.route("/models/image")
def get_image_models():
    d = os.path.join(MODELS_DIR, "image-models")
    if not os.path.exists(d):
        return jsonify([])
    return jsonify(sorted(f for f in os.listdir(d) if f.endswith(".safetensors")))

@api_bp.route("/catalogue")
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
        result.append(
            {
                **item,
                "is_downloading": is_dl,
                "is_downloaded": os.path.exists(target_path),
                "dl_percent": percent,
            }
        )
    return jsonify(result)

@api_bp.route("/download/<model_id>", methods=["POST"])
def download_model(model_id):
    import subprocess
    model = next((m for m in CATALOGUE if m["id"] == model_id), None)
    if not model:
        return jsonify({"error": "Model not found"}), 404
    target_dir = os.path.join(MODELS_DIR, model["category"])
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
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    downloads[model_id] = {
        "proc": proc,
        "target_path": target_path,
        "total_bytes": int(model.get("size_gb", 0) * 1024**3),
    }
    return jsonify({"status": "started"})

@api_bp.route("/system")
def get_system():
    ram = psutil.virtual_memory()
    swap = psutil.swap_memory()
    gpu = get_gpu_info()
    return jsonify(
        {
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
            "gpu_vram_percent": gpu["vram_percent"],
        }
    )

@api_bp.route("/start/<service>", methods=["POST"])
def start_service(service):
    data, code = start_service_logic(service)
    return jsonify(data), code

@api_bp.route("/stop/<service>", methods=["POST"])
def stop_service(service):
    data, code = stop_service_logic(service)
    return jsonify(data), code

@api_bp.route("/logs/<service>")
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

@api_bp.route("/config", methods=["GET", "POST"])
def config_api():
    if request.method == "POST":
        if request.is_json:
            save_config(request.get_json())
            return jsonify({"status": "saved"})
        return jsonify({"error": "Invalid format"}), 400
    return jsonify(load_config())

@api_bp.route("/chat", methods=["POST"])
def chat():
    if not request.is_json:
        return jsonify({"error": "JSON required"}), 400
    payload = request.get_json()
    cfg = load_config().get("llama", {})
    port = cfg.get("port", 8080)
    url = f"http://localhost:{port}/v1/chat/completions"

    # Always stream
    payload["stream"] = True

    data_bytes = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    def generate():
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                for chunk in resp:
                    yield chunk
        except Exception as e:
            yield f'data: {{"error": "{e}"}}\n\n'.encode()

    return Response(
        stream_with_context(generate()),
        content_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},
    )

@api_bp.route("/tts/speak", methods=["POST"])
def tts_speak():
    if not request.is_json:
        return jsonify({"error": "JSON required"}), 400
    payload = request.get_json()
    cfg = load_config().get("text2speach", {})
    port = cfg.get("port", 8090)
    # llama.cpp TTS endpoint
    url = f"http://localhost:{port}/tts/speech"
    body = json.dumps(
        {"input": payload.get("text", ""), "voice": payload.get("voice", "")}
    ).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            audio_data = resp.read()
        return Response(audio_data, content_type="audio/wav")
    except Exception as e:
        return jsonify({"error": str(e)}), 503

COMFY_PORT = 8188

def _comfy_post(path, payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"http://localhost:{COMFY_PORT}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def _comfy_get(path):
    with urllib.request.urlopen(
        f"http://localhost:{COMFY_PORT}{path}", timeout=10
    ) as r:
        return json.loads(r.read())

@api_bp.route("/image/generate", methods=["POST"])
def image_generate():
    if not request.is_json:
        return jsonify({"error": "JSON required"}), 400
    d = request.get_json()

    prompt_text = d.get("prompt", "a beautiful landscape")
    negative_text = d.get("negative", "blurry, ugly, nsfw")
    model_filename = d.get("model", "")
    steps = int(d.get("steps", 20))
    cfg_scale = float(d.get("cfg", 7.0))
    width = int(d.get("width", 512))
    height = int(d.get("height", 512))
    seed = int(d.get("seed", -1))
    import random

    if seed == -1:
        seed = random.randint(0, 2**32 - 1)

    # If no model picked, use first available
    if not model_filename:
        avail = sorted(
            f
            for f in os.listdir(os.path.join(MODELS_DIR, "image-models"))
            if f.endswith(".safetensors")
        )
        if not avail:
            return (
                jsonify({"error": "No image models found in ~/models/image-models/"}),
                400,
            )
        model_filename = avail[0]

    # Standard KSampler txt2img workflow
    workflow = {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": model_filename},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt_text, "clip": ["4", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative_text, "clip": ["4", 1]},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg_scale,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "chaos-ai", "images": ["8", 0]},
        },
    }

    try:
        result = _comfy_post("/prompt", {"prompt": workflow})
        return jsonify({"prompt_id": result["prompt_id"], "seed": seed})
    except Exception as e:
        return jsonify({"error": f"ComfyUI error: {e}"}), 503

@api_bp.route("/image/status/<prompt_id>")
def image_status(prompt_id):
    """Poll ComfyUI queue + history for progress."""
    try:
        # Check if still in queue
        queue = _comfy_get("/queue")
        running = queue.get("queue_running", [])
        pending = queue.get("queue_pending", [])

        for item in running:
            if len(item) > 1 and item[1] == prompt_id:
                # Get step progress from /progress if available
                try:
                    prog = _comfy_get("/progress")
                    step = prog.get("value", 0)
                    max_step = prog.get("max", 1)
                    pct = round(step / max_step * 100) if max_step else 0
                    return jsonify(
                        {
                            "status": "running",
                            "step": step,
                            "max": max_step,
                            "percent": pct,
                        }
                    )
                except Exception:
                    return jsonify({"status": "running", "percent": 50})

        for item in pending:
            if len(item) > 1 and item[1] == prompt_id:
                return jsonify({"status": "queued", "percent": 0})

        # Not in queue — check history
        history = _comfy_get(f"/history/{prompt_id}")
        if prompt_id in history:
            outputs = history[prompt_id].get("outputs", {})
            images = []
            for node_id, node_out in outputs.items():
                for img in node_out.get("images", []):
                    images.append(img["filename"])
            if images:
                return jsonify({"status": "done", "percent": 100, "images": images})

        return jsonify({"status": "unknown", "percent": 0})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 503

@api_bp.route("/image/view/<filename>")
def image_view(filename):
    """Proxy image bytes from ComfyUI /view endpoint."""
    safe = urllib.parse.quote(filename)
    try:
        with urllib.request.urlopen(
            f"http://localhost:{COMFY_PORT}/view?filename={safe}&type=output",
            timeout=10,
        ) as r:
            data = r.read()
        return Response(data, content_type="image/png")
    except Exception as e:
        return jsonify({"error": str(e)}), 503
