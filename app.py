#!/usr/bin/env python3
import sys
import os
import time
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Automatically look for Waveshare libraries
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
try:
    from waveshare_epd import epd2in13_V4
except ImportError:
    print("Error: Waveshare library not found. Ensure 'lib' directory exists.")
    sys.exit(1)

# ==================== CONFIGURATION ===================
LOOP_DELAY = 60         # How often the screen alternates views (in seconds)
WEATHER_CITY = "Chicago"
WEATHER_UNITS = "u"     # "u" for Imperial (°F), "m" for Metric (°C")

# SECURITY: In a production environment, it is better to load this from an environment variable.
CTA_API_KEY = "xxx"  # Paste your 25-digit CTA key here

# Enter ALL stop IDs at your intersection
CTA_STOP_IDS = ["3563", "3564", "14166"]

# Sensor Configuration
SENSOR_PI_IP = "172.16.0.208"
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
            for idx, day in enumerate(data.get('weather', [])):
                if idx == 0: day_label = "Today"
                elif idx == 1: day_label = "Tomw"
                else: day_label = datetime.strptime(day['date'], "%Y-%m-%d").strftime("%a")
                
                hi = day['maxtempF'] if WEATHER_UNITS == "u" else day['maxtempC']
                lo = day['mintempF'] if WEATHER_UNITS == "u" else day['mintempC']
                weather_code = day['hourly'][4]['weatherCode'] 
                cond = CONDITION_MAP.get(str(weather_code), "Wthr")
                
                forecast_list.append({"day": day_label, "hi": hi, "lo": lo, "cond": cond})
            return forecast_list
    except Exception as e:
        print(f"Weather sync failed: {e}")
    return None

def get_cta_predictions():
    """Fetches real-time arrivals for all buses at configured stops"""
    try:
        stops_str = ",".join(CTA_STOP_IDS)
        url = f"http://ctabustracker.com/bustime/api/v2/getpredictions?key={CTA_API_KEY}&stpid={stops_str}&format=json"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'bustime-response' in data and 'prd' in data['bustime-response']:
                predictions = data['bustime-response']['prd']
                arrival_times = []
                
                for prd in predictions:
                    arrival_raw = datetime.strptime(prd['prdtm'], "%Y%m%d %H:%M")
                    minutes_away = round((arrival_raw - datetime.now()).total_seconds() / 60)
                    time_label = "DUE" if minutes_away <= 1 else f"{minutes_away}m"
                    
                    direction_map = {"Northbound": "N", "Southbound": "S", "Eastbound": "E", "Westbound": "W"}
                    dir_short = direction_map.get(prd['rtdir'], prd['rtdir'][:1])
                    
                    arrival_times.append({
                        "route": prd['rt'],
                        "dir": dir_short,
                        "time": time_label,
                        "dest": prd['des'],
                        "raw_minutes": minutes_away
                    })
                
                arrival_times.sort(key=lambda x: x['raw_minutes'])
                return arrival_times[:3] 
                
            elif 'error' in data['bustime-response']:
                return [{"route": "None", "dir": "", "time": "Sch", "dest": "No active buses"}]
    except Exception as e:
        print(f"CTA sync failed: {e}")
    return None

def get_air_quality():
    """Fetches air quality from the Sensor Pi receiver"""
    try:
        url = f"http://{SENSOR_PI_IP}:5000/data"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Air Quality sync failed: {e}")
    return None

def main():
    try:
        epd = epd2in13_V4.EPD()
        # We don't init() immediately to keep hardware in sleep until we have data
        
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

        views = ["weather", "cta", "aq"]
        current_view_idx = 0

        print("Starting display loop...")

        while True:
            now = datetime.now()

            # --- 1. DATA FETCH PHASE (Slow, non-hardware intensive) ---
            # We fetch all data BEFORE touching the E-ink hardware.
            # This prevents the "reset glitch" by ensuring the hardware is only 
            # interacted with when the program isn't waiting on a slow network request.
            print(f"[{now.strftime('%H:%M:%S')}] Fetching data...")
            
            w_data = get_3day_forecast()
            c_data = get_cta_predictions()
            a_data = get_air_quality()

            # If any fetch fails, we skip the refresh cycle this time to avoid 
            # showing incomplete/stale data or glitching the screen.
            if w_data is None or c_data is None or a_data is None:
                print("Data fetch failed or incomplete. Skipping this cycle.")
                time.sleep(10)
                continue

            # --- 2. RENDERING PHASE (Fast, Hardware intensive) ---
            image = Image.new('1', (width, height), 255)
            draw = ImageDraw.Draw(image)

            # Upper Clock Header
            time_str = now.strftime("%H:%M")
            date_str = now.strftime("%A, %b %d")
            draw.text((12, 4), time_str, font=font_time, fill=0)
            draw.text((15, 43), date_str, font=font_date, fill=0)
            draw.line([(8, 62), (width - 8, 62)], fill=0, width=1)

            current_view = views[current_view_idx]

            if current_view == "weather":
                start_x = 12
                col_width = 81
                for idx, day in enumerate(w_data):
                    x_pos = start_x + (idx * col_width)
                    draw.text((x_pos, 68), day['day'], font=font_bold_sm, fill=0)
                    draw.text((x_pos, 84), day['cond'], font=font_reg_sm, fill=0)
                    draw.text((x_pos, 100), f"{day['hi']}°/{day['lo']}°", font=font_reg_sm, fill=0)

            elif current_view == "cta":
                draw.text((12, 65), "Soonest Intersection Arrivals:", font=font_bold_sm, fill=0)
                start_x = 10
                col_width = 80
                for idx, bus in enumerate(c_data):
                    x_pos = start_x + (idx * col_width)
                    bus_label = f"{bus['route']} {bus['dir']}" if bus['dir'] else bus['route']
                    draw.text((x_pos, 78), bus_label, font=font_bold_sm, fill=0)
                    draw.text((x_pos, 91), bus['time'], font=font_bus_lg, fill=0)
                    clean_dest = bus['dest'][:12]
                    draw.text((x_pos, 110), clean_dest, font=font_dest_xs, fill=0)

            elif current_view == "aq":
                draw.text((12, 65), "Air Quality (PM2.5)", font=font_bold_sm, fill=0)
                pm25 = a_data.get('pm25', 0)
                draw.text((12, 85), f"{pm25} µg/m³", font=font_bus_lg, fill=0)
                status = "Good"
                if float(pm25) > 12: status = "Moderate"
                if float(pm25) > 35: status = "Unhealthy"
                draw.text((12, 110), status, font=font_reg_sm, fill=0)

            # Physical Hardware Write
            print(f"[{now.strftime('%H:%M:%S')}] Updating display...")
            epd.init()
            epd.display(epd.getbuffer(image))
            epd.sleep()

            current_view_idx = (current_view_idx + 1) % len(views)
            time.sleep(LOOP_DELAY)

    except KeyboardInterrupt:
        epd2in13_V4.epdconfig.module_exit()
        sys.exit()
    except Exception as e:
        print(f"Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
