import os
import sys
import numpy as np
import logging    
import time
import traceback
import math
# import RPi.GPIO as GPIO
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
# from PIL import Image, ImageDraw, ImageFont
# from waveshare_OLED import OLED_1in27_rgb
# picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
# libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
# if os.path.exists(libdir):
# #     sys.path.append(libdir)
# logging.basicConfig(level=logging.DEBUG)

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

# Default phase lengths (sum = 28 days)
MoonPhaseLengthDays = { # maybe break into percentages
    'Full Moon':       1,
    'Waning Gibbous':  6,
    'Last Quarter':    1,
    'Waning Crescent': 6,
    'New Moon':        1,
    'Waxing Crescent': 6,
    'First Quarter':   1,
    'Waxing Gibbous':  6
}

MoonPhaseChecker = { 
    'Full Moon':       'x',
    'Waning Gibbous':  'o',
    'Last Quarter':    'x',
    'Waning Crescent': 'o',
    'New Moon':        'x',
    'Waxing Crescent': 'o',
    'First Quarter':   'x',
    'Waxing Gibbous':  'o'
}


DEFAULT_LUNAR_CYCLE_LENGTH = 28   # Days in the "default" cycle
DEFAULT_LATER_PER_DAY = (50*28) / 29 # minutes later each day for a 28 day cycle 24 hours
SUNSET_HOUR = 18                  # 6 PM
SUNRISE_HOUR = 6                  # 6 AM

def get_num_phases(target_cycle_length):
    scalar = target_cycle_length / DEFAULT_LUNAR_CYCLE_LENGTH
    scaled_phases = {}
    for phase in LUNAR_PHASES:
        if scalar >= 1:
            if MoonPhaseChecker[phase] == 'x':
                new_length = math.floor(scalar * MoonPhaseLengthDays[phase])
            else:
                new_length = math.ceil(scalar * MoonPhaseLengthDays[phase])
        if scalar < 1:
            if MoonPhaseChecker[phase] == 'x':
                new_length = math.ceil(scalar * MoonPhaseLengthDays[phase])
            else:
                new_length = math.floor(scalar * MoonPhaseLengthDays[phase])
        scaled_phases[phase] = new_length
    new_total = sum(scaled_phases.values())

    if new_total != target_cycle_length:
        if new_total > target_cycle_length:
            for phase in MoonPhaseChecker:
                if MoonPhaseChecker[phase] == 'o':
                    tempLength = scaled_phases[phase]
                    tempLength -= 1
                    scaled_phases[phase] = tempLength
                    new_total = sum(scaled_phases.values())
                    if new_total == target_cycle_length:
                        break
        else:
            for phase in MoonPhaseChecker:
                if MoonPhaseChecker[phase] == 'o':
                    tempLength = scaled_phases[phase]
                    tempLength += 1
                    scaled_phases[phase] = tempLength
                    new_total = sum(scaled_phases.values())
                    if new_total == target_cycle_length:
                        break      
    
    # print(new_total)
    # print(scaled_phases)
    return scaled_phases, new_total

def calculate_moonrise_times(target_cycle_length):
    scaled_phases, new_total_days = get_num_phases(target_cycle_length)
    scale_factor = float(target_cycle_length) / 29.5
    kickback =  DEFAULT_LATER_PER_DAY / scale_factor
    base_time_minutes = SUNSET_HOUR * 60
    phase_sequence = []
    for phase_name in LUNAR_PHASES:
        count = scaled_phases[phase_name]
        phase_sequence.extend([phase_name] * count)

    results = []

    last_new_moon_day = None
    for day in range(new_total_days):
        this_phase = phase_sequence[day]
        if this_phase == "New Moon":
            moonrise_time = None
            moonset_time  = None
            last_new_moon_day = day
        else:
            # pre-New Moon
            if last_new_moon_day is None:
                offset_minutes = int(round(day * kickback))
                total_rise_minutes = base_time_minutes + offset_minutes
                rise_hour = (total_rise_minutes // 60) % 24
                rise_minute = total_rise_minutes % 60
                moonrise_time = datetime.time(rise_hour, rise_minute)
                
                moonset_time = datetime.time(6, 0)

            # post-New Moon 
            else:
                # Set rise at 18:00
                moonrise_time = datetime.time(18, 0)
                
                # For the moonset, shift forward by ~50 min each day after the last New Moon
                days_since_new_moon = day - last_new_moon_day
                offset_after_new_moon = int(round(days_since_new_moon * kickback))
                total_set_minutes = (SUNSET_HOUR * 60) + offset_after_new_moon
                set_hour = (total_set_minutes // 60) % 24
                set_minute = total_set_minutes % 60
                moonset_time = datetime.time(set_hour, set_minute)

        if moonrise_time and moonset_time:
            today = datetime.date.today()
            rise_dt = datetime.datetime.combine(today, moonrise_time)
            set_dt = datetime.datetime.combine(today, moonset_time)
            if set_dt < rise_dt:
                set_dt += datetime.timedelta(days=1)
                total_vis = (set_dt - rise_dt).total_seconds()
        else:
            total_vis = 0

        # Store the result for this day
        results.append({
            'day': day,
            'phase': this_phase,
            'moonrise_time': moonrise_time,
            'moonset_time': moonset_time,
            'total_visibility' : total_vis
        })
    return results


def calculate_current_altitude(schedule_entry, specific_time, cycle_start_date):
    """Calculate altitude with proper date context"""
    # Calculate the actual date for this lunar day
    entry_date = cycle_start_date + datetime.timedelta(days=schedule_entry['day'])
    
    # Create datetime objects with correct dates
    moonrise_dt = datetime.datetime.combine(entry_date, schedule_entry['moonrise_time'])
    moonset_dt = datetime.datetime.combine(entry_date, schedule_entry['moonset_time'])

    # Handle overnight visibility
    if moonset_dt <= moonrise_dt:
        moonset_dt += datetime.timedelta(days=1)

    if specific_time < moonrise_dt or specific_time > moonset_dt:
        return 0

    time_since_rise = (specific_time - moonrise_dt).total_seconds()
    total_vis = (moonset_dt - moonrise_dt).total_seconds()
    
    progress = time_since_rise / total_vis
    return np.sin(progress * np.pi) * 90

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
        #Convert datetime.time -> decimal hour, e.g.30 => 18.5
        return t.hour + t.minute / 60.0 if t else None

    for entry in schedule:
        day_label = entry['day'] + 1
        rise_hours.append(to_decimal_hour(entry['moonrise_time']))
        set_hours.append(to_decimal_hour(entry['moonset_time']))
        days.append(day_label)
    
    plt.figure(figsize=(10,5))
    plt.plot(days, rise_hours, marker='o', label='Moonrise', color='blue')
    plt.plot(days, set_hours, marker='o', label='Moonset',  color='red')
    
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
    phase_indices = []
    days = []
    for entry in schedule:
        day_label = entry['day'] + 1
        days.append(day_label)
        p_idx = LUNAR_PHASES.index(entry['phase']) if entry['phase'] in LUNAR_PHASES else -1
        phase_indices.append(p_idx)
    
    plt.figure(figsize=(10,4))
    plt.scatter(days, phase_indices, marker='o', color='green')
    
    
    plt.yticks(range(len(LUNAR_PHASES)), LUNAR_PHASES)
    plt.xlabel("Day in Lunar Cycle")
    plt.ylabel("Lunar Phase")
    plt.title("Lunar Phase by Day")
    plt.grid(True)
    plt.show()

import matplotlib.dates as mdates

def plot_hourly_altitude(schedule_entry, cycle_start_date):
    """Plot moon altitude throughout its visibility period with hourly markers."""
    if not schedule_entry['moonrise_time'] or not schedule_entry['moonset_time']:
        print("No moon visibility for this phase")
        return

    # Calculate the actual date for this lunar day
    entry_date = cycle_start_date + datetime.timedelta(days=schedule_entry['day'])
    
    # Create datetime objects with correct dates
    moonrise_dt = datetime.datetime.combine(entry_date, schedule_entry['moonrise_time'])
    moonset_dt = datetime.datetime.combine(entry_date, schedule_entry['moonset_time'])

    # Handle overnight visibility
    if moonset_dt <= moonrise_dt:
        moonset_dt += datetime.timedelta(days=1)

    # Generate time points at 15-minute intervals for smooth curve
    total_seconds = (moonset_dt - moonrise_dt).total_seconds()
    time_points = [moonrise_dt + datetime.timedelta(seconds=x) 
                   for x in np.arange(0, total_seconds, 15*60)]

    # Calculate altitudes for all time points
    altitudes = [calculate_current_altitude(schedule_entry, t, cycle_start_date) for t in time_points]

    # #Generate hourly markers
    # hour_markers = []
    # current = moonrise_dt
    # while current <= moonset_dt:
    #     hour_markers.append(current)
    #     current += datetime.timedelta(hours=1)

    # 30 minutes markers
    thirty_min_markers = []
    current = moonrise_dt
    while current <= moonset_dt:
        thirty_min_markers.append(current)
        current += datetime.timedelta(minutes=30)

    # Create plot
    #plt.figure(figsize=(12, 6))
    plt.figure(figsize=(14, 6))
    
    # Plot smooth curve
    plt.plot(time_points, altitudes, label='Altitude', color='navy')
    
    # # Plot hourly markers
    # for marker in hour_markers:
    #     alt = calculate_current_altitude(schedule_entry, marker, cycle_start_date)
    #     plt.scatter(marker, alt, color='red', zorder=5)
    #     plt.text(marker, alt+5, f"{alt:.1f}°\n{marker.strftime('%H:%M')}", 
    #             ha='center', fontsize=8)
        
    # Plot 30 minute markers
    for marker in thirty_min_markers:
        alt = calculate_current_altitude(schedule_entry, marker, cycle_start_date)
        plt.scatter(marker, alt, color='red', s=20, zorder=5)  # Smaller marker
        plt.text(marker, alt+5, f"{alt:.1f}°\n{marker.strftime('%H:%M')}", 
                ha='center', fontsize=7)

    # Format plot
    plt.title(f"Moon Altitude - Day {schedule_entry['day']} ({schedule_entry['phase']})")
    plt.xlabel("Time")
    plt.ylabel("Altitude (degrees)")
    plt.grid(True, alpha=0.3)
    
    # Use date locator and formatter
    hours = mdates.HourLocator()
    fmt = mdates.DateFormatter('%H:%M')
    
    plt.gca().xaxis.set_major_locator(hours)
    plt.gca().xaxis.set_major_formatter(fmt)
    plt.gcf().autofmt_xdate()
    
    plt.ylim(0, 100)
    plt.tight_layout()
    plt.show()


def print_terminal_altitude_chart(schedule_entry, cycle_start_date):
    if not schedule_entry['moonrise_time'] or not schedule_entry['moonset_time']:
        print("Moon not visible today")
        return

    # Calculate actual calendar dates
    entry_date = cycle_start_date + datetime.timedelta(days=schedule_entry['day'])
    rise_dt = datetime.datetime.combine(entry_date, schedule_entry['moonrise_time'])
    set_dt = datetime.datetime.combine(entry_date, schedule_entry['moonset_time'])

    if set_dt <= rise_dt:
        set_dt += datetime.timedelta(days=1)


    current = rise_dt
    # # Generate hourly points
    # hour_points = []
    # while current <= set_dt:
    #     hour_points.append(current)
    #     current += datetime.timedelta(hours=1)

    # Generate 30 minute points
    thirty_min_points = []
    while current <= set_dt:
        thirty_min_points.append(current)
        current += datetime.timedelta(minutes=30)

    # Header
    print(f"\nAltitude Timeline - Day {schedule_entry['day']} ({schedule_entry['phase']})")
    print(f"Visibility: {rise_dt.strftime('%Y-%m-%d %H:%M')} to {set_dt.strftime('%Y-%m-%d %H:%M')}")
    print("-" * 40)
    print(" Time    | Altitude")
    print("-" * 40)

    # # Print simple time-altitude pairs per hour
    # for time_point in hour_points:
    #     alt = calculate_current_altitude(schedule_entry, time_point, cycle_start_date)
        
    #     # Format time display
    #     if time_point.date() == rise_dt.date():
    #         time_str = time_point.strftime("%H:%M")
    #     else:
    #         time_str = time_point.strftime("%m-%d %H:%M")
            
    #     print(f" {time_str}  | {alt:5.1f}°")

    #  Print simple time-altitude pairs per 30 minutes
    for time_point in thirty_min_points:
        alt = calculate_current_altitude(schedule_entry, time_point, cycle_start_date)
        
        # Format time display
        if time_point.date() == rise_dt.date():
            time_str = time_point.strftime("%H:%M")
        else:
            time_str = time_point.strftime("%m-%d %H:%M")
            
        print(f" {time_str}  | {alt:5.1f}°")

    print("-" * 40)
if __name__ == "__main__":
    user_cycle_length = input(f"Enter lunar cycle length (default={DEFAULT_LUNAR_CYCLE_LENGTH}): ")
    moon_schedule = calculate_moonrise_times(int(user_cycle_length))
    cycle_start_date = datetime.datetime(2023, 10, 1)  # Set your actual start date
    print_moon_schedule(moon_schedule)
    plot_moon_schedule_times(moon_schedule)
    plot_moon_schedule_phases(moon_schedule)

    altitude_monitor_day = input(f"What day do you want to observe in your {user_cycle_length} lunar cycle?")
    plot_hourly_altitude(moon_schedule[int(altitude_monitor_day)], cycle_start_date)
    print_terminal_altitude_chart(moon_schedule[int(altitude_monitor_day)], cycle_start_date)
