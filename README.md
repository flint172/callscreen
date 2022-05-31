# Call Screen Application
Intercept calls and handle unapproved calls

Service File (/lib/systemd/system/callscreen.service

[Unit]
Description=CallScreener
After=multi-user.target

[Service]
Environment=PYTHONBUFFERED=1
Type=idle
ExecStart=/usr/bin/python3 /home/pi/workspace/callscreen/modembasic.py

[Install]
WantedBy=multi-user.target
