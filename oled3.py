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

# Default: 29-day lunar cycle
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
    This uses continuous time so the phase shifts gradually during each day.
    """
    # How many simulated days have passed (including fractions)
    days_since_start = (simulated_time - start_time).total_seconds() / (24 * 3600)
    # fraction of the current cycle
    phase_progress = (days_since_start % lunar_cycle_length) / lunar_cycle_length
    # index into LUNAR_PHASES
    phase_index = (start_phase_index + int(phase_progress * len(LUNAR_PHASES))) % len(LUNAR_PHASES)
    return LUNAR_PHASES[phase_index]

def calculate_moonrise(day_count_in_cycle, daily_increment):
    """
    Return today's moonrise time based on:
      - day_count_in_cycle (int), e.g. 0 for cycle day 0, 1 for cycle day 1, etc.
      - daily_increment: how much moonrise shifts *each* day (e.g. 50min -> 25min -> 100min)
    If day_count_in_cycle = 0, we reset back to 18:00 (6 PM).
    """
    initial_moonrise = datetime.time(18, 0)  # baseline: 6:00 PM
    total_increment = day_count_in_cycle * daily_increment
    base_datetime = datetime.datetime.combine(datetime.date.today(), initial_moonrise)
    current_moonrise = base_datetime + total_increment
    return current_moonrise.time()

def calculate_altitude_azimuth(simulated_time, moonrise_time, moonset_time):
    """
    Simplistic calculation of the moon's altitude and azimuth.
    Returns altitude, azimuth in degrees.
    """
    date_today = simulated_time.date()
    moonrise_datetime = datetime.datetime.combine(date_today, moonrise_time)
    moonset_datetime = datetime.datetime.combine(date_today, moonset_time)

    if simulated_time < moonrise_datetime or simulated_time > moonset_datetime:
        # If the moon is below the horizon, we still return negative altitude, 
        # but won't override the display with black in this version.
        return -90, -1

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
    phase_image = phase_image.resize((96, 96))
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
    print("Simulate a lunar cycle in 'simulated time', which can run faster or slower than real time.")
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
      - The moonrise time is static for each *day in the current cycle*.
      - Once we pass the cycle boundary, we reset day_count_in_cycle -> 0 => 18:00 again.
      - The display always shows either the custom color or the moon phase image,
        even if the altitude < 0.
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
    simulated_start_time = real_start_time  # We'll treat "now" as the start
    # Start phase index: 4 => 'Full Moon' (or any other index you prefer)
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

            # -------------------------------------------------------------------
            # Determine how many *days* have elapsed in the current cycle
            # -------------------------------------------------------------------
            # 1) total days since simulation started
            total_sim_days = (simulated_time - simulated_start_time).total_seconds() / (24*3600)
            # 2) how many days into the *current* cycle are we? (fractional)
            days_into_cycle = total_sim_days % lunar_cycle_length
            # 3) integer day count in this cycle => used for moonrise offset
            day_count_in_cycle = int(days_into_cycle)

            # Calculate today's moonrise time
            moonrise_time = calculate_moonrise(day_count_in_cycle, daily_moonrise_increment)

            # Calculate the current lunar phase
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
            print(f" Simulated Time: {simulated_time:%Y-%m-%d %H:%M:%S}")
            print(f"  -> {total_sim_days:.2f} sim days since start")
            print(f"  -> {days_into_cycle:.2f} days into the current {lunar_cycle_length}-day cycle (day_count_in_cycle = {day_count_in_cycle})")
            print(f" Moonrise: {moonrise_time}, Moonset: {MOONSET_TIME}")
            print(f" Altitude: {altitude:.2f}°, Azimuth: {azimuth:.2f}°")
            print(f" Phase: {current_phase}")
            print("-" * 60)

            # -------------------------------------------------------------
            # Always display either the custom color or moon phase image
            # even if altitude < 0 (moon below horizon).
            # -------------------------------------------------------------
            if use_custom_color and custom_color:
                image = Image.new('RGB', (disp.width, disp.height), custom_color)
            else:
                image = Image.new('RGB', (disp.width, disp.height), "BLACK")
                image = overlay_moon_phase(image, current_phase)

            # Show the image on the display
            disp.ShowImage(disp.getbuffer(image))

            # Pause briefly in real time before the next update
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
