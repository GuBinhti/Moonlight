import cv2
import time
import datetime
import numpy as np
import os
import pytz

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

# Set the timezone to PST
pst = pytz.timezone("America/Los_Angeles")

# Lunar cycle configuration
LUNAR_CYCLE_DAYS = 29.5
MOON_PHASES = [
    'New Moon', 'Waxing Crescent', 'First Quarter', 'Waxing Gibbous', 
    'Full Moon', 'Waning Gibbous', 'Last Quarter', 'Waning Crescent'
]

MOONRISE_BASE_TIME = datetime.datetime(2018, 1, 1, 18, 0)  # Initial moonrise time (6:00 PM)

def overlay_moon_phase(frame, moon_phase, position, brightness):
    """Overlay a moon phase image on the frame with specific brightness and position."""
    # Get the path of the phase image
    image_path = PHASE_IMAGES.get(moon_phase)
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
        rgb_image = moon_image
        alpha_channel = np.ones((100, 100), dtype=float)

    # Define the region of interest (ROI) within the frame for overlaying the moon image
    x, y = position
    h, w = rgb_image.shape[:2]
    y1, y2 = max(0, y), min(frame.shape[0], y + h)
    x1, x2 = max(0, x), min(frame.shape[1], x + w)
    moon_y1, moon_y2 = max(0, -y), min(h, frame.shape[0] - y)
    moon_x1, moon_x2 = max(0, -x), min(w, frame.shape[1] - x)

    # Blend the moon image into the frame
    for c in range(3):
        frame[y1:y2, x1:x2, c] = (
            alpha_channel[moon_y1:moon_y2, moon_x1:moon_x2] * brightness * rgb_image[moon_y1:moon_y2, moon_x1:moon_x2, c] +
            (1 - alpha_channel[moon_y1:moon_y2, moon_x1:moon_x2] * brightness) * frame[y1:y2, x1:x2, c]
        )

    return frame

def run_simulation(year, default_speed_factor=10000):
    """Run the moon phase simulation with a fixed lunar cycle."""
    # Initialize OpenCV window in windowed fullscreen (maximize the window)
    cv2.namedWindow("Moonlight Simulator", cv2.WINDOW_NORMAL)
    screen_width = 1920
    screen_height = 1080
    cv2.resizeWindow("Moonlight Simulator", screen_width, screen_height)

    # Calculate the center of the screen and elliptical orbit radii for the moon’s path
    center_x, center_y = screen_width // 2, screen_height // 2
    orbit_radius_x = center_x - 200
    orbit_radius_y = center_y - 100

    # Simulation loop
    start_date = datetime.datetime.now()
    moonrise_time = MOONRISE_BASE_TIME
    moon_phase_index = 0

    while True:
        # Calculate the current simulation time adjusted by speed_factor
        adjusted_seconds = (datetime.datetime.now() - start_date).total_seconds() * default_speed_factor
        days_elapsed = adjusted_seconds // 86400  # Convert seconds to days
        simulated_date = moonrise_time + datetime.timedelta(days=days_elapsed)

        # Update moon phase and moonrise time
        moon_phase_index = int((days_elapsed % LUNAR_CYCLE_DAYS) / (LUNAR_CYCLE_DAYS / len(MOON_PHASES)))
        moon_phase = MOON_PHASES[moon_phase_index]
        brightness = PHASE_BRIGHTNESS.get(moon_phase, 1)

        # Adjust moonrise time for each day elapsed
        moonrise = moonrise_time + datetime.timedelta(minutes=50 * days_elapsed)

        # Create a blank frame (black background)
        frame = np.zeros((screen_height, screen_width, 3), dtype=np.uint8)

        # Calculate moon position for elliptical orbit
        angle = (days_elapsed % LUNAR_CYCLE_DAYS) * (360 / LUNAR_CYCLE_DAYS)
        moon_x = int(center_x + orbit_radius_x * np.cos(np.radians(angle)))
        moon_y = int(center_y + orbit_radius_y * np.sin(np.radians(angle)))

        # Overlay the moon phase image at the calculated position with synchronized brightness
        frame = overlay_moon_phase(frame, moon_phase, (moon_x, moon_y), brightness)

        # Display simulated date and time in PST
        cv2.putText(frame, f"Simulated Date: {simulated_date.strftime('%Y-%m-%d %H:%M:%S')}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Phase: {moon_phase}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Moonrise: {moonrise.strftime('%H:%M %Z')}", (10, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Show the frame in the window
        cv2.imshow("Moonlight Simulator", frame)

        # Allow exit on pressing 'q'
        if cv2.waitKey(100) & 0xFF == ord('q'):
            break

    # Close the OpenCV window when the simulation is stopped
    cv2.destroyAllWindows()

# Start the simulation
run_simulation(year=2018, default_speed_factor=1)
