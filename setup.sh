#!/bin/bash
python3 -m venv venv

/home/ec2-user/cpu-burner/venv/bin/python -m pip install flask

echo "Creating cpu-burner systemd service"

sudo bash -c "echo -e \
\"[Unit]
Description=CPU Burner Python Service
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/cpu-burner
ExecStart=/home/ec2-user/cpu-burner/venv/bin/python /home/ec2-user/cpu-burner/main.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target\" \
> /etc/systemd/system/cpu-burner.service"

echo "Reloading systemd"
sudo systemctl daemon-reexec
sudo systemctl daemon-reload

echo "Enabling service"
sudo systemctl enable cpu-burner

echo "Starting service"
sudo systemctl start cpu-burner

echo "Done."
echo "Check status with: systemctl status cpu-burner"
echo "View logs with: journalctl -u cpu-burner -f"
