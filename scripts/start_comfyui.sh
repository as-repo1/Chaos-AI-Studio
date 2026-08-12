#!/bin/bash
cd ~/ComfyUI
source venv/bin/activate

# Add our models directory to ComfyUI's search path if not already there
if [ ! -f "extra_model_paths.yaml" ]; then
    echo "a1111:" > extra_model_paths.yaml
    echo "    base_path: $HOME/models/image-models/" >> extra_model_paths.yaml
    echo "    checkpoints: ." >> extra_model_paths.yaml
fi

echo "Starting ComfyUI on Intel XPU..."
# ComfyUI natively detects XPU and will manage VRAM automatically
python main.py --use-pytorch-cross-attention
