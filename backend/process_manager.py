import os
import time
import urllib.request
import threading
import subprocess
import atexit
from backend.config import SCRIPTS_DIR, MODELS_DIR, load_config
from backend.models_manager import list_gguf

# ── Service map ───────────────────────────────────────────────────────────────
script_map = {
    "llama": "start_ai_stack.sh",
    "comfyui": "start_comfyui.sh",
    "wan_video": "start_comfyui.sh",
    "musicgen": "start_musicgen.sh",
    "xtts": "start_tts_server.sh",
    "text2speach": "start_text2speech.sh",
}

# Service health-check endpoints
HEALTH_URLS = {
    "llama": "http://localhost:8080/health",
    "text2speach": "http://localhost:8090/health",
    "comfyui": "http://localhost:8188/",
    "musicgen": "http://localhost:7860/",
}

# ── Watchdog state ────────────────────────────────────────────────────────────
service_state = {s: "stopped" for s in script_map}
_was_running = {s: False for s in script_map}
_watchdog_lock = threading.Lock()

def check_health(service):
    """Returns True if the service's HTTP endpoint responds OK."""
    url = HEALTH_URLS.get(service)
    if not url:
        return is_running(service)  # no health URL → fall back to process check
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
                state = service_state.get(svc, "stopped")

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

def start_watchdog():
    _watchdog_thread = threading.Thread(target=_watchdog_loop, daemon=True)
    _watchdog_thread.start()

# ── Process detection ─────────────────────────────────────────────────────────
def is_running(process_name):
    if process_name == "llama":
        return os.system('pgrep -f "[l]lama-server.*llm-models" > /dev/null 2>&1') == 0
    elif process_name == "text2speach":
        return (
            os.system('pgrep -f "[l]lama-server.*audio-models" > /dev/null 2>&1') == 0
        )
    elif process_name == "comfyui":
        is_comfy = os.system('pgrep -f "ComfyUI/[m]ain.py" > /dev/null 2>&1') == 0
        return is_comfy and not os.path.exists("/tmp/wan_video_active")
    elif process_name == "wan_video":
        is_comfy = os.system('pgrep -f "ComfyUI/[m]ain.py" > /dev/null 2>&1') == 0
        return is_comfy and os.path.exists("/tmp/wan_video_active")
    elif process_name == "musicgen":
        return os.system('pgrep -f "[m]usic_app.py" > /dev/null 2>&1') == 0
    elif process_name == "xtts":
        return os.system('docker ps 2>/dev/null | grep -q "[x]tts_server"') == 0
    return False

def start_service_logic(service):
    if service not in script_map:
        return {"error": "Invalid service"}, 400

    heavy = ["llama", "comfyui", "wan_video", "text2speach"]
    if service in heavy:
        running_heavy = [s for s in heavy if s != service and is_running(s)]
        if running_heavy:
            names = {
                "llama": "Text AI",
                "comfyui": "Image AI",
                "wan_video": "Video AI",
                "text2speach": "TTS",
            }
            return (
                {"error": f"VRAM conflict: stop {names.get(running_heavy[0], running_heavy[0])} first."},
                400,
            )

    if is_running(service):
        return {"status": "already running"}, 200

    config = load_config()
    script_env = os.environ.copy()
    script_path = os.path.join(SCRIPTS_DIR, script_map[service])

    if service == "llama":
        cfg = config.get("llama", {})
        model = cfg.get("model", "")
        if not model:
            available = list_gguf("llm-models")
            model = available[0] if available else ""
        if not model:
            return {"error": "No LLM model found in ~/models/llm-models/"}, 400
        script_env["MODEL_PATH"] = os.path.join(MODELS_DIR, "llm-models", model)
        script_env["CTX_SIZE"] = str(cfg.get("ctx_size", 4096))
        script_env["LLAMA_PORT"] = str(cfg.get("port", 8080))
        script_env["THREADS"] = str(cfg.get("threads", 4))
        # Compute backend: cpu | vulkan:0 | vulkan:1
        backend = cfg.get("compute_backend", "vulkan:0")
        if backend == "cpu":
            script_env["NGL"] = "0"
            script_env["VULKAN_DEVICE"] = "0"
        else:
            script_env["NGL"] = str(cfg.get("ngl", "auto"))
            script_env["VULKAN_DEVICE"] = str(
                backend.split(":")[-1]
                if ":" in backend
                else cfg.get("vulkan_device", 0)
            )

    elif service == "text2speach":
        cfg = config.get("text2speach", {})
        model = cfg.get("model", "vibevoice-1.5b-q4_k_m.gguf")
        script_env["MODEL_PATH"] = os.path.join(MODELS_DIR, "audio-models", model)
        script_env["CTX_SIZE"] = str(cfg.get("ctx_size", 1024))
        # Compute backend
        backend = cfg.get("compute_backend", "vulkan:0")
        if backend == "cpu":
            script_env["NGL"] = "0"
            script_env["VULKAN_DEVICE"] = "0"
        else:
            script_env["NGL"] = str(cfg.get("ngl", "auto"))
            script_env["VULKAN_DEVICE"] = str(
                backend.split(":")[-1]
                if ":" in backend
                else cfg.get("vulkan_device", 0)
            )
        script_env["TTS_PORT"] = str(cfg.get("port", 8090))
        script_env["THREADS"] = str(cfg.get("threads", 4))

    elif service == "comfyui":
        try:
            os.remove("/tmp/wan_video_active")
        except FileNotFoundError:
            pass
        cfg = config.get("comfyui", {})
        # Enforce --lowvram for ComfyUI to enable strict CPU offloading per user request
        script_env["COMFYUI_ARGS"] = "--lowvram"

    elif service == "wan_video":
        open("/tmp/wan_video_active", "w").close()
        script_env["COMFYUI_ARGS"] = "--lowvram --fp16-vae --fp8_e4m3fn-text-enc"

    # Mark as starting before launching
    with _watchdog_lock:
        service_state[service] = "starting"

    log_path = f"/tmp/{service}_spawn.log"
    with open(log_path, "w") as lf:
        lf.write(f"Starting {service} with cmd: ['bash', '{script_path}']\n")
        lf.flush()
        subprocess.Popen(
            ["bash", script_path],
            env=script_env,
            stdout=lf,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid,  # run in new process group to allow killing entirely
        )

    return {"status": "started"}, 200

def stop_service_logic(service):
    if service not in script_map:
        return {"error": "Invalid service"}, 400

    if service == "xtts":
        os.system("docker stop xtts_server")
    elif service == "llama":
        os.system('pkill -f "[l]lama-server.*llm-models"')
    elif service == "text2speach":
        os.system('pkill -f "[l]lama-server.*audio-models"')
    elif service in ("comfyui", "wan_video"):
        os.system('pkill -f "ComfyUI/[m]ain.py"')
    elif service == "musicgen":
        os.system('pkill -f "[m]usic_app.py"')

    with _watchdog_lock:
        service_state[service] = "stopped"

    return {"status": "stopped"}, 200

def cleanup_processes():
    """Kill all managed child AI services on exit"""
    print("Chaos-AI-Studio is shutting down. Cleaning up processes...")
    stop_service_logic("llama")
    stop_service_logic("text2speach")
    stop_service_logic("comfyui")
    stop_service_logic("musicgen")

atexit.register(cleanup_processes)
