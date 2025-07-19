# piper_tts.py
import wave
from pathlib import Path
from piper.voice import PiperVoice

MODEL_PATH = Path("./voices/en_US-lessac-medium.onnx")  # adjust if needed
CONFIG_PATH = MODEL_PATH.with_suffix(".onnx.json")

voice = PiperVoice.load(str(MODEL_PATH), config_path=str(CONFIG_PATH))

def synthesize_to_file(text: str, output_path: Path) -> Path:
    with wave.open(str(output_path), "w") as wav_file:
        voice.synthesize(text, wav_file)
    return output_path
