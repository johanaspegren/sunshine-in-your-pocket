from gpiozero import Button
from signal import pause
from pathlib import Path
import os
import time
import queue
import sounddevice as sd
import wave
from vosk import Model, KaldiRecognizer
from modules.llm_handler import LLMHandler
from piper_tts import synthesize_to_file

# === Settings ===
TMP_AUDIO = Path("./tts_output")
TMP_AUDIO.mkdir(exist_ok=True)
PAUSE = 1

MODEL_PATH = "./models/vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000
BLOCK_SIZE = 8000

# === Helpers ===
def speak(text: str, filename: str):
    path = TMP_AUDIO / filename
    synthesize_to_file(text, path)
    print(f"🔊 {text}")
    os.system(f"aplay {path}")
    time.sleep(PAUSE)

def transcribe_recording(wav_path: Path) -> str:
    model = Model(MODEL_PATH)
    rec = KaldiRecognizer(model, SAMPLE_RATE)
    with wave.open(str(wav_path), "rb") as wf:
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            rec.AcceptWaveform(data)
    result = rec.FinalResult()
    text = eval(result).get("text", "")
    print(f"📝 Transcribed: {text}")
    return text

# === Recording Logic ===
def record_while_button_held():
    q = queue.Queue()
    rec_file = TMP_AUDIO / "recording.wav"

    def callback(indata, frames, time, status):
        q.put(bytes(indata))

    stream = sd.RawInputStream(samplerate=SAMPLE_RATE,
                               blocksize=BLOCK_SIZE,
                               dtype='int16',
                               channels=1,
                               callback=callback)
    wf = wave.open(str(rec_file), "wb")
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SAMPLE_RATE)

    stream.start()
    print("🎙️ Recording... hold button to keep talking.")
    while button.is_pressed:
        data = q.get()
        wf.writeframes(data)

    stream.stop()
    stream.close()
    wf.close()
    print("🛑 Recording stopped.")
    return rec_file

# === Main Logic ===
def on_button_pressed():
    print("🎯 Button pressed. Listening...")
    audio = record_while_button_held()
    spoken_text = transcribe_recording(audio)
    print("🎯 spoken_text: ", spoken_text)

    if not spoken_text:
        speak("I didn’t catch anything. Please try again.", "no_input.wav")
        return

    llm = LLMHandler(provider="ollama", model="gemma3:1b")
    response = llm.call(spoken_text).strip()
    print(f"🤖 Response: {response}")
    speak(response, "response.wav")

# === Setup ===
button = Button(3, pull_up=True)
button.when_pressed = on_button_pressed

print("📲 Hold the button to talk.")
pause()
