
Make saure I2C is disabled, we use the same gpio3



sudo nano /etc/systemd/system/buttontalk.service

antipater@aristoteles:~/dev/personal-assistant $ sudo more /etc/systemd/system/buttontalk.service
[Unit]
Description=ButtonTalk voice button
After=network.target sound.target
# GPIO3 is used -> ensure I2C is disabled at boot (dtparam=i2c_arm=off)

[Service]
Type=simple
User=antipater
WorkingDirectory=/home/antipater/dev/personal-assistant
Environment=GPIOZERO_PIN_FACTORY=lgpio
Environment=PYTHONPATH=/home/antipater/dev/personal-assistant
Environment=PYTHONUNBUFFERED=1
Environment=XDG_RUNTIME_DIR=/run/user/1000
Environment=PULSE_SERVER=unix:/run/user/1000/pulse/native
ExecStartPre=/bin/sleep 2
ExecStartPre=/home/antipater/dev/personal-assistant/.venv/bin/python -c "import sys,os; sys.path.insert(0,'/home/antipater/dev/personal-assistant');
 import piper_tts; print('BUTTONTALK will use:', piper_tts.__file__); print('CWD will be:', os.getcwd())"
ExecStart=/home/antipater/dev/personal-assistant/.venv/bin/python /home/antipater/dev/personal-assistant/buttontalk.py
Restart=on-failure
RestartSec=2
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target



