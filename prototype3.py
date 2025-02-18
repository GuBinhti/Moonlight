import os
import sys
import numpy as np
import logging
import time
import math
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
# import RPi.GPIO as GPIO
# from PIL import Image, ImageDraw, ImageFont
# from waveshare_OLED import OLED_1in27_rgb
# picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
# libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
# if os.path.exists(libdir):
#    sys.path.append(libdir)
logging.basicConfig(level=logging.DEBUG)

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

MoonPhaseLengthDays = {
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

DEFAULT_LUNAR_CYCLE_LENGTH = 28
DEFAULT_LATER_PER_DAY = (50 * 28) / 29  # ~48-50 minutes
SUNSET_HOUR  = 18
SUNRISE_HOUR = 6

def get_num_phases(target_cycle_length):

    scalar = target_cycle_length / DEFAULT_LUNAR_CYCLE_LENGTH
    scaled_phases = {}
    for phase in LUNAR_PHASES:
        if scalar >= 1:
            if MoonPhaseChecker[phase] == 'x':
                new_length = math.floor(scalar * MoonPhaseLengthDays[phase])
            else:
                new_length = math.ceil(scalar * MoonPhaseLengthDays[phase])
        else:
            if MoonPhaseChecker[phase] == 'x':
                new_length = math.ceil(scalar * MoonPhaseLengthDays[phase])
            else:
                new_length = math.floor(scalar * MoonPhaseLengthDays[phase])
        scaled_phases[phase] = new_length
    new_total = sum(scaled_phases.values())

    # Adjust if sum doesn't match target
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

    return scaled_phases, new_total

def calculate_moonrise_times(target_cycle_length):

    # construct a schedule (list of dicts) for each day in the cycle, has moonrise/moonset times based on  scaling from defaults

    scaled_phases, new_total_days = get_num_phases(target_cycle_length)
    scale_factor = float(target_cycle_length) / 29.5
    kickback = DEFAULT_LATER_PER_DAY / scale_factor
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
            if last_new_moon_day is None:
                # Pre-New Moon
                offset_minutes = int(round(day * kickback))
                total_rise_minutes = base_time_minutes + offset_minutes
                rise_hour   = (total_rise_minutes // 60) % 24
                rise_minute = total_rise_minutes % 60
                moonrise_time = datetime.time(rise_hour, rise_minute)
                moonset_time  = datetime.time(6, 0)
            else:
                # Post-New Moon
                moonrise_time = datetime.time(18, 0)
                days_since_new_moon = day - last_new_moon_day
                offset_after_new_moon = int(round(days_since_new_moon * kickback))
                total_set_minutes = (SUNSET_HOUR * 60) + offset_after_new_moon
                set_hour   = (total_set_minutes // 60) % 24
                set_minute = total_set_minutes % 60
                moonset_time = datetime.time(set_hour, set_minute)

        if moonrise_time and moonset_time:
            today = datetime.date.today()
            rise_dt = datetime.datetime.combine(today, moonrise_time)
            set_dt  = datetime.datetime.combine(today, moonset_time)
            if set_dt < rise_dt:
                set_dt += datetime.timedelta(days=1)
                total_vis = (set_dt - rise_dt).total_seconds()
        else:
            total_vis = 0

        results.append({
            'day': day,
            'phase': this_phase,
            'moonrise_time': moonrise_time,
            'moonset_time':  moonset_time,
            'total_visibility': total_vis
        })
    return results

def calculate_current_altitude(schedule_entry, specific_time, cycle_start_date):
    """
    Calculate altitude for a given schedule_entry at a specific_time,
    taking actual date context into account (handles day offset).
    """
    if schedule_entry['phase'] == 'New Moon':
        return -1
    
    if not schedule_entry['moonrise_time'] or not schedule_entry['moonset_time']:
        # By default, if there's no rise or set, let's say it's "always overhead" 
        return 90

    entry_date = cycle_start_date + datetime.timedelta(days=schedule_entry['day'])
    moonrise_dt = datetime.datetime.combine(entry_date, schedule_entry['moonrise_time'])
    moonset_dt  = datetime.datetime.combine(entry_date, schedule_entry['moonset_time'])

    # Handle overnight visibility
    if moonset_dt <= moonrise_dt:
        moonset_dt += datetime.timedelta(days=1)

    # If outside visible time range, altitude = 90 (or 0, if you prefer "below horizon").
    if specific_time < moonrise_dt or specific_time > moonset_dt:
        return 90

    time_since_rise = (specific_time - moonrise_dt).total_seconds()
    total_vis = (moonset_dt - moonrise_dt).total_seconds()
    
    progress = time_since_rise / total_vis
    # Simple sine curve from 0 to 90 degrees
    return np.sin(progress * np.pi) * 90

def print_moon_schedule(schedule):
    
    print(f"{'Day':>3} | {'Phase':<16} | {'Moonrise':>8} | {'Moonset':>8}")
    print("-" * 55)
    for entry in schedule:
        day   = entry['day']
        phase = entry['phase']
        mr_time = entry['moonrise_time']
        ms_time = entry['moonset_time']
        
        mr_str = mr_time.strftime('%H:%M') if mr_time else "None"
        ms_str = ms_time.strftime('%H:%M') if ms_time else "None"
        
        print(f"{day:3d} | {phase:<16} | {mr_str:>8} | {ms_str:>8}")

def plot_moon_schedule_times(schedule):
    days = []
    rise_hours = []
    set_hours  = []

    def to_decimal_hour(t):
        return t.hour + t.minute / 60.0 if t else None

    for entry in schedule:
        day_label = entry['day'] + 1
        rise_hours.append(to_decimal_hour(entry['moonrise_time']))
        set_hours.append(to_decimal_hour(entry['moonset_time']))
        days.append(day_label)
    
    plt.figure(figsize=(10,5))
    plt.plot(days, rise_hours, marker='o', label='Moonrise', color='blue')
    plt.plot(days, set_hours,  marker='o', label='Moonset',  color='red')
    
    plt.title('Moonrise and Moonset Times')
    plt.xlabel('Day in Lunar Cycle')
    plt.ylabel('Time of Day (Hours)')
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

def plot_hourly_altitude(schedule_entry, cycle_start_date, marker_interval=30, smooth_interval=15):
    if not schedule_entry['moonrise_time'] or not schedule_entry['moonset_time']:
        print("No moon visibility for this phase")
        return

    entry_date = cycle_start_date + datetime.timedelta(days=schedule_entry['day'])
    moonrise_dt = datetime.datetime.combine(entry_date, schedule_entry['moonrise_time'])
    moonset_dt  = datetime.datetime.combine(entry_date, schedule_entry['moonset_time'])

    if moonset_dt <= moonrise_dt:
        moonset_dt += datetime.timedelta(days=1)

    total_seconds = (moonset_dt - moonrise_dt).total_seconds()
    time_points = [
        moonrise_dt + datetime.timedelta(seconds=x) 
        for x in np.arange(0, total_seconds, smooth_interval * 60)
    ]
    altitudes = [
        calculate_current_altitude(schedule_entry, t, cycle_start_date) 
        for t in time_points
    ]

    marker_points = []
    current = moonrise_dt
    while current <= moonset_dt:
        marker_points.append(current)
        current += datetime.timedelta(minutes=marker_interval)

    plt.figure(figsize=(14, 6))
    plt.plot(time_points, altitudes, label='Altitude', color='navy')

    for marker in marker_points:
        alt = calculate_current_altitude(schedule_entry, marker, cycle_start_date)
        plt.scatter(marker, alt, color='red', s=20, zorder=5)
        plt.text(marker, alt + 5, f"{alt:.1f}°\n{marker.strftime('%H:%M')}", 
                 ha='center', fontsize=7)

    plt.title(f"Moon Altitude - Day {schedule_entry['day']} ({schedule_entry['phase']})")
    plt.xlabel("Time")
    plt.ylabel("Altitude (degrees)")
    plt.grid(True, alpha=0.3)
    
    hours = mdates.HourLocator()
    fmt   = mdates.DateFormatter('%H:%M')
    
    plt.gca().xaxis.set_major_locator(hours)
    plt.gca().xaxis.set_major_formatter(fmt)
    plt.gcf().autofmt_xdate()
    
    plt.ylim(0, 100)
    plt.tight_layout()
    plt.show()

def print_terminal_altitude_chart(schedule_entry, cycle_start_date, marker_interval=30):
    if not schedule_entry['moonrise_time'] or not schedule_entry['moonset_time']:
        print("Moon not visible today")
        return

    entry_date = cycle_start_date + datetime.timedelta(days=schedule_entry['day'])
    rise_dt = datetime.datetime.combine(entry_date, schedule_entry['moonrise_time'])
    set_dt  = datetime.datetime.combine(entry_date, schedule_entry['moonset_time'])

    if set_dt <= rise_dt:
        set_dt += datetime.timedelta(days=1)

    marker_points = []
    current = rise_dt
    while current <= set_dt:
        marker_points.append(current)
        current += datetime.timedelta(minutes=marker_interval)

    print(f"\nAltitude Timeline - Day {schedule_entry['day']} ({schedule_entry['phase']})")
    print(f"Visibility: {rise_dt.strftime('%Y-%m-%d %H:%M')} to {set_dt.strftime('%Y-%m-%d %H:%M')}")
    print("-" * 40)
    print(" Time    | Altitude")
    print("-" * 40)

    for time_point in marker_points:
        alt = calculate_current_altitude(schedule_entry, time_point, cycle_start_date)
        if time_point.date() == rise_dt.date():
            time_str = time_point.strftime("%H:%M")
        else:
            time_str = time_point.strftime("%m-%d %H:%M")
        print(f" {time_str}  | {alt:5.1f}°")

    print("-" * 40)


def find_schedule_entry_for_time(schedule, cycle_start_date, sim_time):

    for entry in schedule:
        day_offset = entry['day']
        rise_time = entry['moonrise_time']
        set_time  = entry['moonset_time']

        # If no rise or set time, skip this entry
        if not rise_time or not set_time:
            continue

        # Calculate the actual date+time for rise and set
        rise_dt = datetime.datetime.combine(cycle_start_date + datetime.timedelta(days=day_offset), rise_time)
        set_dt  = datetime.datetime.combine(cycle_start_date + datetime.timedelta(days=day_offset), set_time)

        # Handle the scenario where set_dt is after midnight
        if set_dt <= rise_dt:
            set_dt += datetime.timedelta(days=1)

        # Check if sim_time is within [rise_dt, set_dt)
        if rise_dt <= sim_time < set_dt:
            return entry

    # If we couldn't match any entry, return None
    return None


def start_simulation(schedule, cycle_start_date, user_cycle_length, update_interval_minutes=5, speed_factor=1.0):
    simulation_time = cycle_start_date
    cycle_end_time = cycle_start_date + datetime.timedelta(days=user_cycle_length)

    print("\n--- Starting Simulation with Speed Factor =", speed_factor, "---")
    print(f"Simulation Start (sim time): {simulation_time}")
    print(f"Simulation End   (sim time): {cycle_end_time}\n")
    print(f"Real-time update interval: {update_interval_minutes} minute(s).")
    print("Press Ctrl + C to cancel.\n")

    try:
        while True:
            if simulation_time >= cycle_end_time:
                print(f"Reached the end of the {user_cycle_length}-day simulation!")
                break

            current_entry = find_schedule_entry_for_time(schedule, cycle_start_date, simulation_time)
            
            if current_entry is not None:
                # We are within a lunar schedule entry (the Moon is up)
                altitude_deg = calculate_current_altitude(
                    current_entry,
                    simulation_time,
                    cycle_start_date
                )
                print(
                    f"[Real {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                    f"Sim {simulation_time.strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"Day {current_entry['day']} - Phase: {current_entry['phase']} "
                    f"- Altitude: {altitude_deg:.1f}°"
                )
            else:
                # Check if it's daytime (06:00–18:00). If yes, sun is out (altitude=90)
                if 6 <= simulation_time.hour < 18:
                    altitude_deg = 90
                    print(
                        f"[Real {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"Sim {simulation_time.strftime('%Y-%m-%d %H:%M:%S')}] "
                        f"The sun is out (altitude = {altitude_deg:.1f}°)."
                    )
                else:
                    # Otherwise, altitude = 0
                    altitude_deg = 0
                    print(
                        f"[Real {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                        f"Sim {simulation_time.strftime('%Y-%m-%d %H:%M:%S')}] "
                        "The Moon is not visible (altitude = 0)."
                    )

            # Sleep in real-time for the chosen interval
            time.sleep(update_interval_minutes * 60)

            # Advance simulation time by update_interval_minutes * speed_factor
            simulation_time += datetime.timedelta(minutes=update_interval_minutes * speed_factor)

    except KeyboardInterrupt:
        print("\nSimulation manually stopped by user.")
    finally:
        print("Simulation finished or interrupted.")


# --- MAIN / EXAMPLE USAGE ---
if __name__ == "__main__":
    raw_cycle_length = input(f"Enter lunar cycle length (default={DEFAULT_LUNAR_CYCLE_LENGTH}): ")
    user_cycle_length = int(raw_cycle_length) if raw_cycle_length else DEFAULT_LUNAR_CYCLE_LENGTH

    moon_schedule = calculate_moonrise_times(user_cycle_length)

    # print_moon_schedule(moon_schedule)
    # plot_moon_schedule_times(moon_schedule)
    # plot_moon_schedule_phases(moon_schedule)

    # altitude_monitor_day = input(f"What day do you want to observe in your {user_cycle_length}-day lunar cycle? ")
    # altitude_monitor_day = int(altitude_monitor_day)
    # plot_hourly_altitude(moon_schedule[altitude_monitor_day], cycle_start_date, marker_interval=30)
    # print_terminal_altitude_chart(moon_schedule[altitude_monitor_day], cycle_start_date, marker_interval=30)

    cycle_start_date = datetime.datetime.today()  # Start "today"

    raw_speed = input("Enter a speed factor for the simulation (default=1.0, e.g. 2.0=2x faster): ")
    speed_factor = float(raw_speed) if raw_speed else 1.0

    start_simulation(
        schedule=moon_schedule,
        cycle_start_date=cycle_start_date,
        user_cycle_length=user_cycle_length,
        update_interval_minutes=0.01,  # for quick testing
        speed_factor=speed_factor
    )
