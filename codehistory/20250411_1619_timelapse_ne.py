from picamera2 import Picamera2
import time
from datetime import datetime
from PIL import Image  # For image brightness analysis
import numpy as np
import csv
import os

# Create/open a CSV file for logging
log_file = "photo_log.csv"
log_exists = os.path.isfile(log_file)

# Create header if the file is new
if not log_exists:
    with open(log_file, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "filename", "brightness", "exposure_time", "gain", "focus_mode", "lens_position"])

# Initialize the camera
picam2 = Picamera2()

# Set up still image configuration (highest quality)
config = picam2.create_still_configuration()
picam2.configure(config)

# Initial exposure settings
exposure_time = 100000      # 0.1 seconds (in microseconds)
gain = 1.0                  # Low analog gain (ISO-like)

# initial last brightness
last_brightness = 100

# Function to measure image brightness (0 = dark, 255 = bright)
def measure_brightness(image_path):
    image = Image.open(image_path).convert('L')  # Convert to grayscale
    return np.array(image).mean()                # Average pixel brightness

# Function to decide if it's daytime based on brightness threshold
def is_daytime(brightness, threshold=80):
    return brightness > threshold

# Start the time-lapse loop
while True:
    # Set exposure time and gain before each capture
    picam2.set_controls({
        "ExposureTime": exposure_time,
        "AnalogueGain": gain
    })

#     # Focus logic
#     if 'last_brightness' in locals() and is_daytime(last_brightness):
#         # If it's bright: autofocus
#         print("Daylight: Running autofocus")
#         picam2.set_controls({"AfMode": 1})   # Continuous autofocus
#         time.sleep(1)                        # Give time for autofocus to run
#         picam2.set_controls({"AfMode": 0})   # Lock focus once it's found
#     else:
#         # If it's dark: use fixed manual focus
#         print("Night: Fixed focus")
#         picam2.set_controls({
#             "AfMode": 0,                     # Disable autofocus
#             "LensPosition": 4              # Set a fixed focus point (adjust as needed)
#         })
        
    # focus logic
    if last_brightness is not None and is_daytime(last_brightness):
        print("Daylight: Running autofocus")
        picam2.set_controls({
            "AeEnable":True,	#auto exposure
            "AfMode": 2})  		# Auto-once
        time.sleep(2)
        #picam2.set_controls({"AfMode": 0})
    else:
        print("Night: Fixed focus")
        picam2.set_controls({"AfMode": 0, "LensPosition": 0.47})

    # Start camera, wait for exposure time, then capture the image
    picam2.start()
    time.sleep(exposure_time / 1_000_000 + 1)  # Wait for exposure + buffer
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{timestamp}.jpg"
    picam2.capture_file(filename)
    # Get current metadata
    metadata = picam2.capture_metadata()
    lens_position = metadata.get("LensPosition", "NA")
    picam2.stop()
    
    last_brightness = measure_brightness(filename)
    
    # Log this capture to CSV
    with open(log_file, mode='a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp,
            filename,
            f"{last_brightness:.1f}",
            exposure_time,
            f"{gain:.2f}",
            "auto" if is_daytime(last_brightness) else "fixed",
            round(lens_position, 2) if lens_position != "NA" else "NA"
        ])


    # Analyze brightness of the captured image
    last_brightness = measure_brightness(filename)
    print(f"{timestamp}: Brightness = {last_brightness:.1f}")

    # Adjust exposure based on brightness to target 100
    target = 100            # Ideal mean brightness (tweakable)
    tolerance = 10          # Allowable range around target

    if last_brightness < target - tolerance and exposure_time < 8000000:
        # Too dark ? increase exposure and gain
        exposure_time = int(exposure_time * 1.5)
        gain = min(gain * 1.2, 8.0)
    elif last_brightness > target + tolerance and exposure_time > 10000:
        # Too bright ? decrease exposure and gain
        exposure_time = int(exposure_time / 1.5)
        gain = max(gain / 1.2, 1.0)

    # Keep exposure time within safe limits
    exposure_time = min(max(exposure_time, 10000), 8000000)

    # Wait 5 minutes before next shot
    time.sleep(300)
