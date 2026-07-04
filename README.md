# pi_zero
homelab pi zero code

Dependencies:

After flashing the 32 bit os, install dependencies and obtain drivers for wavesphere display
```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-pil python3-numpy git
sudo pip3 install rpi-lgpio spidev

git clone https://github.com/waveshare/e-Paper.git
cd e-Paper/RaspberryPi_JetsonNano/python
```


Create service in systemd, copy paste inkclock.service:
```bash
sudo nano /etc/systemd/system/inkclock.service
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable inkclock.service
sudo systemctl start inkclock.service
```
