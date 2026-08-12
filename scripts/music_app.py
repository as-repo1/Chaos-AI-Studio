import gradio as gr
from transformers import AutoProcessor, MusicgenForConditionalGeneration
import scipy.io.wavfile
import torch
import numpy as np
import datetime
import os

print("Loading MusicGen-Small model (this might take a minute on first run)...")
processor = AutoProcessor.from_pretrained("facebook/musicgen-small")
model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")

def generate_music(prompt, duration):
    print(f"Generating music for prompt: '{prompt}' (Duration: {duration}s)")
    inputs = processor(
        text=[prompt],
        padding=True,
        return_tensors="pt",
    )
    
    # Calculate tokens needed (musicgen generates 50 tokens per second of audio)
    max_new_tokens = int(duration * 50)
    
    audio_values = model.generate(**inputs, max_new_tokens=max_new_tokens)
    sampling_rate = model.config.audio_encoder.sampling_rate
    
    audio_data = audio_values[0, 0].cpu().numpy()
    
    # Save the file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.expanduser(f"~/Music/ai-music/musicgen_{timestamp}.wav")
    scipy.io.wavfile.write(filename, rate=sampling_rate, data=audio_data)
    
    return (sampling_rate, audio_data)

with gr.Blocks(title="AI Music Generator") as demo:
    gr.Markdown("# 🎵 Local AI Music Generator")
    gr.Markdown("Uses Meta's MusicGen-Small to generate music directly on your computer.")
    
    with gr.Row():
        with gr.Column():
            prompt = gr.Textbox(label="Music Prompt", placeholder="e.g. 80s electronic track with melodic synthesizers, upbeat and driving", lines=3)
            duration = gr.Slider(minimum=5, maximum=30, value=10, step=1, label="Duration (Seconds)")
            generate_btn = gr.Button("Generate Music", variant="primary")
        
        with gr.Column():
            output_audio = gr.Audio(label="Generated Track")
    
    generate_btn.click(fn=generate_music, inputs=[prompt, duration], outputs=output_audio)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
