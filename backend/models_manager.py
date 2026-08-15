import os
import subprocess
from backend.config import MODELS_DIR

# Track active downloads: { model_id: { proc, target_path, total_bytes } }
downloads = {}

CATALOGUE = [
    {
        "id": "llama-3-8b",
        "name": "Llama 3 8B Instruct",
        "type": "Text (GGUF)",
        "description": "State-of-the-art 8B model. Perfect for coding and conversation.",
        "url": "https://huggingface.co/lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf",
        "filename": "Meta-Llama-3-8B-Instruct-Q4_K_M.gguf",
        "category": "llm-models",
        "size_gb": 4.9,
    },
    {
        "id": "sdxl-turbo",
        "name": "SDXL Turbo",
        "type": "Image (Safetensors)",
        "description": "Lightning-fast image generation. Creates images in 1-2 steps.",
        "url": "https://huggingface.co/stabilityai/sdxl-turbo/resolve/main/sd_xl_turbo_1.0_fp16.safetensors",
        "filename": "sd_xl_turbo_1.0_fp16.safetensors",
        "category": "image-models",
        "size_gb": 6.9,
    },
    {
        "id": "openhermes-2.5",
        "name": "OpenHermes 2.5",
        "type": "Text (GGUF)",
        "description": "Capable uncensored chat model. Excellent for roleplay and creative writing.",
        "url": "https://huggingface.co/TheBloke/OpenHermes-2.5-Mistral-7B-GGUF/resolve/main/openhermes-2.5-mistral-7b.Q4_K_M.gguf",
        "filename": "openhermes-2.5-mistral-7b.Q4_K_M.gguf",
        "category": "llm-models",
        "size_gb": 4.4,
    },
    {
        "id": "animagine-xl",
        "name": "Animagine XL 3.1",
        "type": "Image (Safetensors)",
        "description": "Best anime-style generation model available.",
        "url": "https://huggingface.co/cagliostrolab/animagine-xl-3.1/resolve/main/animagine-xl-3.1.safetensors",
        "filename": "animagine-xl-3.1.safetensors",
        "category": "image-models",
        "size_gb": 6.6,
    },
    {
        "id": "wan-video-1.3b",
        "name": "Wan2.1 (1.3B)",
        "type": "Video (Safetensors)",
        "description": "Text-to-video model. Requires ComfyUI.",
        "url": "https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B/resolve/main/models_t2v_1.3B/diffusion_pytorch_model.safetensors",
        "filename": "wan2.1_t2v_1.3b.safetensors",
        "category": "video-models",
        "size_gb": 2.8,
    },
    {
        "id": "qwen2.5-1.5b",
        "name": "Qwen 2.5 (1.5B)",
        "type": "Text (GGUF)",
        "description": "Smart SLM — easily runs on 4GB VRAM.",
        "url": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "category": "llm-models",
        "size_gb": 1.0,
    },
    {
        "id": "deepseek-r1-7b",
        "name": "DeepSeek R1 (7B)",
        "type": "Text (GGUF)",
        "description": "Excellent reasoning model for code and complex queries.",
        "url": "https://huggingface.co/TheBloke/deepseek-coder-6.7B-instruct-GGUF/resolve/main/deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
        "filename": "deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
        "category": "llm-models",
        "size_gb": 4.1,
    },
    {
        "id": "llava-1.5-7b",
        "name": "LLaVA 1.5 (7B)",
        "type": "Multimodal (GGUF)",
        "description": "Vision-language model. Upload an image and chat about its contents.",
        "url": "https://huggingface.co/mys/ggml_llava-v1.5-7b/resolve/main/ggml-model-q4_k.gguf",
        "filename": "ggml-model-q4_k.gguf",
        "category": "llm-models",
        "size_gb": 4.1,
    },
    {
        "id": "nomic-embed",
        "name": "Nomic Embed Text v1.5",
        "type": "Embedding (GGUF)",
        "description": "High-performance embedding model for RAG.",
        "url": "https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF/resolve/main/nomic-embed-text-v1.5.Q4_K_M.gguf",
        "filename": "nomic-embed-text-v1.5.Q4_K_M.gguf",
        "category": "llm-models",
        "size_gb": 0.3,
    },
    {
        "id": "bark-small",
        "name": "Suno Bark (Small)",
        "type": "Audio (PyTorch)",
        "description": "Expressive TTS capable of non-speech sounds.",
        "url": "https://huggingface.co/suno/bark-small/resolve/main/pytorch_model.bin",
        "filename": "pytorch_model.bin",
        "category": "audio-models",
        "size_gb": 0.9,
    },
]

def list_gguf(subdir):
    d = os.path.join(MODELS_DIR, subdir)
    if not os.path.exists(d):
        return []
    return sorted(f for f in os.listdir(d) if f.endswith(".gguf"))


def get_models():
    models = []
    for subdir, mtype in [
        ("llm-models", "Text (GGUF)"),
        ("image-models", "Image (Safetensors)"),
        ("video-models", "Video (GGUF)"),
    ]:
        d = os.path.join(MODELS_DIR, subdir)
        if not os.path.exists(d):
            continue
        for f in os.listdir(d):
            if f.endswith((".gguf", ".safetensors")):
                size = os.path.getsize(os.path.join(d, f)) / (1024**3)
                models.append({"name": f, "type": mtype, "size": f"{size:.2f} GB"})
    return models
