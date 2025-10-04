ButtonTalk is a lightweight voice assistant that runs entirely on a Raspberry Pi.
Press a button, speak, and it listens, thinks, and replies — while the Display-O-Tron HAT shows what’s happening in real time.

✨ Features

🎙️ Push-to-Talk voice capture via gpiozero.Button

🗣️ Local speech-to-text with Vosk

🤖 LLM response generation using your choice of provider
(ollama, openai, groq, etc.) via the custom LLMHandler

🔊 Voice synthesis with Piper-TTS

💡 Display-O-Tron HAT integration – shows “Listening… / Thinking… / Speaking…”
using a minimal patched st7036 driver

🪛 Runs as a resilient systemd service on boot

🧩 Modular design – all helpers live under /modules/

🧱 Project Structure
personal-assistant/
├── buttontalk.py              # Main service logic
├── modules/
│   ├── llm_handler.py
│   ├── display_handler.py     # Minimal st7036 LCD driver wrapper
│   ├── dothat/                # (Optional) legacy HAT modules
│   └── ...
├── models/                    # Local Vosk models
├── tts_output/                # Temporary audio files
└── deploy_buttontalk.sh       # Installer & systemd setup

🔧 Hardware Setup
Component	Function	GPIO
Push button	Record trigger	GPIO 5
Dot HAT LCD	Display output	I²C + pins 25 & 12
Audio device	Playback	PulseAudio / ALSA

Earlier versions used GPIO 3 for the button, which conflicted with I²C.
I²C must remain enabled in /boot/firmware/config.txt:

dtparam=i2c_arm=on

🧩 Display Handler

The Dot HAT’s LCD is driven directly through a patched st7036 library
(no dependency on dothat, sn3218, or cap1xxx).

import st7036

class DisplayHandler:
    def __init__(self):
        self.lcd = st7036.st7036(register_select_pin=25, reset_pin=12)
        self.lcd.set_contrast(50)

    def write(self, text):
        self.lcd.clear()
        self.lcd.write(text[:32])


Typical usage inside the assistant:

display.write("Listening…")
display.write("Thinking…")
display.write("Speaking…")
display.write("Idle")

🚀 Installation
git clone https://github.com/<yourusername>/personal-assistant.git
cd personal-assistant
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install gpiozero sounddevice vosk onnxruntime pydantic instructor \
            openai groq ollama python-dotenv piper-tts RPi.GPIO lgpio


Enable I²C in Raspberry Pi Configuration or by editing /boot/firmware/config.txt.

Run once to verify:

python3 buttontalk.py

🧩 Deploy as a Service
sudo bash deploy_buttontalk.sh
sudo systemctl status buttontalk
sudo journalctl -u buttontalk -f

🧪 Troubleshooting
Symptom	Likely Cause	Fix
TimeoutError: [Errno 110] Connection timed out	I²C disabled	sudo raspi-config → Interfaces → I2C → Enable
Cannot determine SOC peripheral base address	Missing lgpio	sudo apt install python3-lgpio
Button doesn’t trigger	Wrong GPIO pin	Ensure button on GPIO 5 + GND
LCD dark / no text	Use patched st7036	Copy working file into venv or modules/
Service doesn’t start	Wrong venv path	Edit /etc/systemd/system/buttontalk.service
🧪 Quick Test
python3 - <<'EOF'
from modules.display_handler import DisplayHandler
d = DisplayHandler()
for msg in ["Listening…", "Thinking…", "Speaking…", "Idle"]:
    d.write(msg)
    import time; time.sleep(1)
EOF

💡 Future Ideas

Add colour backlight feedback (sn3218 integration)

Implement simple dialogue memory on disk

Optional microphone VU meter on LCD

WebSocket interface for remote control

🧙 Author

Johan Müllern-Aspegren
Capgemini | Applied Innovation Exchange Nordics
Dry humour. Warm circuits.