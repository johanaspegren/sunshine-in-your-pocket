

1) Create systemd service file

sudo nano /etc/systemd/system/buttontalk.service

paste: 
[Unit]
Description=ButtonTalk Literacy Assistant
After=network.target sound.target

[Service]
WorkingDirectory=/home/antipater/dev/personal-assistant
ExecStart=/home/antipater/dev/personal-assistant/.venv/bin/python /home/antipater/dev/personal-assistant/buttontalk.py
Environment="PATH=/home/antipater/dev/personal-assistant/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Restart=always
User=antipater

[Install]
WantedBy=multi-user.target



sudo usermod -aG gpio antipater

sudo systemctl enable --now pigpiod
systemctl status pigpiod   # should be active (running)

