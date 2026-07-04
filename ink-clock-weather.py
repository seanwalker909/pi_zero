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
CITY = "Chicago"      # Your city name
WEATHER_UNITS = "u"   # Use "u" for Imperial (°F), or "m" for Metric (°C)
# =====================

# Expanded dictionary using nicer, cleaner words since we have more room now!
CONDITION_MAP = {
    "113": "Clear", "116": "P.Cloudy", "119": "Cloudy", "122": "Overcast", "143": "Mist", "176": "Showers",
    "200": "T-Storm", "227": "Snow", "230": "Blizzard", "248": "Fog", "260": "Freezing Fog", "263": "Drizzle",
    "266": "Drizzle", "293": "Light Rain", "296": "Rain", "299": "Heavy Rain", "302": "Heavy Rain", "353": "Showers",
    "356": "Heavy Rain", "359": "Torrential", "386": "T-Storm", "389": "Heavy T-Storm"
}

def get_3day_forecast():
    """Fetches weather data from wttr.in and returns an optimized 3-day array"""
    try:
        url = f"https://wttr.in/{CITY}?format=j1"
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            forecast_list = []
            
            # Slice the array to only grab the first 3 days
            for idx, day in enumerate(data.get('weather', [])[:3]):
                # Human-friendly day labels
                if idx == 0:
                    day_label = "Today"
                elif idx == 1:
                    day_label = "Tomorrow"
                else:
                    date_raw = datetime.strptime(day['date'], "%Y-%m-%d")
                    day_label = date_raw.strftime("%A") # Full day name, e.g., "Monday"
                
                # Temperature unit parsing
                if WEATHER_UNITS == "u":
                    hi = day['maxtempF']
                    lo = day['mintempF']
                else:
                    hi = day['maxtempC']
                    lo = day['mintempC']
                
                # Fetch Mid-day condition code
                weather_code = day['hourly'][4]['weatherCode'] 
                cond = CONDITION_MAP.get(weather_code, "Weather")
                
                forecast_list.append({
                    "day": day_label,
                    "hi": hi,
                    "lo": lo,
                    "cond": cond
                })
            return forecast_list
    except Exception as e:
        print(f"3-day weather parse failed: {e}")
    return []

try:
    print("Initializing 2.13in e-Paper 3-Day Dashboard...")
    epd = epd2in13_V4.EPD()
    epd.init()
    epd.Clear(0xFF)

    width, height = epd.height, epd.width  # 250 x 122 pixels
    
    # Notice the upgraded font sizes! Much easier to read on a desk.
    try:
        font_time = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 38)
        font_date = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
        font_grid_hdr = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 11)
        font_grid_txt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 11)
    except IOError:
        print("Default DejaVu font missing, using system defaults.")
        font_time = font_date = font_grid_hdr = font_grid_txt = ImageFont.load_default()

    print("Clock running. Press Ctrl+C to exit.")
    
    last_minute = -1
    last_weather_update = 0
    forecast_data = []

    while True:
        now = datetime.now()
        current_timestamp = time.time()
        
        # Update weather data every hour to keep the 3 days highly accurate
        if current_timestamp - last_weather_update > 3600 or not forecast_data:
            print("Downloading fresh weather data...")
            fresh_data = get_3day_forecast()
            if fresh_data: 
                forecast_data = fresh_data
            last_weather_update = current_timestamp

        # Update layout on the minute mark
        if now.minute != last_minute:
            last_minute = now.minute
            
            image = Image.new('1', (width, height), 255) 
            draw = ImageDraw.Draw(image)

            # Top Half: Time and Date Modules
            time_str = now.strftime("%H:%M")
            date_str = now.strftime("%A, %b %d")
            
            draw.text((12, 4), time_str, font=font_time, fill=0)
            draw.text((15, 43), date_str, font=font_date, fill=0)
            
            # Clean layout boundary line separating clock from forecast matrix
            draw.line([(8, 62), (width - 8, 62)], fill=0, width=1)
            
            # Bottom Half: Spaced 3-Column Layout Matrix
            if forecast_data:
                start_x = 12
                col_width = 81  # Beautifully balances 3 columns across the 250px total width
                
                for idx, day in enumerate(forecast_data):
                    x_pos = start_x + (idx * col_width)
                    
                    # Row 1: Day Bold Header ("Today", "Tomorrow", "Monday")
                    draw.text((x_pos, 68), day['day'], font=font_grid_hdr, fill=0)
                    
                    # Row 2: Clean text condition descriptions ("Clear", "P.Cloudy")
                    draw.text((x_pos, 84), day['cond'], font=font_grid_txt, fill=0)
                    
                    # Row 3: High and Low paired elegantly on one line (e.g. "74°/55°")
                    temp_str = f"{day['hi']}°/{day['lo']}°"
                    draw.text((x_pos, 100), temp_str, font=font_grid_txt, fill=0)
            else:
                draw.text((15, 82), "Loading local weather forecast...", font=font_date, fill=0)

            # Send buffer map to screen
            epd.init()
            epd.display(epd.getbuffer(image))
            epd.sleep()
            
        time.sleep(5)

except KeyboardInterrupt:    
    print("\nExiting script.")
    epd2in13_V4.epdconfig.module_exit()
    sys.exit()
