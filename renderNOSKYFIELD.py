import cv2
import datetime
import numpy as np
import os

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

# Define a fixed lunar cycle
LUNAR_PHASES = [
    'New Moon',
    'Waxing Crescent',
    'First Quarter',
    'Waxing Gibbous',
    'Full Moon',
    'Waning Gibbous',
    'Last Quarter',
    'Waning Crescent'
]
DEFAULT_LUNAR_CYCLE_LENGTH = 29.5  # Days


def calculate_phase(simulated_date, start_date, start_phase_index, lunar_cycle_length):
    """Determine the current lunar phase based on the simulated date and starting phase."""
    days_since_start = (simulated_date - start_date).total_seconds() / (24 * 3600)
    phase_progress = (days_since_start % lunar_cycle_length) / lunar_cycle_length
    phase_index = (start_phase_index + int(phase_progress * len(LUNAR_PHASES))) % len(LUNAR_PHASES)
    return LUNAR_PHASES[phase_index]


def overlay_moon_phase(frame, moon_phase, position, brightness):
    """Overlay a moon phase image on the frame with specific brightness and position."""
    image_path = PHASE_IMAGES.get(moon_phase)
    if not image_path or not os.path.exists(image_path):
        print(f"Image not found for phase: {moon_phase} at path: {image_path}")
        return frame

    moon_image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if moon_image is None:
        print(f"Error loading image for phase: {moon_phase}")
        return frame

    moon_image = cv2.resize(moon_image, (100, 100))
    if moon_image.shape[2] == 4:
        rgb_image = moon_image[:, :, :3]
        alpha_channel = moon_image[:, :, 3] / 255.0
    else:
        rgb_image = moon_image
        alpha_channel = np.ones((100, 100), dtype=float)

    x, y = position
    h, w = rgb_image.shape[:2]
    y1, y2 = max(0, y), min(frame.shape[0], y + h)
    x1, x2 = max(0, x), min(frame.shape[1], x + w)
    moon_y1, moon_y2 = max(0, -y), min(h, frame.shape[0] - y)
    moon_x1, moon_x2 = max(0, -x), min(w, frame.shape[1] - x)

    for c in range(3):
        frame[y1:y2, x1:x2, c] = (
            alpha_channel[moon_y1:moon_y2, moon_x1:moon_x2] * brightness * rgb_image[moon_y1:moon_y2, moon_x1:moon_x2, c] +
            (1 - alpha_channel[moon_y1:moon_y2, moon_x1:moon_x2] * brightness) * frame[y1:y2, x1:x2, c]
        )

    return frame


def run_simulation(start_year, day_speed_factor=10000, night_speed_factor=10000):
    print("Available Moon Phases:", ", ".join(LUNAR_PHASES))
    selected_phase = input(f"Enter the starting moon phase (default: Full Moon): ").strip().title()
    if not selected_phase:
        selected_phase = "Full Moon"

    start_phase_index = LUNAR_PHASES.index(selected_phase) if selected_phase in LUNAR_PHASES else 4
    custom_cycle_input = input(f"Enter the desired lunar cycle length in days (default: {DEFAULT_LUNAR_CYCLE_LENGTH}): ").strip()
    lunar_cycle_length = float(custom_cycle_input) if custom_cycle_input else DEFAULT_LUNAR_CYCLE_LENGTH

    # Adjust speed factors if custom lunar cycle length is provided
    day_speed_factor *= DEFAULT_LUNAR_CYCLE_LENGTH / lunar_cycle_length

    start_date = datetime.datetime(start_year, 1, 1)
    current_date = datetime.datetime.now()
    screen_width, screen_height = 1920, 1080

    cv2.namedWindow("Moonlight Simulator", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Moonlight Simulator", screen_width, screen_height)

    center_x, center_y = screen_width // 2, screen_height // 2
    orbit_radius_x, orbit_radius_y = center_x - 200, center_y - 100

    while True:
        adjusted_seconds = (datetime.datetime.now() - current_date).total_seconds()

        # Simulate time progression
        simulated_time = start_date

        # Time loop to adjust simulated time based on day/night
        sim_seconds = 0
        while sim_seconds < adjusted_seconds:
            hour = simulated_time.hour
            if 6 <= hour < 18:
                increment = min(adjusted_seconds - sim_seconds, 1)
                sim_seconds += increment
                simulated_time += datetime.timedelta(seconds=increment * day_speed_factor)
            else:
                increment = min(adjusted_seconds - sim_seconds, 1)
                sim_seconds += increment
                simulated_time += datetime.timedelta(seconds=increment * night_speed_factor)

        phase = calculate_phase(simulated_time, start_date, start_phase_index, lunar_cycle_length)
        brightness = PHASE_BRIGHTNESS.get(phase, 1)

        # Calculate moon position (simple simulation)
        # Moon is visible during nighttime
        hour = simulated_time.hour
        if 18 <= hour or hour < 6:
            # Map hour to angle (6 PM to 6 AM maps to 0 to 180 degrees)
            if hour >= 18:
                angle = ((hour - 18) / 12.0) * 180
            else:
                angle = ((hour + 6) / 12.0) * 180
            moon_x = int(center_x + orbit_radius_x * np.cos(np.radians(angle)))
            moon_y = int(center_y + orbit_radius_y * np.sin(np.radians(angle)))
            moon_visible = True
        else:
            moon_visible = False

        # Create frame
        frame = np.zeros((screen_height, screen_width, 3), dtype=np.uint8)

        if moon_visible:
            frame = overlay_moon_phase(frame, phase, (moon_x, moon_y), brightness)

        # Display simulated information
        cv2.putText(frame, f"Simulated Date: {simulated_time.strftime('%Y-%m-%d %H:%M:%S')}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Phase: {phase}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Time Speed Factor: Day {day_speed_factor}, Night {night_speed_factor}", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.imshow("Moonlight Simulator", frame)
        if cv2.waitKey(100) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()


# Start the simulation
run_simulation(start_year=2022)
