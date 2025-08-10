
from gpiozero import Button
from gpiozero.pins.lgpio import LGPIOFactory  # ← add this


from signal import pause
from pathlib import Path
import os
import re
import sys
import time
import queue
import sounddevice as sd
import wave
import json
from vosk import Model, KaldiRecognizer
from modules.llm_handler import LLMHandler
from piper_tts import synthesize_to_file

# Project root = folder where THIS file lives
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))  # so "modules/..." imports work anywhere

# === Settings ===
TMP_AUDIO = (PROJECT_ROOT / "tts_output")
TMP_AUDIO.mkdir(parents=True, exist_ok=True)
PAUSE = 1


# === Settings ===

MODEL_PATH = str(PROJECT_ROOT / "models" / "vosk-model-small-en-us-0.15")
SAMPLE_RATE = 16000
BLOCK_SIZE = 8000



# === Instantiate once ===
print("🧠 Initializing models…")
vosk_model = Model(MODEL_PATH)
llm = LLMHandler(provider="ollama", model="gemma3:1b")

conversation = [
    {"role": "system", "content": "You are a helpful AI assistant. Answer short and friendly."}
]

# === Helpers ===
def speak(text: str, filename: str):
    path = TMP_AUDIO / filename
    print("path: ", path)
    synthesize_to_file(text, path)
    print(f"🔊 {text}")
    os.system(f"aplay {path}")
    time.sleep(PAUSE)

def transcribe_recording(wav_path: Path) -> str:
    rec = KaldiRecognizer(vosk_model, SAMPLE_RATE)
    with wave.open(str(wav_path), "rb") as wf:
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            rec.AcceptWaveform(data)
    result = json.loads(rec.FinalResult())
    text = result.get("text", "")
    print(f"📝 Transcribed: {text}")
    return text

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
    print("🎙️ Recording… hold button to keep talking.")
    while button.is_pressed:
        data = q.get()
        wf.writeframes(data)

    stream.stop()
    stream.close()
    wf.close()
    print("🛑 Recording stopped.")
    return rec_file




def stream_and_speak(conversation: list, llm, tmp_audio_dir: Path, prefix: str = "response", temperature: float = 0.7):
    """
    Streams LLM response and speaks it sentence-by-sentence as it comes in.

    Args:
        conversation (list): Current conversation list with system/user/assistant turns
        llm (LLMHandler): Your LLM handler instance
        tmp_audio_dir (Path): Directory to store temporary audio files
        prefix (str): Prefix for audio filenames
        temperature (float): LLM generation temperature
    Returns:
        str: Full response from the assistant
    """
    buffer = ""
    sentence_id = 0
    full_response_parts = []

    sentence_end_pattern = re.compile(r"(.*?[\.!?])\s")  # full thought

    print("🤖 Streaming response…")
    for chunk in llm.stream(conversation, temperature=temperature):
        content = chunk.get("content", "")
        if not content:
            continue
        print(content, end="", flush=True)
        buffer += content
        full_response_parts.append(content)

        # extract full sentences
        while True:
            match = sentence_end_pattern.match(buffer)
            if not match:
                break
            sentence = match.group(1).strip()
            buffer = buffer[len(match.group(0)):]  # remove spoken part
            if sentence:
                sentence_id += 1
                filename = f"{prefix}_{sentence_id}.wav"
                print("filename: ", filename)
                print("tmp_audio_dir: ", tmp_audio_dir)
                speak(sentence,filename)

    # speak any leftover buffer
    if buffer.strip():
        sentence_id += 1
        filename = f"{prefix}_{sentence_id}.wav"
        speak(buffer.strip(),filename)

    full_response = "".join(full_response_parts).strip()
    return full_response

# === Main Logic ===

def on_button_pressed():
    print("🎯 Button pressed. Listening…")
    audio = record_while_button_held()
    spoken_text = transcribe_recording(audio)
    print("🎯 spoken_text: ", spoken_text)

    if not spoken_text:
        speak("I didn’t catch anything. Please try again.", "no_input.wav")
        return

    conversation.append({"role": "user", "content": spoken_text})

    response = stream_and_speak(conversation, llm, TMP_AUDIO)
    conversation.append({"role": "assistant", "content": response})


def handle_button_event():
    q = queue.Queue()
    rec_file = TMP_AUDIO / "recording.wav"

    def callback(indata, frames, time, status):
        q.put(bytes(indata))

    stream = sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        dtype='int16',
        channels=1,
        callback=callback
    )
    wf = wave.open(str(rec_file), "wb")
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SAMPLE_RATE)

    print("🎯 Button pressed. Starting recording immediately…")
    stream.start()
    start_time = time.time()

    while button.is_pressed:
        data = q.get()
        wf.writeframes(data)

    duration = time.time() - start_time
    stream.stop()
    stream.close()
    wf.close()
    print(f"🛑 Recording stopped. Duration: {duration:.2f}s")

    if duration < 0.5:
        speak("Hello! I'm ready when you are.", "welcome.wav")
        return

    spoken_text = transcribe_recording(rec_file)
    print("🎯 spoken_text: ", spoken_text)

    if not spoken_text:
        speak("I didn’t catch anything. Please try again.", "no_input.wav")
        return

    conversation.append({"role": "user", "content": spoken_text})
    response = stream_and_speak(conversation, llm, TMP_AUDIO)
    conversation.append({"role": "assistant", "content": response})


# === Setup ===
def main():
    speak("Hello! I'm online and ready to hang out", "online.wav")
    button.when_pressed = handle_button_event

    print("📲 Tap or hold the button to talk.")
    pause()


# button = Button(3, pull_up=True)
#pin_factory = PiGPIOFactory()  # uses the pigpiod daemon
#button = Button(3, pull_up=True, pin_factory=pin_factory)
pin_factory = LGPIOFactory()
button = Button(3, pull_up=True, pin_factory=pin_factory)



if __name__ == "__main__":
    main()