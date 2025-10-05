#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Buttontalk Assistant — Deluxe Edition
-------------------------------------
A voice-triggered local assistant using:
 - gpiozero (button on GPIO 5)
 - Vosk (speech-to-text)
 - Piper (speech synthesis)
 - OpenAI (streaming LLM)
Now with: coloured logs + backlight pulse for "thinking"
"""

from gpiozero import Button
from gpiozero.pins.lgpio import LGPIOFactory
from signal import pause
from pathlib import Path
import os, sys, time, wave, queue, re, json, subprocess, shutil, signal, logging
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from colorama import Fore, Style, init as color_init
from piper_tts import synthesize_to_file
from modules.llm_handler import LLMHandler
from modules.display_handler import DisplayHandler

# === Setup ===
color_init(autoreset=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

PROJECT_ROOT = Path(__file__).resolve().parent
TMP_AUDIO = PROJECT_ROOT / "tts_output"
TMP_AUDIO.mkdir(parents=True, exist_ok=True)
MODEL_PATH = str(PROJECT_ROOT / "models" / "vosk-model-small-en-us-0.15")
SAMPLE_RATE = 16000
BLOCK_SIZE = 8000
PAUSE = 1.0

vosk_model = None
llm = None
conversation = [{"role": "system", "content": "You are a helpful and witty AI assistant."}]

# === Utility functions ===
def print_banner(text, color=Fore.CYAN):
    border = f"{color}{'═' * (len(text) + 4)}{Style.RESET_ALL}"
    print(f"\n{border}\n{color}║ {text} ║{Style.RESET_ALL}\n{border}\n")

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

    subprocess.run(cmd, capture_output=True, text=True)
    time.sleep(PAUSE)


def init_models():
    global vosk_model, llm
    if vosk_model is None:
        print_banner("🧠 Loading Vosk model...", Fore.YELLOW)
        vosk_model = Model(MODEL_PATH)
    if llm is None:
        print_banner("🤖 Initialising LLM handler...", Fore.MAGENTA)
        display.write("LLM Init - openai")
        llm = LLMHandler(provider="openai", model="gpt-4o-mini")
        display.write("Ready")


def transcribe_recording(wav_path: Path) -> str:
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


def record_audio_while_pressed(button: Button):
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
        print(Fore.CYAN + "🎙️ Recording… hold button to talk." + Style.RESET_ALL)
        start = time.time()
        while button.is_pressed:
            wf.writeframes(q.get())

    duration = time.time() - start
    print(Fore.CYAN + f"🛑 Recording stopped ({duration:.2f}s)" + Style.RESET_ALL)
    return rec_file, duration


def stream_and_speak(conversation, llm, tmp_audio_dir, prefix="response", temperature=0.7):
    """Stream the LLM response and speak sentence by sentence."""
    buffer = ""
    sentence_id = 0
    full_response_parts = []
    pattern = re.compile(r"(.*?[\.!?])\s")

    print(Fore.MAGENTA + "\n🤔 Thinking..." + Style.RESET_ALL)
    display.start_pulse(color=(0, 80, 255), speed=1.8)  # nice blue pulse

    display_buffer = ""
    for chunk in llm.stream(conversation, temperature=temperature):
        content = chunk.get("content", "")
        if not content:
            continue

        # --- Terminal output ---
        print(Fore.BLUE + content + Style.RESET_ALL, end="", flush=True)

        # --- Update display in real time ---
        display_buffer += content
        # Keep only last 32 chars (2×16 LCD)
        truncated = display_buffer[-32:]
        display.write(truncated)

        buffer += content
        full_response_parts.append(content)

        while match := pattern.match(buffer):
            sentence = match.group(1).strip()
            buffer = buffer[len(match.group(0)) :]
            if sentence:
                sentence_id += 1
                speak(sentence, f"{prefix}_{sentence_id}.wav")

    display.stop_pulse()  # stop pulsing when response done
    print(Fore.GREEN + "\n✅ Response complete!\n" + Style.RESET_ALL)

    if buffer.strip():
        sentence_id += 1
        speak(buffer.strip(), f"{prefix}_{sentence_id}.wav")

    return "".join(full_response_parts).strip()


def handle_button_event():
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


def shutdown_handler(sig, frame):
    print_banner("🧹 Shutting down gracefully…", Fore.YELLOW)
    display.off()
    try:
        speak("Goodbye!", "goodbye.wav")
    except Exception:
        pass
    sys.exit(0)


signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)


def main():
    print_banner("🚀 Starting Buttontalk Assistant", Fore.GREEN)
    display.fade_in(color=(0, 100, 255))
    display.write("Hello")
    speak("Hello! I'm online and ready to hang out.", "online.wav")
    button.when_pressed = handle_button_event
    print(Fore.CYAN + "📲 Tap or hold the button to talk.\n" + Style.RESET_ALL)
    pause()


# === Hardware init ===
pin_factory = LGPIOFactory()
button = Button(5, pull_up=True, pin_factory=pin_factory)
display = DisplayHandler()

if __name__ == "__main__":
    main()
