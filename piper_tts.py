# piper_tts.py
from pathlib import Path
import wave
from piper.voice import PiperVoice

PROJECT = Path(__file__).resolve().parent
MODEL_PATH = (PROJECT / "voices" / "en_US-lessac-medium.onnx").resolve()
CONFIG_PATH = MODEL_PATH.with_suffix(".onnx.json")

voice = PiperVoice.load(str(MODEL_PATH), config_path=str(CONFIG_PATH))

def synthesize_to_file(text: str, output_path: Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wav:   # wave object, not plain file
        voice.synthesize_wav(text, wav)              # Piper sets header + writes PCM
    return output_path
