

1) Create systemd service file

sudo nano /etc/systemd/system/buttontalk.service

paste: 
ExecStart=
/home/antipater/dev/personal-assistant/.venv/bin/python /home/antipater/dev/personal-assistant/buttontalk.py

