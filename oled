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
from PIL import Image,ImageDraw,ImageFont
logging.basicConfig(level=logging.DEBUG)
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
    # Combine moonrise and moonset times with the simulated date
    moonrise_datetime = datetime.datetime.combine(simulated_time.date(), moonrise_time)
    moonset_datetime = datetime.datetime.combine(simulated_time.date(), moonset_time)

    # Check if the moon is below the horizon
    if simulated_time < moonrise_datetime or simulated_time > moonset_datetime:
        return -90, -1  # Moon is below the horizon

    total_visibility_duration = (moonset_datetime - moonrise_datetime).total_seconds()
    time_since_rise = (simulated_time - moonrise_datetime).total_seconds()
    progress = time_since_rise / total_visibility_duration

    # Altitude: approximate sinusoidal function
    altitude = np.sin(progress * np.pi) * 45  # Max altitude: 45°
    azimuth = 90 + (progress * 180)
    return altitude, azimuth


def overlay_moon_phase(image, moon_phase):
    """Overlay moon phase image on the OLED display."""
    image_path = PHASE_IMAGES.get(moon_phase)
    if not image_path or not os.path.exists(image_path):
        print(f"Image not found for phase: {moon_phase} at path: {image_path}")
        return image

    phase_image = Image.open(image_path).convert("RGBA")
    phase_image = phase_image.resize((128, 128))  # Adjust size to fit the screen
    image.paste(phase_image, (0, 0), phase_image)
    return image


def run_simulation(speed_factor=10000):
    disp = OLED_1in27_rgb.OLED_1in27_rgb()  # Use the correct OLED class
    logging.info("\r 1.27inch rgb OLED ")
    disp.Init()
    disp.clear()

    start_date = datetime.datetime.now()
    start_phase_index = 4  # Full Moon
    lunar_cycle_length = DEFAULT_LUNAR_CYCLE_LENGTH

    while True:
        adjusted_seconds = (datetime.datetime.now() - start_date).total_seconds() * speed_factor
        simulated_time = start_date + datetime.timedelta(seconds=adjusted_seconds)
        days_since_start = (simulated_time - start_date).days

        phase = calculate_phase(simulated_time, start_date, start_phase_index, lunar_cycle_length)
        moonrise_time = calculate_moonrise(start_phase_index, days_since_start, lunar_cycle_length)
        moonset_time = MOONSET_TIME

        # Print information to the console
        print(f"Simulated Time: {simulated_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Phase: {phase}")
        print(f"Moonrise: {moonrise_time}")
        print(f"Moonset: {moonset_time}")
        print("-" * 40)

        # Display only the moon image on the OLED
        image = Image.new('RGB', (disp.width, disp.height), "BLACK")
        image = overlay_moon_phase(image, phase)
        disp.ShowImage(disp.getbuffer(image))

        time.sleep(1)  # Adjust the refresh rate if needed


run_simulation(speed_factor=50000)
