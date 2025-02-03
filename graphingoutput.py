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
import time
import matplotlib.pyplot as plt


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

def run_simulation(speed_factor=10000):
    # Prompt the user for custom lunar cycle length
    user_input = input(f"Enter the lunar cycle length in days (default {DEFAULT_LUNAR_CYCLE_LENGTH}): ").strip()
    lunar_cycle_length = float(user_input) if user_input else DEFAULT_LUNAR_CYCLE_LENGTH

    start_date = datetime.datetime.now()
    real_time = start_date
    start_phase_index = 4  # Full Moon
    time_counter = 0
    time_array = []
    azi_array = []

    while True:
        real_time += datetime.timedelta(minutes=30)           
        adjusted_seconds = (real_time - start_date).total_seconds()
        simulated_time = start_date + datetime.timedelta(seconds=adjusted_seconds)
        days_since_start = (simulated_time - start_date).days

        
        if days_since_start >= lunar_cycle_length:
            break

        if time_counter >= 48:
            break

        phase = calculate_phase(simulated_time, start_date, start_phase_index, lunar_cycle_length)
        moonrise_time = calculate_moonrise(start_phase_index, days_since_start, lunar_cycle_length)
        moonset_time = MOONSET_TIME
        
        alt, azi = calculate_altitude_azimuth(simulated_time, moonrise_time, moonset_time)
        zenith = 90- alt

        time_array.append(time_counter)
        azi_array.append(azi)

        # Print information to the console
        print(f"Simulated Time: {simulated_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Phase: {phase}")
        print(f"Moonrise: {moonrise_time}")
        print(f"Zentith: {zenith}")
        print(f"Moonset: {moonset_time}")
        print(f"Altitude: {alt} Azimuth: {azi}")
        print("-" * 40)

        time_counter += 1
    
    print(f"Time Array: {time_array}")
    print(f"Azimuth Array: {azi_array}")

    plt.plot(time_array, azi_array)
    plt.xlabel('Time From Start (in 30 minute increments)')
    plt.ylabel('Azimuth')
    plt.title('Azimuth vs Time')

    plt.show()

    

if __name__ == '__main__':
    run_simulation(speed_factor=10000)
