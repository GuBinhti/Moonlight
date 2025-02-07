import os
import sys
# picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
# libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
# if os.path.exists(libdir):
#     sys.path.append(libdir)
import numpy as np
import logging    
import time
import traceback
#from waveshare_OLED import OLED_1in27_rgb
# from PIL import Image, ImageDraw, ImageFont
# logging.basicConfig(level=logging.DEBUG)
#import RPi.GPIO as GPIO
import datetime
import matplotlib.pyplot as plt

servo_pin = 24
# def setup_servo(pin):
#     GPIO.setmode(GPIO.BCM)
#     GPIO.setup(pin, GPIO.OUT)
#     # Using frequency 50 Hz
#     pwm = GPIO.PWM(pin, 50)
#     pwm.start(0) 
#     return pwm

def set_servo_angle(pwm, angle):
    duty_cycle = ((500 + (angle/270)*2000)/20000)*100  # Map angle to servo range (2% to 12%)
    pwm.ChangeDutyCycle(duty_cycle)
    time.sleep(0.5)  # Allow the servo to reach the position
    pwm.ChangeDutyCycle(0)  # Stop sending signal to prevent jitter

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
    'Full Moon',
    'Waning Gibbous',
    'Last Quarter',
    'Waning Crescent',
    'New Moon',
    'Waxing Crescent',
    'First Quarter',
    'Waxing Gibbous'
]

# Default phase lengths (sum = 29 days)
MoonPhaseLengthInDays = {
    'Full Moon':       1,
    'Waning Gibbous':  6,
    'Last Quarter':    1,
    'Waning Crescent': 6,
    'New Moon':        1,
    'Waxing Crescent': 6,
    'First Quarter':   1,
    'Waxing Gibbous':  7
}

DEFAULT_LUNAR_CYCLE_LENGTH = 29   # Days in the "default" cycle
DEFAULT_LATER_PER_DAY = 50        # 50-minute shift in moonrise daily
SUNSET_HOUR = 18                  # 6 PM
SUNRISE_HOUR = 6                  # 6 AM


def scale_phases(target_cycle_length):

    base_cycle_length = 29
    scale_factor = target_cycle_length / base_cycle_length
    
    scaled_phases = {}
    
    for phase in LUNAR_PHASES:
        original_length = MoonPhaseLengthInDays[phase]
        
        if scale_factor >= 1:
            # Scale all phases normally by flooring
            new_length = int(original_length * scale_factor)
            new_length = max(new_length, 1)
        else:
            # If scale_factor < 1, multi-day phases get scaled down
            # Single-day phases remain 1 day
            if original_length == 1:
                new_length = 1
            else:
                new_length = int(original_length * scale_factor)
                new_length = max(new_length, 1)
        
        scaled_phases[phase] = new_length
    
    new_total = sum(scaled_phases.values())
    return scaled_phases, new_total

def get_scaled_phase(day_in_cycle, scaled_phases):
    cumulative = 0
    for phase in LUNAR_PHASES:
        length = scaled_phases[phase]
        if cumulative <= day_in_cycle < (cumulative + length):
            return phase
        cumulative += length
    return 'Unknown Phase'

def calculate_moonrise_times_scaled(target_cycle_length):

    # 1) Round user input to the nearest integer
    rounded_cycle_length = int(round(target_cycle_length))
    if rounded_cycle_length != target_cycle_length:
        print(f"Requested {target_cycle_length:.2f} days; rounding to {rounded_cycle_length} days.")
    else:
        print(f"User requested an integer cycle of {rounded_cycle_length} days.")
    
    # 2) Scale phases
    scaled_phases, new_total_days = scale_phases(rounded_cycle_length)
    print(f"  => Scaled phases sum to {new_total_days} days in total.\n")

    # 3) Daily offset (scale_factor = (rounded_cycle_length / 29))
    scale_factor = float(rounded_cycle_length) / 29.0
    minutes_later_per_day = 50.0 / scale_factor
    
    # 4) Approximate new_moon_day ~ 48% of new_total_days
    new_moon_day = int(round((14.0 / 29.0) * new_total_days))
    
    results = []
    base_time_minutes = SUNSET_HOUR * 60  # 18:00 => 1080
    
    for day in range(new_total_days):
        phase = get_scaled_phase(day, scaled_phases)
        
        # --- Moonrise ---
        if day < new_moon_day:
            offset_minutes = int(round(day * minutes_later_per_day))
            total_minutes = base_time_minutes + offset_minutes
            rise_hour = (total_minutes // 60) % 24
            rise_minute = total_minutes % 60
            moonrise_time = datetime.time(rise_hour, rise_minute)
        elif day == new_moon_day:
            moonrise_time = None
        else:
            # After new moon => always 18:00
            moonrise_time = datetime.time(18, 0)
        
        # --- Moonset ---
        if day < new_moon_day:
            moonset_time = datetime.time(6, 0)
        elif day == new_moon_day:
            moonset_time = None
        else:
            offset_after_new_moon = int(round((day - new_moon_day) * minutes_later_per_day))
            total_set_minutes = (SUNSET_HOUR * 60) + offset_after_new_moon
            set_hour = (total_set_minutes // 60) % 24
            set_minute = total_set_minutes % 60
            moonset_time = datetime.time(set_hour, set_minute)
        
        results.append({
            'day': day,
            'phase': phase,
            'moonrise_time': moonrise_time,
            'moonset_time': moonset_time
        })
    
    return results


def print_moon_schedule(schedule):

    print(f"{'Day':>3} | {'Phase':<16} | {'Moonrise':>8} | {'Moonset':>8}")
    print("-" * 55)
    for entry in schedule:
        day = entry['day']
        phase = entry['phase']
        mr_time = entry['moonrise_time']
        ms_time = entry['moonset_time']
        
        mr_str = mr_time.strftime('%H:%M') if mr_time else "None"
        ms_str = ms_time.strftime('%H:%M') if ms_time else "None"
        
        print(f"{day:3d} | {phase:<16} | {mr_str:>8} | {ms_str:>8}")

def plot_moon_schedule_times(schedule):

    days = []
    rise_hours = []
    set_hours = []
    
    def to_decimal_hour(t):
        """Convert datetime.time -> decimal hour, e.g. 18:30 => 18.5"""
        return t.hour + t.minute / 60.0 if t else None

    for entry in schedule:
        day_label = entry['day'] + 1
        rise_hours.append(to_decimal_hour(entry['moonrise_time']))
        set_hours.append(to_decimal_hour(entry['moonset_time']))
        days.append(day_label)
    
    plt.figure(figsize=(10,5))
    plt.plot(days, rise_hours, marker='o', label='Moonrise', color='blue')
    plt.plot(days, set_hours, marker='o', label='Moonset',  color='red')
    
    # Format
    plt.title('Moonrise and Moonset Times')
    plt.xlabel('Day in Lunar Cycle')
    plt.ylabel('Time of Day (hours, 0=Midnight, 12=Noon, 24=Midnight)')
    plt.xticks(range(1, max(days) + 1))
    plt.yticks(range(0, 25, 2))
    plt.ylim(0, 24)
    plt.grid(True)
    plt.legend()
    plt.show()

def plot_moon_schedule_phases(schedule):
    # map each phase to an integer index 0..7
    phase_indices = []
    days = []
    for entry in schedule:
        day_label = entry['day'] + 1
        days.append(day_label)
        p_idx = LUNAR_PHASES.index(entry['phase']) if entry['phase'] in LUNAR_PHASES else -1
        phase_indices.append(p_idx)
    
    plt.figure(figsize=(10,4))
    plt.scatter(days, phase_indices, marker='o', color='green')
    
    # Set Y ticks to show phase names
    plt.yticks(range(len(LUNAR_PHASES)), LUNAR_PHASES)
    plt.xlabel("Day in Lunar Cycle")
    plt.ylabel("Lunar Phase")
    plt.title("Lunar Phase by Day")
    plt.grid(True)
    plt.show()


if __name__ == "__main__":
    user_input = input(f"Enter the number of days for the lunar cycle (default={DEFAULT_LUNAR_CYCLE_LENGTH}): ")
    try:
        if user_input.strip():
            user_cycle_length = float(user_input.strip())
        else:
            user_cycle_length = DEFAULT_LUNAR_CYCLE_LENGTH
    except ValueError:
        print("Invalid input. Using default 29 days.")
        user_cycle_length = DEFAULT_LUNAR_CYCLE_LENGTH


    moon_schedule = calculate_moonrise_times_scaled(user_cycle_length)


    print_moon_schedule(moon_schedule)

    plot_moon_schedule_times(moon_schedule)

    plot_moon_schedule_phases(moon_schedule)
