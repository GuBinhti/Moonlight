import cv2
import time
import datetime
from skyfield.api import Loader, Topos
from skyfield.almanac import moon_phase
import numpy as np
import os

# Set the base path relative to the script's location
BASE_PATH = os.path.join(os.path.dirname(__file__), "Moonlight", "Moon Phase")

# Define paths to your moon phase images relative to BASE_PATH
PHASE_IMAGES = {
    'Waxing Crescent': os.path.join(BASE_PATH, 'Waxing Crescent.png'),
    'First Quarter': os.path.join(BASE_PATH, 'First Quarter.png'),
    'Waxing Gibbous': os.path.join(BASE_PATH, 'Waxing Gibbous.png'),
    'Full Moon': os.path.join(BASE_PATH, 'Full Moon.png'),
    'Waning Gibbous': os.path.join(BASE_PATH, 'Waning Gibbous.png'),
    'Last Quarter': os.path.join(BASE_PATH, 'Last Quarter.png'),
    'Waning Crescent': os.path.join(BASE_PATH, 'Waning Crescent.png'),
    'New Moon': os.path.join(BASE_PATH, 'New Moon.png')
}

# Define brightness factors for each phase
PHASE_BRIGHTNESS = {
    'Waxing Crescent': 0.3,
    'First Quarter': 0.5,
    'Waxing Gibbous': 0.7,
    'Full Moon': 1.0,
    'Waning Gibbous': 0.7,
    'Last Quarter': 0.5,
    'Waning Crescent': 0.3,
    'New Moon': 0.1
}

# Set up the Skyfield Loader, location, and ephemeris
load = Loader('~/skyfield-data')
ts = load.timescale()
eph = load('de421.bsp')
location = Topos(latitude_degrees=52.0, longitude_degrees=0.0)  # Example location

def get_moon_position_and_phase(date):
    # Convert date to Skyfield time
    time_obj = ts.utc(date.year, date.month, date.day, date.hour, date.minute, date.second)
    
    # Get Moon's position and phase relative to the Earth-centered location
    astrometric = (eph['earth'] + location).at(time_obj).observe(eph['moon'])
    alt, az, distance = astrometric.apparent().altaz()
    
    # Determine moon phase
    phase_degrees = moon_phase(eph, time_obj).degrees
    if 0 <= phase_degrees < 45:
        moon_phase_name = 'Waxing Crescent'
    elif 45 <= phase_degrees < 90:
        moon_phase_name = 'First Quarter'
    elif 90 <= phase_degrees < 135:
        moon_phase_name = 'Waxing Gibbous'
    elif 135 <= phase_degrees < 180:
        moon_phase_name = 'Full Moon'
    elif 180 <= phase_degrees < 225:
        moon_phase_name = 'Waning Gibbous'
    elif 225 <= phase_degrees < 270:
        moon_phase_name = 'Last Quarter'
    elif 270 <= phase_degrees < 315:
        moon_phase_name = 'Waning Crescent'
    else:
        moon_phase_name = 'New Moon'

    return alt.degrees, az.degrees, moon_phase_name

def overlay_moon_phase(frame, moon_phase, position, brightness):
    # Check if the image path exists
    image_path = PHASE_IMAGES.get(moon_phase)
    if not image_path or not os.path.exists(image_path):
        print(f"Image not found for phase: {moon_phase} at path: {image_path}")
        return frame

    # Load moon phase image
    moon_image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if moon_image is None:
        print(f"Error loading image for phase: {moon_phase}")
        return frame

    # Resize and set brightness (alpha) for overlay
    moon_image = cv2.resize(moon_image, (100, 100))
    overlay = np.zeros_like(frame, dtype=np.uint8)
    alpha = PHASE_BRIGHTNESS[moon_phase] * brightness

    # Place the moon image on the overlay frame
    x, y = position
    overlay[y:y+moon_image.shape[0], x:x+moon_image.shape[1]] = moon_image

    # Apply the overlay with brightness transparency
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    return frame

def run_simulation(year, speed_factor=1):
    # Set the start date to the current date in 2024 but using 2018 data
    start_date = datetime.datetime.now()
    target_year_date = start_date.replace(year=year)
    
    # Start OpenCV window
    cv2.namedWindow("Moonlight Simulator", cv2.WINDOW_NORMAL)
    
    while True:
        # Calculate adjusted date based on speed factor
        adjusted_seconds = (datetime.datetime.now() - start_date).total_seconds() * speed_factor
        simulated_date = target_year_date + datetime.timedelta(seconds=adjusted_seconds)
        
        # Get moon position and phase
        alt, az, phase = get_moon_position_and_phase(simulated_date)
        
        # Prepare the frame
        frame = np.zeros((500, 500, 3), dtype=np.uint8)
        moon_x = int(250 + 200 * np.cos(np.radians(az)))
        moon_y = int(250 - 200 * np.sin(np.radians(alt)))
        
        # Overlay moon phase image at calculated position with brightness factor
        frame = overlay_moon_phase(frame, phase, (moon_x, moon_y), PHASE_BRIGHTNESS.get(phase, 1))
        
        # Display the date and time at the top of the frame
        cv2.putText(frame, f"Simulated Date: {simulated_date.strftime('%Y-%m-%d %H:%M:%S')}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Display phase and additional information
        cv2.putText(frame, f"Phase: {phase}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Altitude: {alt:.2f} Azimuth: {az:.2f}", (10, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Show the frame
        cv2.imshow("Moonlight Simulator", frame)
        
        # Exit on pressing 'q'
        if cv2.waitKey(100) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

# Start the simulation with the target year data and a speed factor (e.g., 10x faster)
run_simulation(year=2018, speed_factor=10)
