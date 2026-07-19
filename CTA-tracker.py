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

# ==================== CONFIGURATION ====================
LOOP_DELAY = 60         # How often the screen alternates views (in seconds)
WEATHER_CITY = "Chicago"
WEATHER_UNITS = "u"     # "u" for Imperial (°F), "m" for Metric (°C)

CTA_API_KEY = "xxx"  # Paste your 25-digit CTA key here

# Enter ALL stop IDs at your intersection (e.g., Northbound and Southbound)
# Example: Stop 1634 (Northbound) and Stop 1635 (Southbound) at the same crossroads
CTA_STOP_IDS = ["3563", "3564", "14166"]
# =======================================================

CONDITION_MAP = {
    "113": "Clear", "116": "P.Cloudy", "119": "Cloudy", "122": "Overcast", "143": "Mist", "176": "Showers",
    "200": "T-Storm", "227": "Snow", "230": "Blizzard", "248": "Fog", "260": "Frz Fog", "263": "Drizzle",
    "266": "Drizzle", "293": "L.Rain", "296": "Rain", "299": "Hvy Rain", "302": "Hvy Rain", "353": "Showers",
    "356": "Hvy Rain", "359": "Torntial", "386": "T-Storm", "389": "Hvy T-Stm"
}

def get_3day_forecast():
    """Fetches weather data from wttr.in"""
    try:
        url = f"https://wttr.in/{WEATHER_CITY}?format=j1"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            forecast_list = []
            for idx, day in enumerate(data.get('weather', [][:3])):
                if idx == 0: day_label = "Today"
                elif idx == 1: day_label = "Tomw"
                else: day_label = datetime.strptime(day['date'], "%Y-%m-%d").strftime("%a")
                
                hi = day['maxtempF'] if WEATHER_UNITS == "u" else day['maxtempC']
                lo = day['mintempF'] if WEATHER_UNITS == "u" else day['mintempC']
                weather_code = day['hourly'][4]['weatherCode'] 
                cond = CONDITION_MAP.get(weather_code, "Wthr")
                
                forecast_list.append({"day": day_label, "hi": hi, "lo": lo, "cond": cond})
            return forecast_list
    except Exception as e:
        print(f"Weather sync failed: {e}")
    return []

def get_cta_predictions():
    """Fetches real-time arrivals for all buses at configured stops, sorted by arrival time"""
    try:
        # Join multiple stops with a comma for a single API query
        stops_str = ",".join(CTA_STOP_IDS)
        url = f"http://ctabustracker.com/bustime/api/v2/getpredictions?key={CTA_API_KEY}&stpid={stops_str}&format=json"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'bustime-response' in data and 'prd' in data['bustime-response']:
                predictions = data['bustime-response']['prd']
                arrival_times = []
                
                for prd in predictions:
                    # Calculate minutes away
                    arrival_raw = datetime.strptime(prd['prdtm'], "%Y%m%d %H:%M")
                    minutes_away = round((arrival_raw - datetime.now()).total_seconds() / 60)
                    time_label = "DUE" if minutes_away <= 1 else f"{minutes_away}m"
                    
                    # Clean up direction shorthand
                    direction_map = {"Northbound": "N", "Southbound": "S", "Eastbound": "E", "Westbound": "W"}
                    dir_short = direction_map.get(prd['rtdir'], prd['rtdir'][:1])
                    
                    arrival_times.append({
                        "route": prd['rt'],
                        "dir": dir_short,
                        "time": time_label,
                        "dest": prd['des'],
                        "raw_minutes": minutes_away
                    })
                
                # Sort pooled predictions from all stops by physical arrival sequence
                arrival_times.sort(key=lambda x: x['raw_minutes'])
                return arrival_times[:3] # Keep top 3 soonest departures
                
            elif 'error' in data['bustime-response']:
                return [{"route": "None", "dir": "", "time": "Sch", "dest": "No active buses"}]
    except Exception as e:
        print(f"CTA sync failed: {e}")
    return []

try:
    epd = epd2in13_V4.EPD()
    epd.init()
    epd.Clear(0xFF)

    width, height = epd.height, epd.width # 250x122
    
    try:
        font_time = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 38)
        font_date = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
        font_bold_sm = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 11)
        font_reg_sm = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 11)
        font_bus_lg = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
        font_dest_xs = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 9)
    except IOError:
        font_time = font_date = font_bold_sm = font_reg_sm = font_bus_lg = font_dest_xs = ImageFont.load_default()

    # Cache timers
    last_weather_fetch = 0
    last_cta_fetch = 0
    weather_cache = []
    cta_cache = []
    
    show_weather_view = True


    while True:
        now = datetime.now()
        current_timestamp = time.time()

        # Update Weather cache every hour
        if current_timestamp - last_weather_fetch > 3600 or not weather_cache:
            print("Background updating weather data...")
            fresh_w = get_3day_forecast()
            if fresh_w: weather_cache = fresh_w
            last_weather_fetch = current_timestamp

        # Update CTA arrivals cache every 45 seconds
        if current_timestamp - last_cta_fetch > 45 or not cta_cache:
            print("Background updating intersection CTA data...")
            fresh_c = get_cta_predictions()
            if fresh_c: cta_cache = fresh_c
            last_cta_fetch = current_timestamp

        # Start Drawing
        image = Image.new('1', (width, height), 255)
        draw = ImageDraw.Draw(image)

        # Upper Clock Header
        time_str = now.strftime("%H:%M")
        date_str = now.strftime("%A, %b %d")
        draw.text((12, 4), time_str, font=font_time, fill=0)
        draw.text((15, 43), date_str, font=font_date, fill=0)
        
        # Grid line divider
        draw.line([(8, 62), (width - 8, 62)], fill=0, width=1)

        # Bottom Alternating views
        if show_weather_view:
            # --- WEATHER DASHBOARD ---
            if weather_cache:
                start_x = 12
                col_width = 81
                for idx, day in enumerate(weather_cache):
                    x_pos = start_x + (idx * col_width)
                    draw.text((x_pos, 68), day['day'], font=font_bold_sm, fill=0)
                    draw.text((x_pos, 84), day['cond'], font=font_reg_sm, fill=0)
                    draw.text((x_pos, 100), f"{day['hi']}°/{day['lo']}°", font=font_reg_sm, fill=0)
            else:
                draw.text((15, 82), "Loading local forecast...", font=font_date, fill=0)
        else:
            # --- POOLED INTERSECTION BUS DASHBOARD ---
            header_text = "Soonest Intersection Arrivals:"
            draw.text((12, 65), header_text, font=font_bold_sm, fill=0)
            
            if cta_cache:
                start_x = 10
                col_width = 80
                for idx, bus in enumerate(cta_cache):
                    x_pos = start_x + (idx * col_width)
                    
                    # Line 1: Route & Direction Shorthand (e.g., "22 N" or "36 S")
                    bus_label = f"{bus['route']} {bus['dir']}" if bus['dir'] else bus['route']
                    draw.text((x_pos, 78), bus_label, font=font_bold_sm, fill=0)
                    
                    # Line 2: Large Countdown (e.g., "DUE", "4m")
                    draw.text((x_pos, 91), bus['time'], font=font_bus_lg, fill=0)
                    
                    # Line 3: Truncated destination name to prevent overlap (e.g. "Howard")
                    clean_dest = bus['dest'][:12]
                    draw.text((x_pos, 110), clean_dest, font=font_dest_xs, fill=0)
            else:
                draw.text((12, 85), "Connecting to CTA...", font=font_reg_sm, fill=0)

        # Output to physical hardware
        epd.init()
        epd.display(epd.getbuffer(image))
        epd.sleep()

        # Switch view layout and wait
        show_weather_view = not show_weather_view
        time.sleep(LOOP_DELAY)

except KeyboardInterrupt:
    epd2in13_V4.epdconfig.module_exit()
    sys.exit()
