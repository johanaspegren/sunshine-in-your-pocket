#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Buttontalk Assistant — Refined Edition
--------------------------------------
A voice-triggered local assistant using:
 - gpiozero (button on GPIO 5)
 - Vosk (speech-to-text)
 - Piper (speech synthesis)
 - Your LLMHandler for streaming responses
"""

from gpiozero import Button
from gpiozero.pins.lgpio import LGPIOFactory
from signal import pause
from pathlib import Path
import os, sys, time, wave, queue, re, json, subprocess, shutil, signal, logging
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from piper_tts import synthesize_to_file
from modules.llm_handler import LLMHandler
from modules.display_handler import DisplayHandler


# === Setup logging ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# === Paths ===
PROJECT_ROOT = Path(__file__).resolve().parent
TMP_AUDIO = PROJECT_ROOT / "tts_output"
TMP_AUDIO.mkdir(parents=True, exist_ok=True)

MODEL_PATH = str(PROJECT_ROOT / "models" / "vosk-model-small-en-us-0.15")
SAMPLE_RATE = 16000
BLOCK_SIZE = 8000
PAUSE = 1.0

# === Globals ===
vosk_model = None
llm = None
conversation = [{"role": "system", "content": "You are a helpful AI assistant. Answer short and friendly."}]


# === Utility functions ===
def speak(text: str, filename: str):
    """Convert text to speech and play."""
    path = TMP_AUDIO / filename
    synthesize_to_file(text, path)
    logging.info(f"🔊 Speaking: {text}")

    if shutil.which("paplay"):
        cmd = ["paplay", str(path)]
    else:
        dev = os.getenv("APLAY_DEVICE", "default")
        cmd = ["aplay", "-q", "-D", dev, str(path)]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        logging.warning(f"Audio playback error: {r.stderr.strip()}")
    time.sleep(PAUSE)


def init_models():
    """Lazy-load heavy models."""
    global vosk_model, llm
    if vosk_model is None:
        logging.info("🧠 Loading Vosk model...")
        vosk_model = Model(MODEL_PATH)
    if llm is None:
        logging.info("🤖 Initializing LLM handler...")
        llm = LLMHandler(provider="ollama", model="gemma3:1b")


def transcribe_recording(wav_path: Path) -> str:
    """Transcribe recorded audio to text."""
    rec = KaldiRecognizer(vosk_model, SAMPLE_RATE)
    with wave.open(str(wav_path), "rb") as wf:
        while True:
            data = wf.readframes(4000)
            if not data:
                break
            rec.AcceptWaveform(data)
    result = json.loads(rec.FinalResult())
    text = result.get("text", "").strip()
    display.write(text)
    logging.info(f"📝 Transcribed: {text}")
    return text


def record_audio_while_pressed(button: Button) -> Path:
    """Record audio while button is held."""
    q = queue.Queue()
    rec_file = TMP_AUDIO / "recording.wav"

    def callback(indata, frames, time_info, status):
        q.put(bytes(indata))

    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        dtype="int16",
        channels=1,
        callback=callback,
    ), wave.open(str(rec_file), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)

        logging.info("🎙️ Recording… hold button to talk.")
        start = time.time()
        while button.is_pressed:
            wf.writeframes(q.get())

    duration = time.time() - start
    logging.info(f"🛑 Recording stopped ({duration:.2f}s)")
    return rec_file, duration


def stream_and_speak(conversation, llm, tmp_audio_dir, prefix="response", temperature=0.7):
    """Stream the LLM response and speak sentence by sentence."""
    buffer = ""
    sentence_id = 0
    full_response_parts = []
    pattern = re.compile(r"(.*?[\.!?])\s")

    logging.info("🤖 Streaming LLM response…")
    for chunk in llm.stream(conversation, temperature=temperature):
        content = chunk.get("content", "")
        if not content:
            continue
        print(content, end="", flush=True)
        buffer += content
        full_response_parts.append(content)

        # Speak complete sentences
        while match := pattern.match(buffer):
            sentence = match.group(1).strip()
            buffer = buffer[len(match.group(0)) :]
            if sentence:
                sentence_id += 1
                speak(sentence, f"{prefix}_{sentence_id}.wav")

    if buffer.strip():
        sentence_id += 1
        speak(buffer.strip(), f"{prefix}_{sentence_id}.wav")

    return "".join(full_response_parts).strip()


def handle_button_event():
    """Triggered when the button is pressed."""
    init_models()
    rec_file, duration = record_audio_while_pressed(button)

    if duration < 0.5:
        speak("Hello! I'm ready when you are.", "welcome.wav")
        return

    spoken_text = transcribe_recording(rec_file)
    if not spoken_text:
        speak("I didn’t catch anything. Please try again.", "no_input.wav")
        return

    conversation.append({"role": "user", "content": spoken_text})
    response = stream_and_speak(conversation, llm, TMP_AUDIO)
    conversation.append({"role": "assistant", "content": response})


# === Setup and cleanup ===
def shutdown_handler(sig, frame):
    logging.info("🧹 Shutting down gracefully…")
    try:
        speak("Goodbye!", "goodbye.wav")
    except Exception:
        pass
    sys.exit(0)


signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)


def main():
    logging.info("🚀 Starting Buttontalk Assistant")
    display.write("Hello")
    speak("Hello! I'm online and ready to hang out.", "online.wav")
    button.when_pressed = handle_button_event
    logging.info("📲 Tap or hold the button to talk.")
    pause()


# === Initialize button on GPIO5 ===
pin_factory = LGPIOFactory()
button = Button(5, pull_up=True, pin_factory=pin_factory)
display = DisplayHandler()

if __name__ == "__main__":
    main()
