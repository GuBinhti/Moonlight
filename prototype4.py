import os
import sys
import numpy as np
import time
import math
import datetime
import threading
from queue import Queue

#from rpi_hardware_pwm import HardwarePWM
import time

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.ion()

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


# def set_servo_angle(angle):
#     pwm = HardwarePWM(pwm_channel=0, hz=50, chip=2)
#     pwm.start(0)
#     duty_cycle = 2.6 + 6.5 * (angle / 180.0)
#     pwm.change_duty_cycle(duty_cycle)
#     return duty_cycle


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
            # If scalar < 1, do the opposite logic
            if MoonPhaseChecker[phase] == 'x':
                new_length = math.ceil(scalar * base_length)
            else:
                new_length = math.floor(scalar * base_length)

        scaled_phases[phase] = new_length

    new_total = sum(scaled_phases.values())

    # Adjust if sum doesn't match target
    if new_total != target_cycle_length:
        if new_total > target_cycle_length:
            # Reduce one day from 'o' phases until we match
            for phase in MoonPhaseChecker:
                if MoonPhaseChecker[phase] == 'o' and scaled_phases[phase] > 0:
                    scaled_phases[phase] -= 1
                    new_total = sum(scaled_phases.values())
                    if new_total == target_cycle_length:
                        break
        else:
            # Add one day to 'o' phases until we match
            for phase in MoonPhaseChecker:
                if MoonPhaseChecker[phase] == 'o':
                    scaled_phases[phase] += 1
                    new_total = sum(scaled_phases.values())
                    if new_total == target_cycle_length:
                        break

    return scaled_phases, new_total


def calculate_moonrise_times(target_cycle_length):
    """
    creates a list of dictionaries, one per day in the cycle,
    with keys: [day, phase, moonrise_time, moonset_time, total_visibility].
    """
    scaled_phases, new_total_days = get_num_phases(target_cycle_length)
    scale_factor = float(target_cycle_length) / 29.5
    kickback = DEFAULT_LATER_PER_DAY / scale_factor
    base_time_minutes = SUNSET_HOUR * 60

    # Build the day-by-day phase sequence
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

        # Calculate total visibility for reference
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


def find_schedule_entry_for_time(schedule, cycle_start_date, sim_time):
    # returns the schedule entry (day, phase, etc.) that covers sim_time
    for entry in schedule:
        day_offset = entry['day']
        mr = entry['moonrise_time']
        ms = entry['moonset_time']
        if not mr or not ms:
            continue

        # Actual datetime
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
        return 0  # no data => assume 0

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
    # simple sine wave 0 -> 90 deg
    return np.sin(progress * np.pi) * 90


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

    plt.title(f"Hourly Altitude (Day {schedule_entry['day']}, {schedule_entry['phase']})")
    plt.xlabel("Time")
    plt.ylabel("Altitude (degrees)")

    hours = mdates.HourLocator()
    fmt   = mdates.DateFormatter('%H:%M')
    plt.gca().xaxis.set_major_locator(hours)
    plt.gca().xaxis.set_major_formatter(fmt)
    plt.gcf().autofmt_xdate()

    plt.ylim(0, 100)
    plt.grid(True, alpha=0.3)


def user_input_thread(command_queue):
    while True:
        cmd = input().strip().lower()
        if cmd == "pa":
            day_str = input("Enter a day index [0, N-1] to plot the altitude: ")
            command_queue.put(('pa', day_str))
        else:
            command_queue.put((cmd, None))
        if cmd == 'q':
            break


def start_simulation(
    schedule,
    cycle_start_date,
    user_cycle_length,
    update_interval_minutes=1,
    speed_factor=1.0,
    day_length_in_real_seconds=86400
):
    """
    :param schedule:                The precomputed lunar schedule
    :param cycle_start_date:        Datetime for day 0 of the cycle
    :param user_cycle_length:       How many sim-days the cycle runs
    :param update_interval_minutes: How many sim-minutes we jump each loop
    :param speed_factor:            Additional factor to speed up or slow down
    :param day_length_in_real_seconds: how many real seconds = 24 sim hours
    """

    # Real seconds per simulated minute (baseline, i.e. speed_factor=1)
    # 24 sim-hours = 24*60 sim-minutes
    real_secs_per_sim_minute = day_length_in_real_seconds / (24 * 60)

    simulation_time = cycle_start_date
    cycle_end_time  = cycle_start_date + datetime.timedelta(days=user_cycle_length)

    # Create a queue to receive commands from the user
    command_queue = Queue()
    t = threading.Thread(target=user_input_thread, args=(command_queue,), daemon=True)
    t.start()

    print("\n--- Starting Simulation (threaded) ---")
    print(f"Simulation Start (sim time): {simulation_time}")
    print(f"Simulation End   (sim time): {cycle_end_time}")
    print(f"Speed factor     : {speed_factor}x")
    print(f"One sim-day (24h) = {day_length_in_real_seconds} real seconds.")
    print(f"So 1 sim-minute = {real_secs_per_sim_minute:.6f} real seconds (x1).")
    print("Type commands any time:\n"
          "  pt  -> plot moonrise/moonset times\n"
          "  pp  -> plot moon phases\n"
          "  pa  -> plot hourly altitude for a specific day\n"
          "  q   -> quit simulation\n"
          "Hit Enter to post a command.\n")

    try:
        while True:
            # 1) Check if we're past the end of the cycle
            if simulation_time >= cycle_end_time:
                print("Reached the end of the simulation!")
                break

            # 2) Simulation logic
            current_entry = find_schedule_entry_for_time(schedule, cycle_start_date, simulation_time)
            if current_entry is not None:
                altitude_deg = calculate_current_altitude(current_entry, simulation_time, cycle_start_date)
                print(
                    f"[Sim {simulation_time.strftime('%Y-%m-%d %H:%M')}] "
                    f"Day {current_entry['day']} - Phase: {current_entry['phase']} "
                    f"- Altitude: {altitude_deg:.1f}°"
                )
                # SERVO CODE
                # dc = set_servo_angle(altitude_deg)
                # print(f"Servo DC: {dc:.2f}% ")
            else:
                # Possibly day time or no moon visible
                if 6 <= simulation_time.hour < 18:
                    # Sun is up
                    altitude_deg = 90
                    print(
                        f"[Sim {simulation_time.strftime('%Y-%m-%d %H:%M')}] "
                        f"Sun is out (altitude ~ {altitude_deg}°)."
                    )
                    # dc = set_servo_angle(altitude_deg)
                    # print(f"Servo DC: {dc:.2f}% ")
                else:
                    # Moon is not visible
                    altitude_deg = 0
                    print(
                        f"[Sim {simulation_time.strftime('%Y-%m-%d %H:%M')}] "
                        "Moon is not visible (altitude = 0)."
                    )
                    # dc = set_servo_angle(altitude_deg)
                    # print(f"Servo DC: {dc:.2f}% ")

            # 3) Check for user commands in the queue
            while not command_queue.empty():
                cmd, arg = command_queue.get()
                if cmd == 'pt':
                    print("Plotting Moonrise/Moonset times...")
                    plot_moon_schedule_times(schedule)

                elif cmd == 'pp':
                    print("Plotting Moon schedule phases...")
                    plot_moon_schedule_phases(schedule)

                elif cmd == 'pa':
                    day_str = arg
                    if day_str.isdigit():
                        day_idx = int(day_str)
                        if 0 <= day_idx < len(schedule):
                            print(f"Plotting altitude for day {day_idx}...")
                            plot_hourly_altitude(schedule[day_idx], cycle_start_date, marker_interval=30)
                        else:
                            print("Invalid day index!")
                    else:
                        print("Please enter an integer.")

                elif cmd == 'q':
                    print("User requested to quit simulation.")
                    return

                elif cmd == '':
                    pass
                else:
                    print(f"Unknown command: {cmd}")

            # If update_interval_minutes=1, we want to skip 1 sim-min in time
            # and sleep real_secs_per_sim_minute / speed_factor in real time.
            # If update_interval_minutes=10, multiply that times the baseline.
            real_time_to_sleep = (update_interval_minutes * real_secs_per_sim_minute) / speed_factor
            time.sleep(real_time_to_sleep)

            # Advance the simulation clock by the chosen sim-minutes
            # (we no longer multiply by speed_factor here!)

            simulation_time += datetime.timedelta(minutes=update_interval_minutes)

            # Keep Matplotlib windows responsive
            plt.pause(0.001)

    except KeyboardInterrupt:
        print("\nSimulation manually stopped by user.")
    finally:
        print("Simulation finished or interrupted.")


if __name__ == "__main__":
    raw_cycle_length = input(f"Enter lunar cycle length (default={DEFAULT_LUNAR_CYCLE_LENGTH}): ")
    user_cycle_length = int(raw_cycle_length) if raw_cycle_length else DEFAULT_LUNAR_CYCLE_LENGTH

    # Creates the full schedule for the lunar schedule
    moon_schedule = calculate_moonrise_times(user_cycle_length)

    cycle_start_date = datetime.datetime.now()

    raw_speed = input("Enter a speed factor (default=1.0, e.g. 2.0=2x faster): ")
    speed_factor = float(raw_speed) if raw_speed else 1.0

    ### ask for a day length in real-time seconds
    raw_day_length = input("Enter real-time seconds for 24-hour sim-day (default=86400 = 24h): ")
    if raw_day_length.strip():
        day_length_in_real_seconds = float(raw_day_length)
    else:
        day_length_in_real_seconds = 86400.0  # 24 hours in seconds

    start_simulation(
        schedule=moon_schedule,
        cycle_start_date=cycle_start_date,
        user_cycle_length=user_cycle_length,
        update_interval_minutes=1,  # e.g. small steps for demonstration
        speed_factor=speed_factor,
        day_length_in_real_seconds=day_length_in_real_seconds
    )

    print("Main program complete.")
