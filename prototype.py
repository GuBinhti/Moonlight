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
import RPi.GPIO as GPIO
import time

servo_pin = 24
def setup_servo(pin):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.OUT)
    

    # Using frequency 50 Hz
    pwm = GPIO.PWM(pin, 50)
    pwm.start(0) 
    return pwm


def set_servo_angle(pwm, angle):
    duty_cycle = ((500 + (angle/270)*2000)/20000)*100  # Map angle to servo range (2% to 12%)
    pwm.ChangeDutyCycle(duty_cycle)
    time.sleep(0.5)  # Allow the servo to reach the position
    pwm.ChangeDutyCycle(0)  # Stop sending signal to prevent jitter

# Define paths to moon phase images
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
    Adjusts moonrise increment based on lunar cycle.
    """
    initial_moonrise = datetime.time(18, 0)  # 6:00 PM
    moonrise_increment_minutes = (DEFAULT_MOONRISE_INCREMENT.total_seconds() / 60) * (DEFAULT_LUNAR_CYCLE_LENGTH / lunar_cycle_length)
    moonrise_increment = datetime.timedelta(minutes=moonrise_increment_minutes)
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
    #if simulated_time < moonrise_datetime or simulated_time > moonset_datetime:
        #return -90, -1  # Moon is below the horizon

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
    phase_image = phase_image.resize((96, 96))  # Adjust size to fit the screen
    image.paste(phase_image, (0, 0), phase_image)
    return image


def run_simulation(speed_factor=10000):
    disp = OLED_1in27_rgb.OLED_1in27_rgb()  # Use the correct OLED class
    logging.info("\r 1.27inch rgb OLED ")
    disp.Init()
    disp.clear()

    # Prompt the user for custom lunar cycle length
    user_input = input(f"Enter the lunar cycle length in days (default {DEFAULT_LUNAR_CYCLE_LENGTH}): ").strip()
    lunar_cycle_length = float(user_input) if user_input else DEFAULT_LUNAR_CYCLE_LENGTH

    # Prompt the user for a custom hex code
    # If the user enters something like "#FF0000", the entire screen will be that color
    user_input_hex = input("Enter a custom hex color code (e.g. #FF0000) or press Enter to use moon phase images: ").strip()

    # Validate the hex code if needed (this is optional and simplistic):
    if user_input_hex and not user_input_hex.startswith('#'):
        print("Invalid hex code format. It should start with '#' (e.g., #FF0000).")
        user_input_hex = ""

    start_date = datetime.datetime.now()
    start_phase_index = 4  # Full Moon        
    servo_pwm = setup_servo(servo_pin)
    set_servo_angle (servo_pwm, 0)

        
    while True:
        adjusted_seconds = (datetime.datetime.now() - start_date).total_seconds() * speed_factor
        simulated_time = start_date + datetime.timedelta(seconds=adjusted_seconds)
        days_since_start = (simulated_time - start_date).days
        
        if days_since_start >= lunar_cycle_length:
            break

        phase = calculate_phase(simulated_time, start_date, start_phase_index, lunar_cycle_length)
        moonrise_time = calculate_moonrise(start_phase_index, days_since_start, lunar_cycle_length)
        moonset_time = MOONSET_TIME
        
        alt, azi = calculate_altitude_azimuth(simulated_time, moonrise_time, moonset_time)
        zenith = 90- alt
        servo_angle = max(0, min(180, zenith))
        set_servo_angle(servo_pwm, servo_angle)

        
        # Print information to the console
        
        print(f"Simulated Time: {simulated_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Phase: {phase}")
        print(f"Moonrise: {moonrise_time}")
        print(f"Zentith: {zenith}")
        print(f"Moonset: {moonset_time}")
        print(f"Altitude: {alt} Azimuth: {azi}")
        print("-" * 40)

        # Create a new blank image
        # If the user provided a hex code, fill the entire screen with that color
        # Otherwise, overlay the appropriate moon phase image
        if user_input_hex:
            image = Image.new('RGB', (disp.width, disp.height), user_input_hex)
        else:
            image = Image.new('RGB', (disp.width, disp.height), "BLACK")
            image = overlay_moon_phase(image, phase)

        disp.ShowImage(disp.getbuffer(image))
        time.sleep(1)


if __name__ == '__main__':

    run_simulation(speed_factor=1000)
