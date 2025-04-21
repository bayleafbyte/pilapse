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

# initialise last brightness
last_brightness = 100

#set target brightness
target_brightness = 100
tolerance = 10 

# Function to measure image brightness (0 = dark, 255 = bright)
def measure_brightness(image_path):
    image = Image.open(image_path).convert('L')  # Convert to grayscale
    return np.array(image).mean()                # Average pixel brightness

# Function to decide if it's daytime based on brightness threshold
def is_daytime(brightness, threshold = target_brightness - tolerance):
    return brightness > threshold

# Function to set exposure - ChatGPT 21/4/25
def adjust_exposure(current_brightness, current_exposure, min_exposure=10000, max_exposure=111000000):
    error = target_brightness - current_brightness

    # Use a proportional controller
    k = 1000000  # gain factor ? tweak this based on behavior
    adjustment = k * (error / target_brightness)

    new_exposure = current_exposure + adjustment

    # Clamp exposure to camera limits
    return int(max(min_exposure, min(max_exposure, new_exposure)))

# Start the time-lapse loop
while True:
    # focus and autoexposure logic 21/4/25
    if last_brightness is not None and is_daytime(last_brightness):
        print("Daylight: Autoexposure and autofocus")
        picam2.set_controls({"AeEnable":True, "AfMode": 2})
        time.sleep(2)
        # Start camera then capture the image
        picam2.start()
        time.sleep(2)
    # focus and exposure for night 21/4/25
    else:
        print("Night: Fixed focus")
        picam2.set_controls({"AfMode": 0, "LensPosition": 0.47,"ExposureTime": exposure_time,"AnalogueGain": gain})
        # Start camera, wait for exposure time, then capture the image
        picam2.start()
        time.sleep(exposure_time / 1_000_000 + 1)  # Wait for exposure + buffer
        
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{timestamp}.jpg"
    picam2.capture_file(filename)

    # Get current metadata - get actual exposure time and gain rather than set exposure and gain 21/4/25
    metadata = picam2.capture_metadata()
    exposure_time = metadata.get("ExposureTime", exposure_time)  # use actual value
    gain = metadata.get("AnalogueGain", gain)
    lens_position = metadata.get("LensPosition", "NA")
    picam2.stop()
    
    # Measure brightnss of last image
    last_brightness = measure_brightness(filename)
    
    # Log this capture to CSV
    with open(log_file, mode='a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp,
            filename,
            f"{last_brightness:.1f}",
            f"{exposure_time:.1f}",
            f"{gain:.2f}",
            "auto" if is_daytime(last_brightness) else "fixed",
            round(lens_position, 2) if lens_position != "NA" else "NA"
        ])

    # Analyze brightness of the captured image
    last_brightness = measure_brightness(filename)
    print(f"{timestamp}: Brightness = {last_brightness:.1f}")

    # set exposure
    exposure_time = adjust_exposure(last_brightness, exposure_time)

    # Wait 5 minutes before next shot
    time.sleep(300)
