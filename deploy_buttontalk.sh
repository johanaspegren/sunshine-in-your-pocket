#!/bin/bash

set -e

PROJECT_DIR=/home/antipater/dev/personal-assistant
VENV_DIR=$PROJECT_DIR/.venv
SERVICE_NAME=buttontalk
SERVICE_FILE=/etc/systemd/system/$SERVICE_NAME.service

echo "🚀 Deploying ButtonTalk Assistant …"

# Step 1: Activate .venv or create it if missing
if [ ! -d "$VENV_DIR" ]; then
    echo "🔧 Creating virtualenv at $VENV_DIR"
    python3 -m venv $VENV_DIR
fi

echo "🐍 Activating virtualenv …"
source $VENV_DIR/bin/activate

# Step 2: Install required Python packages
echo "📦 Installing Python packages …"
pip install -U pip
pip install gpiozero sounddevice vosk onnxruntime pydantic instructor openai groq ollama python-dotenv piper-tts RPi.GPIO

# Step 3: Test script
echo "🧪 Testing script manually …"
python $PROJECT_DIR/buttontalk.py & sleep 3 && kill $!

# Step 4: Write systemd service
echo "📝 Writing systemd service …"
sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=ButtonTalk Literacy Assistant
After=network.target sound.target

[Service]
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_DIR/bin/python $PROJECT_DIR/buttontalk.py
Environment="PATH=$VENV_DIR/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Restart=always
User=antipater

[Install]
WantedBy=multi-user.target
EOF

# Step 5: Enable and start service
echo "🔗 Enabling and starting service …"
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME.service
sudo systemctl restart $SERVICE_NAME.service

echo "✅ Done!"
echo "👉 View status:  sudo systemctl status $SERVICE_NAME"
echo "👉 View logs:    journalctl -u $SERVICE_NAME -f"
