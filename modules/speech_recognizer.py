# speech_recognizer.py

import json
import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer

MODEL_PATH = "./models/vosk-model-small-en-us-0.15"  # Adjust if needed
SAMPLE_RATE = 16000
BLOCK_SIZE = 8000

# Load model once
model = Model(MODEL_PATH)

def listen_and_transcribe(duration: int = 5) -> str:
    """Record and transcribe speech for a given duration in seconds."""
    q = queue.Queue()

    def callback(indata, frames, time, status):
        if status:
            print(f"⚠️ {status}")
        q.put(bytes(indata))

    print("🎧 Listening... Speak now!")
    rec = KaldiRecognizer(model, SAMPLE_RATE)
    result_text = []

    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE, dtype='int16',
                           channels=1, callback=callback):
        for _ in range(int(SAMPLE_RATE / BLOCK_SIZE * duration)):
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                result_text.append(result.get("text", ""))

    final = json.loads(rec.FinalResult()).get("text", "")
    result_text.append(final)

    full_result = " ".join(result_text).strip()
    print(f"🗣️ Heard: {full_result}")
    return full_result
