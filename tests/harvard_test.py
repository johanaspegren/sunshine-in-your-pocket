#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
harvard_test.py — File-based harness for your Buttontalk assistant.
- Streams harvard.wav into Vosk in chunks (realtime or fast).
- Can use a deterministic Mock LLM or your real LLM.
- Can mute TTS for “pure” timing.
- Emits JSONL metrics if bench.py is enabled.
"""

from __future__ import annotations
import os, time, json, wave, argparse
from pathlib import Path

# Import *public* bits from your main app.
# Make sure your main file has the usual:
# if __name__ == "__main__": main()
# so importing it won't auto-run main().
from buttontalk import (
    init_models, stream_and_speak, ensure_display, ensure_llm, ensure_vosk_model, display, llm, vosk_model,
    SAMPLE_RATE, BLOCK_SIZE, conversation, TMP_AUDIO
)

try:
    from bench import bench
except Exception:
    class _Null:
        def start(self): ...
        def mark(self, *a, **k): ...
        def value(self, *a, **k): ...
        def span(self, *a, **k):
            class _Ctx:
                def __enter__(self): ...
                def __exit__(self, *a): return False
            return _Ctx()
    bench = _Null()

class MockStreamer:
    """Deterministic token-ish streaming for stable benchmarks."""
    def __init__(self, text="Thanks. Your audio pipeline is working. This is only a test."):
        self.text = text
    def stream(self, conversation, temperature=0.0):
        for token in self.text.split(" "):
            yield {"content": token + " "}

def stt_from_wav_streaming(wav_path: Path, pace: str = "realtime") -> str:
    """
    Feed a WAV file into Vosk as if it were the mic.
    pace='realtime' sleeps to mimic mic timing; 'fast' pushes ASAP.
    """
    from vosk import KaldiRecognizer
    model = ensure_vosk_model()
    if model is None:
        raise RuntimeError("Vosk model not initialised. Did you call app.init_models()?")

    rec = KaldiRecognizer(model, SAMPLE_RATE)

    bytes_per_sec = SAMPLE_RATE * 2  # 16-bit mono
    chunk_bytes = BLOCK_SIZE * 2

    text_parts = []
    last_display = 0

    with wave.open(str(wav_path), "rb") as wf:
        assert wf.getframerate() == SAMPLE_RATE, f"Expected {SAMPLE_RATE} Hz"
        assert wf.getnchannels() == 1, "Expected mono WAV"

        bench.mark("stt.wav.stream.start", frames=wf.getnframes())
        t0 = time.perf_counter_ns()

        with bench.span("stt.wav.stream.total"):
            while True:
                data = wf.readframes(BLOCK_SIZE)
                if not data:
                    break

                if rec.AcceptWaveform(data):
                    res = json.loads(rec.Result())
                    if (txt := res.get("text", "")):
                        text_parts.append(txt)
                else:
                    # Throttle LCD writes so I2C doesn’t trip you up
                    now = time.time()
                    if now - last_display > 0.1:
                        part = json.loads(rec.PartialResult()).get("partial","")
                        if part:
                            ensure_display().async_write(part[-32:])
                        last_display = now

                if pace == "realtime":
                    time.sleep(chunk_bytes / bytes_per_sec)

        final = json.loads(rec.FinalResult()).get("text", "")
        text = (" ".join(text_parts) + " " + final).strip()

    bench.value("stt.wav.time_to_final_s", (time.perf_counter_ns()-t0)/1e9, text_len=len(text))
    ensure_display().write(text[-32:])
    return text

def run_harvard_test(wav: Path, use_mock_llm: bool, pace: str, mute_tts: bool):
    bench.start()
    init_models()

    d = ensure_display()           # <-- get it now

    # Optionally mute TTS for clean timing
    if mute_tts:
        os.environ["TTS_MUTE"] = "1"

    test_llm = MockStreamer() if use_mock_llm else ensure_llm()


    bench.mark("test.start", wav=str(wav), pace=pace, mock_llm=use_mock_llm, mute_tts=mute_tts)
    d.fade_in(color=(0, 100, 255))
    d.write("WAV test")

    with bench.span("test.stt_total"):
        spoken_text = stt_from_wav_streaming(wav, pace=pace)
    if not spoken_text:
        print("No text produced from WAV. Check sample rate/channels.")
        return

    conversation.append({"role":"user","content":spoken_text})
    with bench.span("test.llm_total"):
        response = stream_and_speak(conversation, test_llm, TMP_AUDIO, temperature=0.3)
    conversation.append({"role":"assistant","content":response})

    bench.mark("test.done", resp_len=len(response))
    print("✅ Harvard test complete.")

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", type=str, required=True, help="Path to harvard.wav (mono, 16kHz)")
    ap.add_argument("--pace", choices=["realtime","fast"], default="realtime", help="Feed audio in real time or as fast as possible")
    ap.add_argument("--mock-llm", action="store_true", help="Use a deterministic mock LLM streamer")
    ap.add_argument("--mute-tts", action="store_true", help="Don’t play audio; useful for clean timing")
    return ap.parse_args()

if __name__ == "__main__":
    args = parse_args()
    run_harvard_test(Path(args.wav), use_mock_llm=args.mock_llm, pace=args.pace, mute_tts=args.mute_tts)
