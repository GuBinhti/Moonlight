import time
import math
import datetime
import threading
from queue import Queue

import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from rpi_hardware_pwm import HardwarePWM

SUNSET_HOUR  = 18
SUNRISE_HOUR = 6
DEFAULT_LUNAR_CYCLE_LENGTH = 28

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

DEFAULT_LATER_PER_DAY = (50 * 28) / 29


def set_servo_angle(angle):
    """
    Set servo to the given angle (0-180). Returns the duty cycle used.
    """
    pwm = HardwarePWM(pwm_channel=0, hz=50, chip=2)
    pwm.start(0)
    duty_cycle = 2.6 + 6.5 * (angle / 180.0)
    pwm.change_duty_cycle(duty_cycle)
    return duty_cycle

def get_num_phases(target_cycle_length):
    scalar = target_cycle_length / DEFAULT_LUNAR_CYCLE_LENGTH
    scaled_phases = {}

    for phase in LUNAR_PHASES:
        base_length = MoonPhaseLengthDays[phase]
        if scalar >= 1:
            if MoonPhaseChecker[phase] == 'x':
                new_length = math.floor(scalar * base_length)
            else:
                new_length = math.ceil(scalar * base_length)
        else:
            # scalar < 1
            if MoonPhaseChecker[phase] == 'x':
                new_length = math.ceil(scalar * base_length)
            else:
                new_length = math.floor(scalar * base_length)

        scaled_phases[phase] = new_length

    new_total = sum(scaled_phases.values())

    # Adjust if sum doesn't match target
    if new_total != target_cycle_length:
        if new_total > target_cycle_length:
            # Reduce days from 'o' phases
            for phase in MoonPhaseChecker:
                if MoonPhaseChecker[phase] == 'o' and scaled_phases[phase] > 0:
                    scaled_phases[phase] -= 1
                    new_total = sum(scaled_phases.values())
                    if new_total == target_cycle_length:
                        break
        else:
            # Add days to 'o' phases
            for phase in MoonPhaseChecker:
                if MoonPhaseChecker[phase] == 'o':
                    scaled_phases[phase] += 1
                    new_total = sum(scaled_phases.values())
                    if new_total == target_cycle_length:
                        break

    return scaled_phases, new_total

def calculate_moonrise_times(target_cycle_length):
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

        # Calculate total_visibility in seconds
        if moonrise_time and moonset_time:
            today = datetime.date.today()
            rise_dt = datetime.datetime.combine(today, moonrise_time)
            set_dt  = datetime.datetime.combine(today, moonset_time)
            if set_dt < rise_dt:
                set_dt += datetime.timedelta(days=1)
            total_vis = (set_dt - rise_dt).total_seconds()
        else:
            total_vis = 0

        phase_angle = set_moon_phase_angle(day, new_total_days)

        results.append({
            'day': day,
            'phase': this_phase,
            'moonrise_time': moonrise_time,
            'moonset_time':  moonset_time,
            'total_visibility': total_vis,
            'phase_angle': phase_angle
        })

    return results

def set_moon_phase_angle(day, cycle_length):

    # Make sure day is within [0, cycle_length], to avoid negative or overshoot
    if day < 0:
        day = 0
    if day > cycle_length:
        day = cycle_length
    y = (day + cycle_length / 2.0) % cycle_length
    return 180 * (1.0 - abs(1.0 - 2.0 * y / cycle_length))


def find_schedule_entry_for_time(schedule, cycle_start_date, sim_time):
    for entry in schedule:
        day_offset = entry['day']
        mr = entry['moonrise_time']
        ms = entry['moonset_time']
        if not mr or not ms:
            continue

        rise_dt = datetime.datetime.combine(cycle_start_date + datetime.timedelta(days=day_offset), mr)
        set_dt  = datetime.datetime.combine(cycle_start_date + datetime.timedelta(days=day_offset), ms)
        if set_dt <= rise_dt:
            set_dt += datetime.timedelta(days=1)

        if rise_dt <= sim_time < set_dt:
            return entry
    return None

def calculate_current_altitude(schedule_entry, specific_time, cycle_start_date):
    if schedule_entry['phase'] == 'New Moon':
        return -1

    mr = schedule_entry['moonrise_time']
    ms = schedule_entry['moonset_time']
    if not mr or not ms:
        return 0

    entry_date = cycle_start_date + datetime.timedelta(days=schedule_entry['day'])
    moonrise_dt = datetime.datetime.combine(entry_date, mr)
    moonset_dt  = datetime.datetime.combine(entry_date, ms)
    if moonset_dt <= moonrise_dt:
        moonset_dt += datetime.timedelta(days=1)

    if specific_time < moonrise_dt or specific_time > moonset_dt:
        return 0

    time_since_rise = (specific_time - moonrise_dt).total_seconds()
    total_vis = (moonset_dt - moonrise_dt).total_seconds()
    progress = time_since_rise / total_vis
    return 90.0 * (1.0 - np.cos(np.pi * progress))

def plot_moon_phase_angle(schedule):

    days = [entry['day'] for entry in schedule]
    angle  = [entry['phase_angle'] for entry in schedule]

    plt.figure(figsize=(8,4))
    plt.plot(days, angle, marker='o', color='blue')
    plt.title("Moon Phase Angle Over Lunar Month")
    plt.xlabel("Day in Lunar Month")
    plt.ylabel("Phase Angle")
    plt.ylim(0, 190.05)  # small padding above 1
    plt.grid(True, alpha=0.3)
    plt.show(block=False)

def plot_moon_schedule_times(schedule):
    def to_decimal_hour(t):
        return t.hour + t.minute / 60.0 if t else None

    days        = []
    rise_hours  = []
    set_hours   = []

    for entry in schedule:
        day_label = entry['day'] + 1
        days.append(day_label)
        mr = entry['moonrise_time']
        ms = entry['moonset_time']
        rise_hours.append(to_decimal_hour(mr))
        set_hours.append(to_decimal_hour(ms))

    plt.figure(figsize=(10,5))
    plt.plot(days, rise_hours, marker='o', label='Moonrise', color='blue')
    plt.plot(days, set_hours,  marker='o', label='Moonset',  color='red')
    plt.title('Moonrise and Moonset Times')
    plt.xlabel('Day in Lunar Cycle')
    plt.ylabel('Time of Day (Hours)')
    plt.xticks(range(1, max(days)+1))
    plt.yticks(range(0, 25, 2))
    plt.ylim(0, 24)
    plt.grid(True)
    plt.legend()
    plt.show(block=False)

def plot_moon_schedule_phases(schedule):
    days = []
    phase_indices = []

    for entry in schedule:
        day_label = entry['day'] + 1
        days.append(day_label)
        phase_name = entry['phase']
        if phase_name in LUNAR_PHASES:
            p_idx = LUNAR_PHASES.index(phase_name)
        else:
            p_idx = -1
        phase_indices.append(p_idx)

    plt.figure(figsize=(10,4))
    plt.scatter(days, phase_indices, marker='o', color='green')
    plt.yticks(range(len(LUNAR_PHASES)), LUNAR_PHASES)
    plt.xlabel("Day in Lunar Cycle")
    plt.ylabel("Lunar Phase")
    plt.title("Lunar Phase by Day")
    plt.grid(True)
    plt.show(block=False)

def plot_hourly_altitude(schedule_entry, cycle_start_date, marker_interval=60):
    mr = schedule_entry['moonrise_time']
    ms = schedule_entry['moonset_time']
    if not mr or not ms:
        print("No moon visibility for this day.")
        return

    entry_date = cycle_start_date + datetime.timedelta(days=schedule_entry['day'])
    moonrise_dt = datetime.datetime.combine(entry_date, mr)
    moonset_dt  = datetime.datetime.combine(entry_date, ms)
    if moonset_dt <= moonrise_dt:
        moonset_dt += datetime.timedelta(days=1)

    time_points = []
    altitudes   = []

    current = moonrise_dt
    while current <= moonset_dt:
        alt = calculate_current_altitude(schedule_entry, current, cycle_start_date)
        time_points.append(current)
        altitudes.append(alt)
        current += datetime.timedelta(minutes=marker_interval)

    plt.figure(figsize=(10,5))
    plt.plot(time_points, altitudes, color='purple')
    plt.scatter(time_points, altitudes, color='red', s=20)
    plt.title(f"Hourly Altitude (Day {schedule_entry['day']} - {schedule_entry['phase']})")
    plt.xlabel("Time")
    plt.ylabel("Altitude (degrees)")

    hours = mdates.HourLocator()
    fmt   = mdates.DateFormatter('%H:%M')
    plt.gca().xaxis.set_major_locator(hours)
    plt.gca().xaxis.set_major_formatter(fmt)
    plt.gcf().autofmt_xdate()

    plt.ylim(0, 200)
    plt.grid(True, alpha=0.3)
    plt.show(block=False)


def user_input_thread(command_queue):
    """
    Reads user input from stdin and pushes commands onto command_queue.
    This runs in parallel, so it doesn't block the main thread or the sim thread.
    """
    while True:
        cmd = input().strip().lower()
        if cmd == "pa":
            day_str = input("Enter a day index [0, N-1] to plot the altitude: ")
            command_queue.put(('pa', day_str))
        else:
            command_queue.put((cmd, None))

        if cmd == 'q':
            break

def simulation_loop(schedule, cycle_start_date, user_cycle_length, update_interval_minutes, speed_factor, day_length_in_real_seconds, stop_event):


    real_secs_per_sim_minute = day_length_in_real_seconds / (24 * 60)
    simulation_time = cycle_start_date
    cycle_end_time  = cycle_start_date + datetime.timedelta(days=user_cycle_length)

    print("\n[Simulation Thread] Started.")
    while not stop_event.is_set():  # loop until told to stop
        if simulation_time >= cycle_end_time:
            print("[Simulation Thread] Reached end of the simulation.")
            break

 
        current_entry = find_schedule_entry_for_time(schedule, cycle_start_date, simulation_time)
        if current_entry is not None:
            altitude_deg = calculate_current_altitude(current_entry, simulation_time, cycle_start_date)
            phase_angle = current_entry.get('phase_angle', 0.0)
            print(f"[Sim {simulation_time.strftime('%Y-%m-%d %H:%M')}] "
                  f"Day {current_entry['day']} - Phase: {current_entry['phase']} "
                  f"- Altitude: {altitude_deg:.1f}°"
                  f"- Phase Angle: {phase_angle:.2f}")
            dc = set_servo_angle(altitude_deg)
            print(f"Servo DC: {dc:.2f}% ")
        else:
            if SUNRISE_HOUR <= simulation_time.hour < SUNSET_HOUR:
                # Sun is up
                altitude_deg = 90
                print(f"[Sim {simulation_time.strftime('%Y-%m-%d %H:%M')}] "
                      f"Sun is out (alt={altitude_deg}°).")
                dc = set_servo_angle(altitude_deg)
                print(f"Servo DC: {dc:.2f}% ")
            else:
                # Moon not visible
                altitude_deg = 0
                print(f"[Sim {simulation_time.strftime('%Y-%m-%d %H:%M')}] "
                      "Moon not visible (alt=0).")
                dc = set_servo_angle(altitude_deg)
                print(f"Servo DC: {dc:.2f}% ")

        
        real_time_to_sleep = (update_interval_minutes * real_secs_per_sim_minute) / speed_factor
        time.sleep(real_time_to_sleep)

        simulation_time += datetime.timedelta(minutes=update_interval_minutes)

    print("[Simulation Thread] Exiting...")

def handle_command(cmd, arg, schedule, cycle_start_date, stop_event):
    if cmd == 'pt':
        print("Plotting Moonrise/Moonset times...")
        plot_moon_schedule_times(schedule)

    elif cmd == 'pp':
        print("Plotting Moon schedule phases...")
        plot_moon_schedule_phases(schedule)

    elif cmd =='pang':
        print("Plotting Moon Phase Angles...")
        plot_moon_phase_angle(schedule)

    elif cmd == 'pa':
        if arg and arg.isdigit():
            day_idx = int(arg)
            if 0 <= day_idx < len(schedule):
                print(f"Plotting altitude for day {day_idx}...")
                plot_hourly_altitude(schedule[day_idx], cycle_start_date, marker_interval=30)
            else:
                print("Invalid day index!")
        else:
            print("Please enter a valid integer for the day index.")

    elif cmd == 'q':
        print("[Main Thread] User requested quit.")
        stop_event.set()

    elif cmd == '':
        pass
    else:
        print(f"[Main Thread] Unknown command: {cmd}")



def main():
    # ssk user for cycle length
    raw_cycle_length = input(f"Enter lunar cycle length (default={DEFAULT_LUNAR_CYCLE_LENGTH}): ")
    user_cycle_length = int(raw_cycle_length) if raw_cycle_length else DEFAULT_LUNAR_CYCLE_LENGTH

    # compute schedule
    moon_schedule = calculate_moonrise_times(user_cycle_length)
    cycle_start_date = datetime.datetime.now()

    # speed factor for testing
    raw_speed = input("Enter a speed factor (default=1.0, e.g. 2.0=2x faster): ")
    speed_factor = float(raw_speed) if raw_speed else 1.0

    # real-time seconds for 24-hour sim-day
    raw_day_length = input("Enter real-time seconds for 24-hour sim-day (default=86400 = 24h): ")
    if raw_day_length.strip():
        day_length_in_real_seconds = float(raw_day_length)
    else:
        day_length_in_real_seconds = 86400.0

    # queue for commands, plus a user-input thread
    command_queue = Queue()
    input_thread = threading.Thread(target=user_input_thread, args=(command_queue,), daemon=True)
    input_thread.start()

    # stop_event to signal the simulation thread to quit
    stop_event = threading.Event()

    # start the simulation thread
    sim_thread = threading.Thread(
        target=simulation_loop,
        args=(
            moon_schedule,         # schedule
            cycle_start_date,      # start date
            user_cycle_length,     # cycle length in sim-days
            1,                     # update_interval_minutes (small steps)
            speed_factor,          # speed factor
            day_length_in_real_seconds,
            stop_event
        ),
        daemon=True
    )
    sim_thread.start()

    print("\n[Main Thread] Simulation started in background.")
    print("Commands:\n"
          "  pt  -> plot moonrise/moonset times\n"
          "  pp  -> plot moon schedule phases\n"
          "  pang  -> plot moon phase angles\n"
          "  pa  -> plot hourly altitude for a specific day\n"
          "  q   -> quit simulation\n"
          "Hit Enter to send commands.\n")

    # main loop does commands and do small sleeps
    while not stop_event.is_set():
        # do any pending commands
        while not command_queue.empty():
            cmd, arg = command_queue.get()
            handle_command(cmd, arg, moon_schedule, cycle_start_date, stop_event)

        
        plt.pause(0.01)


        time.sleep(0.1)

    # the user typed 'q' or simulation ended join the sim thread.
    sim_thread.join()
    print("[Main Thread] Simulation thread joined. Exiting.")


if __name__ == "__main__":
    main()
