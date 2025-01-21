import os
import sys
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

import datetime
import numpy as np
import logging    
import time
import traceback
from waveshare_OLED import OLED_1in27_rgb
from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(level=logging.DEBUG)

# -------------------------------------------------------------------------
#                        DEFAULTS AND CONSTANTS
# -------------------------------------------------------------------------
PHASE_IMAGES = {
    'Waxing Crescent': '/home/moonlight/Desktop/Moon Phase/Waxing Crescent.png',
    'First Quarter': '/home/moonlight/Desktop/Moon Phase/First Quarter.png',
    'Waxing Gibbous': '/home/moonlight/Desktop/Moon Phase/Waxing Gibbous.png',
    'Full Moon': '/home/moonlight/Desktop/Moon Phase/Full Moon.png',
    'Waning Gibbous': '/home/moonlight/Desktop/Moon Phase/Waning Gibbous.png',
    'Last Quarter': '/home/moonlight/Desktop/Moon Phase/Last Quarter.png',
    'Waning Crescent': '/home/moonlight/Desktop/Moon Phase/Waning Crescent.png',
    'New Moon': '/home/moonlight/Desktop/Moon Phase/New Moon.png'
}

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

# Default 29-day lunar cycle.
DEFAULT_LUNAR_CYCLE_LENGTH = 29.0  
# For a 29-day cycle, the moon rises ~50 minutes later each day.
DEFAULT_MOONRISE_INCREMENT = datetime.timedelta(minutes=50)  
MOONSET_TIME = datetime.time(7, 0)  # fixed moonset time

# -------------------------------------------------------------------------
#                             CALCULATIONS
# -------------------------------------------------------------------------
def calculate_phase(simulated_time, start_time, start_phase_index, lunar_cycle_length):
    """
    Determine the current lunar phase as a fraction of 'lunar_cycle_length'.
    This uses continuous time to allow the phase to shift gradually during each day.
    """
    # How many simulated days have passed (fractional)
    days_since_start = (simulated_time - start_time).total_seconds() / (24 * 3600)
    # fraction of the current cycle
    phase_progress = (days_since_start % lunar_cycle_length) / lunar_cycle_length
    # index into LUNAR_PHASES
    phase_index = (start_phase_index + int(phase_progress * len(LUNAR_PHASES))) % len(LUNAR_PHASES)
    return LUNAR_PHASES[phase_index]

def calculate_moonrise(day_count, daily_increment):
    """
    Return today's moonrise time based on the integer 'day_count' and the per-day increment.
    The moonrise only changes at the start of each new simulated day.
    """
    initial_moonrise = datetime.time(18, 0)  # baseline: 6:00 PM
    # total shift = day_count * daily_increment
    total_increment = day_count * daily_increment
    base_datetime = datetime.datetime.combine(datetime.date.today(), initial_moonrise)
    current_moonrise = base_datetime + total_increment
    return current_moonrise.time()

def calculate_altitude_azimuth(simulated_time, moonrise_time, moonset_time):
    """
    Simplistic calculation of the moon's altitude and azimuth.
    If the moon is below the horizon, returns (-90, -1).
    """
    date_today = simulated_time.date()
    moonrise_datetime = datetime.datetime.combine(date_today, moonrise_time)
    moonset_datetime = datetime.datetime.combine(date_today, moonset_time)

    if simulated_time < moonrise_datetime or simulated_time > moonset_datetime:
        return -90, -1  # moon below horizon

    total_visibility = (moonset_datetime - moonrise_datetime).total_seconds()
    time_since_rise = (simulated_time - moonrise_datetime).total_seconds()
    progress = time_since_rise / total_visibility

    # altitude: sinusoidal from 0° -> 45° -> 0°
    altitude = np.sin(progress * np.pi) * 45
    # azimuth: from 90° (East) -> 270° (West)
    azimuth = 90 + (progress * 180)
    return altitude, azimuth

def overlay_moon_phase(image, moon_phase):
    """
    Overlay the given moon phase image on top of 'image'.
    """
    image_path = PHASE_IMAGES.get(moon_phase)
    if not image_path or not os.path.exists(image_path):
        print(f"Warning: No image found for phase '{moon_phase}' at path: {image_path}")
        return image

    phase_image = Image.open(image_path).convert("RGBA")
    phase_image = phase_image.resize((96, 96))  # adjust to your OLED size
    image.paste(phase_image, (0, 0), phase_image)
    return image

# -------------------------------------------------------------------------
#                          USER INTERFACE
# -------------------------------------------------------------------------
def get_user_choices():
    """
    Ask the user:
      1) Desired lunar cycle length in days.
      2) Whether to use a custom color or the default moon phase images.
      3) The custom color code if selected.
      4) Speed factor for the simulation (how many simulated seconds per real second).
    Returns a dictionary with the user settings.
    """
    print("Welcome to the Moon Simulation Program!")
    print("This will simulate a lunar cycle in 'simulated time', which can run faster or slower than real time.\n")
    print("Press Enter at any prompt to use the default, or type 'q' to quit.\n")

    # 1) Lunar cycle length in days
    while True:
        user_input = input(f"Enter the desired lunar cycle length in days (default={DEFAULT_LUNAR_CYCLE_LENGTH}): ").strip()
        if user_input.lower() == 'q':
            sys.exit("Exiting program.")
        if not user_input:
            lunar_cycle_length = DEFAULT_LUNAR_CYCLE_LENGTH
            break
        try:
            lunar_cycle_length = float(user_input)
            if lunar_cycle_length <= 0:
                print("Please enter a positive number of days.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a positive number or press Enter for default.")

    # 2) Custom color vs. moon phase images
    use_custom_color = False
    while True:
        choice = input("Use a custom color instead of moon phase images? (y/n, default=n): ").strip().lower()
        if choice == 'q':
            sys.exit("Exiting program.")
        if choice == '' or choice == 'n':
            use_custom_color = False
            break
        elif choice == 'y':
            use_custom_color = True
            break
        else:
            print("Invalid input. Enter 'y', 'n', or press Enter for default.")

    # 3) If using custom color, get the hex code
    user_hex_color = ""
    if use_custom_color:
        while True:
            color_input = input("Enter a custom hex color code (e.g., #FF0000) or press Enter to cancel: ").strip()
            if color_input.lower() == 'q':
                sys.exit("Exiting program.")
            if not color_input:
                print("No color code entered. Will show moon phase images instead.")
                use_custom_color = False
                break
            if not color_input.startswith('#') or len(color_input) not in [4, 7, 9]:
                print("Invalid hex format. Must be #RGB, #RRGGBB, or #RRGGBBAA.")
            else:
                user_hex_color = color_input
                break

    # 4) Speed factor
    #    e.g. 1 = real time, 2 = twice as fast, 0.5 = half speed, 100 = 100x, etc.
    speed_factor = 1.0
    while True:
        speed_input = input("Enter a speed factor (default=1.0, e.g. 10 = 10x faster): ").strip()
        if speed_input.lower() == 'q':
            sys.exit("Exiting program.")
        if not speed_input:
            speed_factor = 1.0
            break
        try:
            sf = float(speed_input)
            if sf <= 0:
                print("Speed factor must be positive. Try again.")
                continue
            speed_factor = sf
            break
        except ValueError:
            print("Invalid input. Please enter a positive number or press Enter for default (1.0).")

    return {
        "lunar_cycle_length": lunar_cycle_length,
        "use_custom_color": use_custom_color,
        "custom_color": user_hex_color,
        "speed_factor": speed_factor
    }

# -------------------------------------------------------------------------
#                            MAIN SIMULATION
# -------------------------------------------------------------------------
def run_simulation():
    """
    Main loop:
      - User sets lunar cycle length in days and a simulation speed factor.
      - The daily moonrise increment scales based on that length (50 min for 29 days => scaled).
      - We advance 'simulated time' at the chosen speed factor.
      - The moonrise time is static for each integer day in *simulated* time.
    """
    choices = get_user_choices()
    lunar_cycle_length = choices["lunar_cycle_length"]
    use_custom_color = choices["use_custom_color"]
    custom_color = choices["custom_color"]
    speed_factor = choices["speed_factor"]

    # For a 29-day cycle, daily increment is 50 minutes.
    # If user picks X days, daily increment = 50 * (29 / X) minutes.
    daily_moonrise_increment = DEFAULT_MOONRISE_INCREMENT * (DEFAULT_LUNAR_CYCLE_LENGTH / lunar_cycle_length)

    # Initialize display
    disp = OLED_1in27_rgb.OLED_1in27_rgb()
    logging.info("\r1.27inch RGB OLED initializing...")
    disp.Init()
    disp.clear()

    # Record the real start time and define our simulated start time
    real_start_time = datetime.datetime.now()
    simulated_start_time = datetime.datetime.now()  # We'll treat "now" as day 0
    # Start phase index: 4 => 'Full Moon' (choose any you like)
    start_phase_index = 4  

    try:
        while True:
            # Measure how long has passed in real time
            real_now = datetime.datetime.now()
            real_elapsed = real_now - real_start_time

            # Convert that to simulated seconds
            sim_elapsed_seconds = real_elapsed.total_seconds() * speed_factor
            # Our simulated time
            simulated_time = simulated_start_time + datetime.timedelta(seconds=sim_elapsed_seconds)

            # Figure out how many *whole days* have elapsed in the simulation
            # This integer day count determines the static moonrise for that day.
            day_count = int((simulated_time - simulated_start_time).total_seconds() // (24 * 3600))

            # Calculate today's moonrise time (static all day)
            moonrise_time = calculate_moonrise(day_count, daily_moonrise_increment)

            # Calculate the current lunar phase (updates gradually during each day)
            current_phase = calculate_phase(
                simulated_time=simulated_time,
                start_time=simulated_start_time,
                start_phase_index=start_phase_index,
                lunar_cycle_length=lunar_cycle_length
            )

            # Approximate altitude & azimuth
            altitude, azimuth = calculate_altitude_azimuth(simulated_time, moonrise_time, MOONSET_TIME)

            # Print info to the console
            print(f"[Real Time: {real_now:%Y-%m-%d %H:%M:%S}]")
            print(f" Simulated Time: {simulated_time:%Y-%m-%d %H:%M:%S} (Day {day_count})")
            print(f" Lunar Cycle Length: {lunar_cycle_length} days")
            print(f" Phase: {current_phase}")
            print(f" Moonrise: {moonrise_time}, Moonset: {MOONSET_TIME}")
            print(f" Altitude: {altitude:.2f}°, Azimuth: {azimuth:.2f}°")
            print("-" * 50)

            # Prepare an image for the display
            if use_custom_color and custom_color:
                image = Image.new('RGB', (disp.width, disp.height), custom_color)
            else:
                image = Image.new('RGB', (disp.width, disp.height), "BLACK")
                image = overlay_moon_phase(image, current_phase)

            disp.ShowImage(disp.getbuffer(image))

            # Pause in real time before the next update
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nSimulation interrupted by user.")
    except Exception as e:
        print("Error occurred:", e)
        traceback.print_exc()
    finally:
        disp.clear()
        print("Exiting simulation...")

if __name__ == '__main__':
    run_simulation()
