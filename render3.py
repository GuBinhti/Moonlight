import cv2
import time
import datetime
from skyfield.api import Loader, Topos
from skyfield.almanac import moon_phase, risings_and_settings
import numpy as np
import os
import pytz
from skyfield import almanac

# Set the base path relative to the current working directory
BASE_PATH = os.path.join(os.getcwd(), "Moon Phase")

# Define paths to moon phase images
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

# Set location to San Francisco (latitude and longitude)
location = Topos(latitude_degrees=37.7749, longitude_degrees=-122.4194)

# Set the timezone to PST
pst = pytz.timezone("America/Los_Angeles")

# Approximate dates in 2018 for each moon phase (these are rough estimates)
PHASE_DATES = {
    'Waxing Crescent': datetime.datetime(2018, 1, 19),
    'First Quarter': datetime.datetime(2018, 1, 24),
    'Waxing Gibbous': datetime.datetime(2018, 1, 28),
    'Full Moon': datetime.datetime(2018, 1, 31),
    'Waning Gibbous': datetime.datetime(2018, 2, 4),
    'Last Quarter': datetime.datetime(2018, 2, 7),
    'Waning Crescent': datetime.datetime(2018, 2, 10),
    'New Moon': datetime.datetime(2018, 2, 15)
}

# Default lunar cycle length in days (around 29.5 days for a typical lunar cycle)
DEFAULT_LUNAR_CYCLE_LENGTH = 29.5
DEFAULT_START_PHASE = "Full Moon"

def get_moon_position_and_phase(date):
    """Calculate the moon's altitude, azimuth, and phase for a given date and time."""
    # Convert the date to Skyfield's time format
    time_obj = ts.utc(date.year, date.month, date.day, date.hour, date.minute, date.second)
    
    # Get moon's position relative to an Earth-centered location
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

def get_moonrise_moonset(date):
    """Calculate the moonrise and moonset times for a given date."""
    # Set the time window for moonrise and moonset calculations
    start_time = ts.utc(date.year, date.month, date.day)
    end_time = ts.utc(date.year, date.month, date.day + 1)

    # Calculate moonrise and moonset using Skyfield's almanac and risings_and_settings function
    f = almanac.risings_and_settings(eph, eph['moon'], location)
    times, events = almanac.find_discrete(start_time, end_time, f)

    # Initialize moonrise and moonset as None in case they are not found
    moonrise, moonset = None, None

    # Iterate through events to find moonrise and moonset times
    for time, event in zip(times, events):
        local_time = time.utc_datetime().replace(tzinfo=pytz.utc).astimezone(pst)
        if event == 1 and moonrise is None:
            moonrise = local_time
        elif event == 0 and moonset is None:
            moonset = local_time
    
    return moonrise, moonset

def overlay_moon_phase(frame, moon_phase, position, brightness):
    """Overlay a moon phase image on the frame with specific brightness and position."""
    # Get the path of the phase image
    image_path = PHASE_IMAGES.get(moon_phase)
    # Check if image exists at the path
    if not image_path or not os.path.exists(image_path):
        print(f"Image not found for phase: {moon_phase} at path: {image_path}")
        return frame

    # Load the moon phase image with alpha channel if available (RGBA format)
    moon_image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if moon_image is None:
        print(f"Error loading image for phase: {moon_phase}")
        return frame

    # Resize moon image to fit the overlay dimensions
    moon_image = cv2.resize(moon_image, (100, 100))
    # Split alpha channel if present; otherwise, set full opacity
    if moon_image.shape[2] == 4:
        rgb_image = moon_image[:, :, :3]  # RGB channels
        alpha_channel = moon_image[:, :, 3] / 255.0  # Normalize alpha to 0-1
    else:
        rgb_image = moon_image  # If no alpha, use the RGB image as-is
        alpha_channel = np.ones((100, 100), dtype=float)  # Full opacity if no alpha

    # Determine the area on the frame to place the image (centered at position)
    x, y = position
    h, w = rgb_image.shape[:2]

    # Define the region of interest (ROI) within the frame for overlaying the moon image
    y1, y2 = max(0, y), min(frame.shape[0], y + h)
    x1, x2 = max(0, x), min(frame.shape[1], x + w)

    # Calculate where to overlay the image if it partially goes outside the frame boundaries
    moon_y1, moon_y2 = max(0, -y), min(h, frame.shape[0] - y)
    moon_x1, moon_x2 = max(0, -x), min(w, frame.shape[1] - x)

    # Blend the moon image into the frame using the alpha channel and brightness
    for c in range(3):  # Blend each RGB channel individually
        frame[y1:y2, x1:x2, c] = (
            alpha_channel[moon_y1:moon_y2, moon_x1:moon_x2] * brightness * rgb_image[moon_y1:moon_y2, moon_x1:moon_x2, c] +
            (1 - alpha_channel[moon_y1:moon_y2, moon_x1:moon_x2] * brightness) * frame[y1:y2, x1:x2, c]
        )

    return frame

def run_simulation(year, default_speed_factor=10000):
    """Run the moon phase simulation, displaying it in a maximized window with elliptical orbit."""
    # Prompt the user for the desired starting moon phase and custom lunar cycle length
    print("Available Moon Phases:", ", ".join(PHASE_DATES.keys()))
    selected_phase = input(f"Enter the starting moon phase (default: {DEFAULT_START_PHASE}): ").strip().title()
    
    # Use default starting phase if input is empty
    if not selected_phase:
        selected_phase = DEFAULT_START_PHASE
    
    # Set the start date to the approximate date of the selected phase in the given year
    target_year_date = PHASE_DATES.get(selected_phase, PHASE_DATES[DEFAULT_START_PHASE]).replace(year=year)
    
    # Get user input for a custom lunar cycle length
    custom_cycle_input = input(f"Enter the desired lunar cycle length in days (default: {DEFAULT_LUNAR_CYCLE_LENGTH}): ").strip()
    if custom_cycle_input:
        try:
            custom_cycle_length = float(custom_cycle_input)
        except ValueError:
            print("Invalid input. Using the default lunar cycle length.")
            custom_cycle_length = DEFAULT_LUNAR_CYCLE_LENGTH
    else:
        custom_cycle_length = DEFAULT_LUNAR_CYCLE_LENGTH

    # Calculate the adjusted speed factor based on the custom lunar cycle length
    speed_factor = default_speed_factor * (DEFAULT_LUNAR_CYCLE_LENGTH / custom_cycle_length)
    print(f"Adjusted speed factor based on custom lunar cycle: {speed_factor}")

    # Initialize OpenCV window in windowed fullscreen (maximize the window)
    cv2.namedWindow("Moonlight Simulator", cv2.WINDOW_NORMAL)
    screen_width = 1920
    screen_height = 1080
    cv2.resizeWindow("Moonlight Simulator", screen_width, screen_height)

    # Calculate the center of the screen and elliptical orbit radii for the moon’s path
    center_x, center_y = screen_width // 2, screen_height // 2
    orbit_radius_x = center_x - 200  # Horizontal radius for elliptical orbit
    orbit_radius_y = center_y - 100  # Vertical radius for elliptical orbit

    # Simulation loop
    start_date = datetime.datetime.now()
    while True:
        # Calculate the current simulation time adjusted by speed_factor
        adjusted_seconds = (datetime.datetime.now() - start_date).total_seconds() * speed_factor
        simulated_date = target_year_date + datetime.timedelta(seconds=adjusted_seconds)
        
        # Get moon position, phase, and brightness level based on the current simulated date
        alt, az, phase = get_moon_position_and_phase(simulated_date)
        brightness = PHASE_BRIGHTNESS.get(phase, 1)  # Retrieve brightness for the moon phase

        # Get moonrise and moonset times for the simulated date
        moonrise, moonset = get_moonrise_moonset(simulated_date)

        # Print moonrise and moonset to the terminal
        print(f"Moonrise: {moonrise.strftime('%Y-%m-%d %H:%M:%S %Z') if moonrise else 'N/A'}, Moonset: {moonset.strftime('%Y-%m-%d %H:%M:%S %Z') if moonset else 'N/A'}")

        # Convert simulated_date to PST timezone
        simulated_date_pst = simulated_date.replace(tzinfo=pytz.utc).astimezone(pst)
        
        # Create a blank frame (black background)
        frame = np.zeros((screen_height, screen_width, 3), dtype=np.uint8)
        
        # Calculate moon position for elliptical orbit around the screen center
        moon_x = int(center_x + orbit_radius_x * np.cos(np.radians(az)))
        moon_y = int(center_y + orbit_radius_y * np.sin(np.radians(az)))
        
        # Overlay the moon phase image at the calculated position with synchronized brightness
        frame = overlay_moon_phase(frame, phase, (moon_x, moon_y), brightness)
        
        # Display simulated date and time in PST at the top of the frame
        cv2.putText(frame, f"Simulated Date: {simulated_date_pst.strftime('%Y-%m-%d %H:%M:%S %Z')}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Display phase, altitude, azimuth, moonrise, and moonset information
        cv2.putText(frame, f"Phase: {phase}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Altitude: {alt:.2f} Azimuth: {az:.2f}", (10, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Moonrise: {moonrise.strftime('%H:%M %Z') if moonrise else 'N/A'}", (10, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Moonset: {moonset.strftime('%H:%M %Z') if moonset else 'N/A'}", (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Show the frame in the window
        cv2.imshow("Moonlight Simulator", frame)
        
        # Allow exit on pressing 'q'
        if cv2.waitKey(100) & 0xFF == ord('q'):
            break

    # Close the OpenCV window when the simulation is stopped
    cv2.destroyAllWindows()

# Start the simulation with the target year data and a default speed factor
run_simulation(year=2018, default_speed_factor=1)
