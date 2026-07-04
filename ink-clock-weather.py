#!/usr/bin/env python3
import sys
import os
import time
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Automatically look for Waveshare libraries
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
# Change "_V4" to match your specific hardware version sticker (e.g., _V3)
from waveshare_epd import epd2in13_V4

# === CONFIGURATION ===
CITY = "Chicago"  # Change this to your city name (e.g., "London", "Paris", "Austin")
WEATHER_UNITS = "u" # Use "u" for Fahrenheit/mph, or "m" for Celsius/kmh
# =====================

def get_weather():
    """Fetches a lightweight one-line weather string from wttr.in"""
    try:
        # format=1 returns something like "☀️ +72°F" or "🌧️ +12°C"
        url = f"https://wttr.in/{CITY}?format=1&{WEATHER_UNITS}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            # Clean up the string to remove any unexpected layout bugs
            return response.text.strip()
    except Exception as e:
        print(f"Weather fetch failed: {e}")
    return "Weather N/A"

try:
    print("Initializing 2.13in e-Paper Weather Clock...")
    epd = epd2in13_V4.EPD()
    epd.init()
    epd.Clear(0xFF) # Clear screen to white

    # Screen dimensions (rotated layout)
    width, height = epd.height, epd.width 
    
    # Load default fonts
    try:
        font_time = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 44)
        font_date = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)
        font_weather = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
    except IOError:
        print("Default DejaVu font missing, falling back to standard tiny font.")
        font_time = font_date = font_weather = ImageFont.load_default()

    print("Clock running. Press Ctrl+C to exit.")
    
    last_minute = -1
    last_weather_update = 0
    weather_str = "Loading..."

    while True:
        now = datetime.now()
        current_timestamp = time.time()
        
        # 1. Fetch weather once every 15 minutes (900 seconds)
        if current_timestamp - last_weather_update > 900:
            print("Fetching fresh weather data...")
            weather_str = get_weather()
            last_weather_update = current_timestamp

        # 2. Only refresh the e-ink layout when the minute changes
        if now.minute != last_minute:
            last_minute = now.minute
            
            # Create a blank image canvas (1-bit color: white background)
            image = Image.new('1', (width, height), 255) 
            draw = ImageDraw.Draw(image)

            # Format time and date strings
            time_str = now.strftime("%H:%M")
            date_str = now.strftime("%A, %b %d")

            # Draw onto canvas (X, Y layout coordinate points)
            draw.text((15, 10), time_str, font=font_time, fill=0)       # Big Time
            draw.text((18, 62), date_str, font=font_date, fill=0)       # Medium Date
            
            # Draw a clean horizontal separator line
            draw.line([(15, 88), (width - 15, 88)], fill=0, width=1)
            
            # Draw the weather condition text
            draw.text((18, 95), weather_str, font=font_weather, fill=0) # Weather info

            # Send the image buffer to the display hardware
            epd.init()
            epd.display(epd.getbuffer(image))
            epd.sleep() # Put display to sleep to guard against burn-in
            
        time.sleep(5) # Poll system clock quietly in the background

except KeyboardInterrupt:    
    print("\nExiting clock script.")
    epd2in13_V4.epdconfig.module_exit()
    sys.exit()