# pi_zero
homelab pi zero code, and bootstrapping scripts for 2.13 in waveshare e-ink display

Dependencies:

After flashing the 32 bit os, SSH in to install dependencies and obtain drivers for wavesphere display
```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-pil python3-numpy git
sudo pip3 install rpi-lgpio spidev

git clone https://github.com/waveshare/e-Paper.git
cd e-Paper/RaspberryPi_JetsonNano/python
```

Paste CTA API Key into CTA-tracker.py. 
Obtain API Key here: https://www.ctabustracker.com/home
No fancy secrets managment, because we home labbin' :)'

Create service in systemd, copy paste ctatracker.service:
```bash
sudo nano /etc/systemd/system/ctatracker.service
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ctatracker.service
sudo systemctl start ctatracker.service
```
