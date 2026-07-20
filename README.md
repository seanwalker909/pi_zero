# Pi Zero CTA & Weather Dashboard

This repository implements a real-time display for CTA (Chicago Transit Authority) bus arrivals, local weather, and air quality on an E-ink display.

**Status:** ✅ Working (Display loop active)

This implementation follows the **Raspberry Pi Service Deployment Skill** (see [pi_lab/skill.md](https://github.com/seanwalker909/pi_lab/blob/main/skill.md)).

## Features

- **CTA Real-time Bus Tracking**: Shows the next 3 bus arrivals for configured stops.
- **3-Day Weather Forecast**: Displays daily high/low temps and weather conditions via `wttr.in`.
- **Air Quality Monitoring**: Displays PM2.5 levels from a remote sensor Pi.
- **E-ink Optimized**: Designed for Waveshare E-ink displays with a rotation-based view system.

## Hardware Requirements

- Raspberry Pi (Zero, 3, 4, or 5)
- Waveshare E-ink Display (e.g., 2.13 inch V4)
- Connection to a sensor Pi (for Air Quality)

## Deployment Workflow

### 1. Repository Setup
```bash
git clone <your-repo-url>
cd pi_zero
```

### 2. Python Virtual Environment
```bash
# Create the virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2.5 Waveshare Library Setup
If you encounter "Error: Waveshare library not found", you must fetch the driver library from the official repository. This project requires the `lib` folder from `waveshareteam/e-Paper`.

```bash
# Clone the repository (temporary)
git clone --depth 1 https://github.com/waveshareteam/e-Paper.git temp-e-paper

# Copy the lib folder to your project root
cp -r temp-e-paper/RaspberryPi_JetsonNano/python/lib ./lib

# Clean up
rm -rf temp-e-paper
```

### 3. Configuration
Before running, edit `app.py` to update:
- `CTA_API_KEY`: Your 25-digit CTA API key.
- `CTA_STOP_IDS`: The stop IDs you want to track.
- `SENSOR_PI_IP`: The IP address of your air quality sensor Pi.

### 4. Systemd Service Configuration
Create the service file to manage the process:
```bash
sudo nano /etc/systemd/system/ctatracker.service
```
Paste the contents of the `ctatracker.service` file provided in this repo. **Ensure the `User` and `WorkingDirectory` paths match your installation.**

### 5. Deployment
```bash
sudo systemctl daemon-reload
sudo systemctl enable ctatracker.service
sudo systemctl start ctatracker.service
```

## Debugging & Troubleshooting

### MicroSD Card Longevity
**Crucial:** To prevent premature wear and failure of MicroSD cards, avoid excessive logging. This project implements a "data-first" fetch pattern to ensure the E-ink hardware is only engaged when data is successfully received, minimizing power-on/reset cycles.

### Checking Logs
```bash
# View all logs for the service
journalctl -u ctatracker.service

# Follow logs in real-time
journalctl -u ctatracker.service -f
```
