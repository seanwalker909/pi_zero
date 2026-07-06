#!/usr/bin/env python3
import sys
import os
import time
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Automatically look for Waveshare libraries
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
from waveshare_epd import epd2in13_V4

# === CONFIGURATION ===
CTA_API_KEY = "YOUR_CTA_API_KEY_HERE"  # Paste your 25-digit CTA key here
ROUTE = "22"                            # Change to your bus route (e.g., "151", "66")
STOP_ID = "1634"                        # Change to your specific 4 or 5-digit Stop ID
# =====================

def get_cta_predictions():
    """Fetches real-time arrival predictions from the CTA BusTime API"""
    try:
        # Requesting a clean JSON response instead of the old XML standard
        url = f"http://ctabustracker.com/bustime/api/v2/getpredictions?key={CTA_API_KEY}&rt={ROUTE}&stpid={STOP_ID}&format=json"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if the CTA returned a valid prediction wrapper
            if 'bustime-response' in data and 'prd' in data['bustime-response']:
                predictions = data['bustime-response']['prd']
                arrival_times = []
                
                # We only care about the next 3 upcoming buses
                for prd in predictions[:3]:
                    # 'prdtm' format is YYYYMMDD HH:MM
                    arrival_raw = datetime.strptime(prd['prdtm'], "%Y%m%d %H:%M")
                    now = datetime.now()
                    
                    # Calculate exactly how many minutes away the bus is
                    delta = arrival_raw - now
                    minutes_away = round(delta.total_seconds() / 60)
                    
                    # CTA uses "DUE" if the bus is arriving in under 2 minutes
                    if minutes_away <= 1:
                        time_label = "DUE"
                    else:
                        time_label = f"{minutes_away}m"
                        
                    arrival_times.append({
                        "dir": prd['rtdir'],      # e.g., "Northbound"
                        "time": time_label
                    })
                return arrival_times
            elif 'error' in data['bustime-response']:
                # Handles edge cases like late-night when no buses are running
                return [{"dir": "No Bus", "time": "Sch"}]
    except Exception as e:
        print(f"CTA API tracking fetch failed: {e}")
    return []

try:
    print("Initializing 2.13in e-Paper CTA Tracker Clock...")
    epd = epd2in13_V4.EPD()
    epd.init()
    epd.Clear(0xFF)

    width, height = epd.height, epd.width  # 250 x 122 pixels
    
    try:
        font_time = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 38)
        font_date = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
        font_bus_hdr = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 14)
        font_bus_time = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
        font_bus_meta = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 11)
    except IOError:
        font_time = font_date = font_bus_hdr = font_bus_time = font_bus_meta = ImageFont.load_default()

    print("Clock running. Press Ctrl+C to exit.")
    
    last_minute = -1

    while True:
        now = datetime.now()
        
        # Refresh every minute so both clock and bus countdowns remain perfectly accurate
        if now.minute != last_minute:
            last_minute = now.minute
            
            print("Fetching live CTA tracker updates...")
            bus_data = get_cta_predictions()
            
            image = Image.new('1', (width, height), 255) 
            draw = ImageDraw.Draw(image)

            # --- TOP SECTION: Clock & Date ---
            time_str = now.strftime("%H:%M")
            date_str = now.strftime("%A, %b %d")
            draw.text((12, 4), time_str, font=font_time, fill=0)
            draw.text((15, 43), date_str, font=font_date, fill=0)
            
            # --- LAYOUT SEPARATOR LINE ---
            draw.line([(8, 62), (width - 8, 62)], fill=0, width=1)
            
            # --- BOTTOM SECTION: Bus Dashboard Matrix ---
            # Header Label indicating which Route and Stop is being tracked
            header_text = f"Route {ROUTE} Bus Stop Predictions:"
            draw.text((12, 66), header_text, font=font_bus_meta, fill=0)
            
            if bus_data:
                # Distribute up to 3 upcoming arrivals horizontally across the screen
                start_x = 12
                col_width = 80 
                
                for idx, bus in enumerate(bus_data):
                    x_pos = start_x + (idx * col_width)
                    
                    # Top line of column: Big Bold Minutes Left (e.g. "14m" or "DUE")
                    draw.text((x_pos, 82), bus['time'], font=font_bus_time, fill=0)
                    
                    # Bottom line of column: Direction shorthand (e.g. "Northb" / "Southb")
                    short_dir = bus['dir'][:6] + "." if len(bus['dir']) > 6 else bus['dir']
                    draw.text((x_pos, 106), short_dir, font=font_bus_meta, fill=0)
            else:
                draw.text((12, 88), "Connecting to CTA Network...", font=font_bus_meta, fill=0)

            # Clear screen frame mapping and sleep
            epd.init()
            epd.display(epd.getbuffer(image))
            epd.sleep()
            
        time.sleep(5)

except KeyboardInterrupt:    
    print("\nExiting tracker script safely.")
    epd2in13_V4.epdconfig.module_exit()
    sys.exit()
