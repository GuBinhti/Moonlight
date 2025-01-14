import cv2
import datetime
import numpy as np
import os

# Set the base path relative to the current working directory
BASE_PATH = os.path.join(os.getcwd(), "Moon Phase")

# Define paths to moon phase images
PHASE_IMAGES = {
    'Waxing Crescent': '/home/tbt/capstone/Moonlight/Moon Phase/Waxing Crescent.png',
    'First Quarter': '/home/tbt/capstone/Moonlight/Moon Phase/Waxing Gibbous.png',
    'Waxing Gibbous': '/home/tbt/capstone/Moonlight/Moon Phase/Waxing Gibbous.png',
    'Full Moon': '/home/tbt/capstone/Moonlight/Moon Phase/Full Moon.png',
    'Waning Gibbous': '/home/tbt/capstone/Moonlight/Moon Phase/Waning Gibbous.png',
    'Last Quarter': '/home/tbt/capstone/Moonlight/Moon Phase/Last Quarter.png',
    'Waning Crescent': '/home/tbt/capstone/Moonlight/Moon Phase/Waning Crescent.png',
    'New Moon': '/home/tbt/capstone/Moonlight/Moon Phase/New Moon.png'
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

DEFAULT_LUNAR_CYCLE_LENGTH = 29  # Days
DEFAULT_MOONRISE_INCREMENT = datetime.timedelta(minutes=50)  # Default 50 minutes later each day
MOONSET_TIME = datetime.time(7, 0)  # Fixed moonset time

def calculate_phase(simulated_date, start_date, start_phase_index, lunar_cycle_length):
    """Determine the current lunar phase based on the simulated date and starting phase."""
    days_since_start = (simulated_date - start_date).total_seconds() / (24 * 3600)
    phase_progress = (days_since_start % lunar_cycle_length) / lunar_cycle_length
    phase_index = (start_phase_index + int(phase_progress * len(LUNAR_PHASES))) % len(LUNAR_PHASES)
    return LUNAR_PHASES[phase_index]

def calculate_moonrise(start_phase_index, days_since_start, lunar_cycle_length):
    """
    Calculate the moonrise time based on the starting phase index and days since start.
    Each day adds a moonrise increment to the initial full moonrise at 6:00 PM.
    """
    initial_moonrise = datetime.time(18, 0)  # 6:00 PM
    moonrise_increment = datetime.timedelta(
        minutes=(DEFAULT_MOONRISE_INCREMENT.total_seconds() / 60) *
                (DEFAULT_LUNAR_CYCLE_LENGTH / lunar_cycle_length)
    )
    total_increment = days_since_start * moonrise_increment
    full_moon_date = datetime.datetime.combine(datetime.date.today(), initial_moonrise)
    current_moonrise = full_moon_date + total_increment
    return current_moonrise.time()

def calculate_altitude_azimuth(simulated_time, moonrise_time, moonset_time):
    """
    Calculate the altitude and azimuth of the moon.
    """
    total_visibility_duration = (moonset_time - moonrise_time).total_seconds()
    if total_visibility_duration <= 0:
        return -90, -1  # Moon is below the horizon

    time_since_rise = (simulated_time - moonrise_time).total_seconds()
    progress = time_since_rise / total_visibility_duration

    if not (0 <= progress <= 1):
        return -90, -1  # Moon is below the horizon

    # Altitude: approximate sinusoidal function
    altitude = np.sin(progress * np.pi) * 45  # Max altitude ~ 45°
    azimuth = 90 + (progress * 180)
    return altitude, azimuth

def overlay_moon_phase(
    frame, moon_phase, position, brightness, 
    use_custom_color=False, custom_hex_color="#FFFFFF"
):
    """
    If use_custom_color is True:
        - Fill the entire frame with the specified custom color (adjusted by brightness).
    Else:
        - Overlay the corresponding moon phase image at 'position' (also adjusted by brightness).
    """
    if use_custom_color:
        # Parse the hex color (strip '#' if present)
        hex_str = custom_hex_color.lstrip('#')
        if len(hex_str) != 6:
            print("Invalid hex color provided. Using white #FFFFFF instead.")
            hex_str = "FFFFFF"

        # Convert hex to integer BGR (OpenCV uses BGR ordering)
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)

        # Scale color by brightness (ensure 0 <= value <= 255)
        adjusted_b = int(b * brightness)
        adjusted_g = int(g * brightness)
        adjusted_r = int(r * brightness)

        # Fill the entire frame with the (brightness-adjusted) color
        frame[:, :] = (adjusted_b, adjusted_g, adjusted_r)

    else:
        # Use the default moon phase image approach
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
                alpha_channel[moon_y1:moon_y2, moon_x1:moon_x2] 
                * brightness 
                * rgb_image[moon_y1:moon_y2, moon_x1:moon_x2, c]
                + (1 - alpha_channel[moon_y1:moon_y2, moon_x1:moon_x2] * brightness)
                * frame[y1:y2, x1:x2, c]
            )

    return frame

def run_simulation(speed_factor=10000):
    print("Available Moon Phases:", ", ".join(LUNAR_PHASES))
    
    # Prompt if user wants to use a custom color
    use_custom_color_input = input("Custom Color? (yes/no): ").strip().lower()
    use_custom_color = (use_custom_color_input == "yes")
    custom_hex_color = "#FFFFFF"
    if use_custom_color:
        custom_hex_color = input("Enter the hex color code you want to use (e.g. #FFCC00): ").strip()
        if not custom_hex_color:
            custom_hex_color = "#FFFFFF"

    selected_phase = input(f"Enter the starting moon phase (default: Full Moon): ").strip().title()
    if not selected_phase:
        selected_phase = "Full Moon"

    # Validate phase input
    start_phase_index = LUNAR_PHASES.index(selected_phase) if selected_phase in LUNAR_PHASES else 4

    custom_cycle_input = input(f"Enter the desired lunar cycle length in days (default: {DEFAULT_LUNAR_CYCLE_LENGTH}): ").strip()
    lunar_cycle_length = float(custom_cycle_input) if custom_cycle_input else DEFAULT_LUNAR_CYCLE_LENGTH

    use_real_time = input("Do you want to use the current real time? (yes/no): ").strip().lower()
    if use_real_time == "yes":
        start_date = datetime.datetime.now()
    else:
        start_hour = int(input("Enter the starting hour (0-23): ").strip())
        start_minute = int(input("Enter the starting minute (0-59): ").strip())
        start_date = datetime.datetime.combine(datetime.date.today(), datetime.time(start_hour, start_minute))
        moonrise_time = calculate_moonrise(start_phase_index, 0, lunar_cycle_length)
        print(f"Based on the selected phase ({selected_phase}), the moon will rise at approximately {moonrise_time}.")

    moonrise_increment = datetime.timedelta(
        minutes=(DEFAULT_MOONRISE_INCREMENT.total_seconds() / 60) 
                * (DEFAULT_LUNAR_CYCLE_LENGTH / lunar_cycle_length)
    )
    current_date = datetime.datetime.now()
    screen_width, screen_height = 1920, 1080

    cv2.namedWindow("Moonlight Simulator", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Moonlight Simulator", screen_width, screen_height)

    # The position is only relevant if we are using images.
    # For custom color, we'll ignore this, since we're filling the entire frame.
    fixed_position = (screen_width // 2 - 50, screen_height // 2 - 50)

    initial_moonrise_time = datetime.datetime.combine(start_date.date(), datetime.time(18, 0))  # 6:00 PM

    while True:
        # How much time has passed in real life since we started the simulation
        adjusted_seconds = (datetime.datetime.now() - current_date).total_seconds() * speed_factor
        simulated_time = start_date + datetime.timedelta(seconds=adjusted_seconds)

        days_since_start = (simulated_time - start_date).days
        current_moonrise = initial_moonrise_time + days_since_start * moonrise_increment
        current_moonset = datetime.datetime.combine(simulated_time.date(), MOONSET_TIME)

        # Check if the moon is visible based on the current simulated time
        is_visible = current_moonrise <= simulated_time <= current_moonset
        
        phase = calculate_phase(simulated_time, start_date, start_phase_index, lunar_cycle_length)
        brightness = PHASE_BRIGHTNESS.get(phase, 1) if is_visible else 0

        altitude, azimuth = calculate_altitude_azimuth(simulated_time, current_moonrise, current_moonset)
        print(f"Simulated Time: {simulated_time}, Phase: {phase}, Altitude: {altitude:.2f}°, Azimuth: {azimuth:.2f}°")

        # Create a black frame to start with
        frame = np.zeros((screen_height, screen_width, 3), dtype=np.uint8)
        
        # If the moon is visible, fill the screen or overlay the image
        if is_visible:
            frame = overlay_moon_phase(
                frame, 
                phase, 
                fixed_position, 
                brightness,
                use_custom_color=use_custom_color, 
                custom_hex_color=custom_hex_color
            )

        # Display text info
        cv2.putText(frame, f"Simulated Date: {simulated_time.strftime('%Y-%m-%d %H:%M:%S')}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Phase: {phase}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Moon Visible: {'Yes' if is_visible else 'No'}", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Moonrise: {current_moonrise.strftime('%Y-%m-%d %H:%M:%S')}", (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Moonset: {current_moonset.strftime('%Y-%m-%d %H:%M:%S')}", (10, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Show the frame
        cv2.imshow("Moonlight Simulator", frame)
        # Press 'q' to quit the loop
        if cv2.waitKey(100) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_simulation(speed_factor=50000)
