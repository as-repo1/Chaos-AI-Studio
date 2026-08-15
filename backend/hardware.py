import os
import psutil
import subprocess

def get_gpu_info():
    info = {
        "gpu_percent": 0,
        "vram_percent": 0,
        "vram_used_gb": 0.0,
        "vram_total_gb": 4.0,
    }
    try:
        base = "/sys/class/drm/card0/device"
        used_p = os.path.join(base, "mem_info_vram_used")
        total_p = os.path.join(base, "mem_info_vram_total")
        if os.path.exists(used_p) and os.path.exists(total_p):
            with open(used_p) as f:
                used = int(f.read().strip())
            with open(total_p) as f:
                total = int(f.read().strip())
            info["vram_used_gb"] = round(used / (1024**3), 2)
            info["vram_total_gb"] = round(total / (1024**3), 2)
            if total > 0:
                info["vram_percent"] = round((used / total) * 100, 1)
        busy_p = os.path.join(base, "gpu_busy_percent")
        if os.path.exists(busy_p):
            with open(busy_p) as f:
                info["gpu_percent"] = int(f.read().strip())
    except Exception:
        pass
    return info

def get_vulkan_devices():
    """Parse vulkaninfo --summary and return backends including CPU."""
    devices = [{"index": -1, "name": "CPU Only", "type": "cpu", "value": "cpu"}]
    try:
        out = subprocess.check_output(
            ["vulkaninfo", "--summary"], stderr=subprocess.DEVNULL, timeout=5
        ).decode()
        idx = 0
        name = None
        dtype = ""
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("deviceType"):
                dtype = line.split("=")[-1].strip()
            elif line.startswith("deviceName"):
                name = line.split("=")[-1].strip()
                label = name
                if "DISCRETE" in dtype.upper():
                    label += " (Dedicated)"
                elif "INTEGRATED" in dtype.upper():
                    label += " (Integrated)"
                devices.append(
                    {
                        "index": idx,
                        "name": label,
                        "type": dtype,
                        "value": f"vulkan:{idx}",
                    }
                )
                idx += 1
                name = None
    except Exception:
        pass
    return devices
