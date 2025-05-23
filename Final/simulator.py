import os
import sys
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)
import time
import math
import datetime
import threading
from queue import Queue
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from waveshare_OLED import OLED_1in27_rgb
from PIL import Image, ImageDraw, ImageFont
from rpi_hardware_pwm import HardwarePWM

current_servo_angle = 0
# want the feeder to start at 25 degrees
current_feeder_angle = 25

SUNSET_HOUR  = 18
SUNRISE_HOUR = 6
DEFAULT_LUNAR_CYCLE_LENGTH = 28
SUN_COLOR = '#FFFFFF'
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
    global current_servo_angle
    pwm = HardwarePWM(pwm_channel=1, hz=50)
    pwm.start(0)
    duty_cycle = 2.6 + 6.5 * (angle / 180.0)
    pwm.change_duty_cycle(duty_cycle)
    current_servo_angle = angle

    return duty_cycle

def move_arm(start_angle, end_angle, delay= 0.05, step=1):
    #start_angle = 180
    #end_angle = 90
    if start_angle < end_angle:
        angle_range = range(int(start_angle), int(end_angle) + 1, int(step))
    else:
        angle_range = range(int(start_angle), int(end_angle) - 1, -int(step))
    for angle in angle_range:
        set_servo_angle(angle)
        time.sleep(delay) 
        # print(f"Moving arm to {angle}°")
        #print(f"This is the delay: {delay}")

def move_arm_zero(start_angle, end_angle, delay=0.05, step=1):
    """
    Move the arm from start_angle to end_angle one step at a time.
    No reliance on compare_alt; just a straight sweep.
    """
    # pick the right direction
    if start_angle < end_angle:
        angle_range = range(int(start_angle), int(end_angle) + 1, int(step))
    else:
        angle_range = range(int(start_angle), int(end_angle) - 1, -int(step))

    for angle in angle_range:
        set_servo_angle(angle)
        time.sleep(delay)
        # print(f"Moving arm to {angle}°")


def set_feeder_angle(feeder_angle):
    global current_feeder_angle
    #pwm_channel = 1 = pin 13? double check in config.txt file
    pwm = HardwarePWM(pwm_channel=0, hz=50)
    pwm.start(0)
    duty_cycle = 2.6 + 10.5 * (feeder_angle / 180.0)
    pwm.change_duty_cycle(duty_cycle)
    current_feeder_angle = feeder_angle

    return duty_cycle

def move_feeder(start_angle, end_angle, stop_event = None, delay=0.05, step=1):
    if start_angle < end_angle:
        angle_range = range(int(start_angle), int(end_angle) + 1, int(step))
    else:
        angle_range = range(int(start_angle), int(end_angle) - 1, -int(step))
    
    for angle in angle_range:
        # if stop_event.is_set():
        #     return
        # else:
            set_feeder_angle(angle)
            '''thread this sleep bc it stops the entire sim'''
            time.sleep(delay) 
    

def drop_feeder(): #primary
    move_feeder(current_feeder_angle, 120, step=1, delay=0.05)

def reset_feeder():
    move_feeder(current_feeder_angle, 25, delay=0.05, step=1)

def return_feeder():
    move_feeder(120, 25, delay = 0.05, step =1)

def shake_feeder(): # primary
    # Shake the feeder by moving it back and forth
    for _ in range(1):
        move_feeder(current_feeder_angle, 80, delay=0.05, step=5)
        move_feeder(current_feeder_angle, 120, delay=0.05, step=5)
    reset_feeder()

def drop_alarm():
    drop_feeder()
    print(f"Feeder Dropped")
    #print(feeder_thread)

def feeding_alarm():
    print(f"Feeder Reset")
    #shake_feeder()
    move_feeder(current_feeder_angle, 25, delay=0.05, step=1)

    #return_feeder()
    

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


def calculate_moonrise_times(target_cycle_length, start_phase='Full Moon'):
    scaled_phases, new_total_days = get_num_phases(target_cycle_length)

    orig_seq = []
    for phase in LUNAR_PHASES:
        orig_seq.extend([phase] * scaled_phases[phase])
    assert len(orig_seq) == new_total_days

    if start_phase not in LUNAR_PHASES:
        raise ValueError(f"Invalid start_phase: {start_phase!r}")
    idx0     = LUNAR_PHASES.index(start_phase)
    idx0_mod = sum(scaled_phases[p] for p in LUNAR_PHASES[:idx0])

    phase_sequence = orig_seq[idx0_mod:] + orig_seq[:idx0_mod]

    scale_factor      = float(target_cycle_length) / 29.5
    kickback          = DEFAULT_LATER_PER_DAY / scale_factor
    base_time_minutes = SUNSET_HOUR * 60

    results = []
    last_new_moon_day = None

    for d in range(new_total_days):
        this_phase = phase_sequence[d]

        if this_phase == "New Moon":
            moonrise_time = None
            moonset_time  = None
            last_new_moon_day = d
        else:
            if last_new_moon_day is None:
                # Pre-New Moon
                offset_minutes     = int(round(d * kickback))
                total_rise_minutes = base_time_minutes + offset_minutes
                rise_h, rise_m     = divmod(total_rise_minutes, 60)
                moonrise_time      = datetime.time(rise_h % 24, rise_m)
                moonset_time       = datetime.time(SUNRISE_HOUR, 0)
            else:
                # Post-New Moon
                moonrise_time       = datetime.time(SUNSET_HOUR, 0)
                days_since_new      = d - last_new_moon_day
                offset_after_new    = int(round(days_since_new * kickback))
                total_set_minutes   = (SUNSET_HOUR * 60) + offset_after_new
                set_h, set_m        = divmod(total_set_minutes, 60)
                moonset_time        = datetime.time(set_h % 24, set_m)

        # total visibility
        if moonrise_time and moonset_time:
            today   = datetime.date.today()
            rise_dt = datetime.datetime.combine(today, moonrise_time)
            set_dt  = datetime.datetime.combine(today, moonset_time)
            if set_dt < rise_dt:
                set_dt += datetime.timedelta(days=1)
            total_vis = (set_dt - rise_dt).total_seconds()
        else:
            total_vis = 0

        # 6) compute the *shifted* phase angle by pointing back into the original cycle
        orig_day_idx = (d + idx0_mod) % new_total_days
        phase_angle  = set_moon_phase_angle(orig_day_idx, new_total_days)

        results.append({
            'day':              d + 1,    # now 1…N
            'phase':            this_phase,
            'moonrise_time':    moonrise_time,
            'moonset_time':     moonset_time,
            'total_visibility': total_vis,
            'phase_angle':      phase_angle
        })

    return results

def compute_cycle_start_date(start_time_str: str) -> datetime.datetime:
    """Return a datetime that matches the user-supplied HH:MM today."""
    now = datetime.datetime.now()
    h, m = map(int, start_time_str.split(':'))
    return now.replace(hour=h, minute=m, second=0, microsecond=0)


def set_moon_phase_angle(day, cycle_length):
    if day < 0:
        day = 0
    if day > cycle_length:
        day = cycle_length
    y = (day + cycle_length / 2.0) % cycle_length
    return 180 * (1.0 - abs(1.0 - 2.0 * y / cycle_length))

def find_schedule_entry_for_time(schedule, cycle_start_date, sim_time):
    start_dt      = cycle_start_date
    today         = start_dt.date()
    first_sunrise = datetime.datetime.combine(today, datetime.time(SUNRISE_HOUR, 0))
    if start_dt >= first_sunrise:
        first_sunrise += datetime.timedelta(days=1)

    if sim_time < first_sunrise:
        lunar_day = 1
    else:
        secs_since = (sim_time - first_sunrise).total_seconds()
        full_days  = int(secs_since // (24*3600))
        lunar_day  = full_days + 2

    lunar_day = max(1, min(lunar_day, len(schedule)))

    return schedule[lunar_day - 1]

def find_first_day_with_phase(schedule, target_phase):
    """
    Return the zero-based index of the FIRST day in schedule whose 'phase' matches target_phase.
    If none found, returns 0.
    """
    for idx, entry in enumerate(schedule):
        if entry['phase'] == target_phase:
            return idx
    return 0


def calculate_current_altitude(schedule_entry, specific_time, cycle_start_date):
    """Return altitude in degrees (0-90). 0 means below horizon."""
    if schedule_entry['phase'] == 'New Moon':
        return -1                           # force “not visible”

    mr, ms = schedule_entry['moonrise_time'], schedule_entry['moonset_time']
    if not mr or not ms:
        return 0

    entry_date = cycle_start_date.date() + datetime.timedelta(days=schedule_entry['day'])
    moonrise_dt = datetime.datetime.combine(entry_date, mr)
    moonset_dt  = datetime.datetime.combine(entry_date, ms)
    if moonset_dt <= moonrise_dt:           # crosses midnight
        moonset_dt += datetime.timedelta(days=1)


    # If we’re before the rise time, push the clock forward by 24 h so it falls inside the window.
    if specific_time < moonrise_dt:
        specific_time += datetime.timedelta(days=1)

    if specific_time > moonset_dt:
        return 0                            # Moon already set

    total_vis = (moonset_dt - moonrise_dt).total_seconds()
    time_since_rise = (specific_time - moonrise_dt).total_seconds()
    progress = time_since_rise / total_vis
    return 90.0 * (1.0 - np.cos(np.pi * progress))

def rotate_phases(start_phase):
    idx0 = LUNAR_PHASES.index(start_phase)
    return LUNAR_PHASES[idx0:] + LUNAR_PHASES[:idx0]

def plot_moon_phase_angle(schedule):

    # extract days (1…N) and angles
    days   = [entry['day']         for entry in schedule]
    angles = [entry['phase_angle'] for entry in schedule]

    # figure out what phase you began on
    start_phase = schedule[0]['phase']

    plt.figure(figsize=(8,4))
    plt.plot(days, angles, marker='o')
    plt.title(f"Moon Phase Angle Over Lunar Cycle (start: {start_phase})")
    plt.xlabel("Day in Lunar Cycle")
    plt.ylabel("Phase Angle (°)")
    plt.ylim(0, 190.05)   
    plt.xticks(days)
    plt.grid(True, alpha=0.3)
    plt.show(block=False)


def plot_moon_schedule_times(schedule):
    """
    Plot moonrise (blue) and moonset (red) times for each cycle-day,
    using entry['day'] (1…N) as the x-axis.
    """
    def to_decimal_hour(t):
        return t.hour + t.minute / 60.0 if t else None

    days       = []
    rise_hours = []
    set_hours  = []

    for entry in schedule:
        day_label = entry['day'] - 1   # already 1…N
        days.append(day_label)
        rise_hours.append(to_decimal_hour(entry['moonrise_time']))
        set_hours.append(to_decimal_hour(entry['moonset_time']))

    plt.figure(figsize=(10,7))
    plt.plot(days, rise_hours, marker='o', label='Moonrise')
    plt.plot(days, set_hours,  marker='o', label='Moonset')
    plt.title('Moonrise and Moonset Times')
    plt.xlabel('Day in Lunar Cycle')
    plt.ylabel('Time of Day (Hours)')
    plt.xticks(range(1, len(schedule)+1))
    plt.yticks(range(0, 28, 2))
    plt.ylim(0, 28)
    plt.grid(True)
    plt.legend()
    plt.show(block=False)


def plot_moon_schedule_phases(schedule):
    start_phase = schedule[0]['phase']
    rotated     = rotate_phases(start_phase)

    days          = []
    phase_indices = []

    for entry in schedule:
        days.append(entry['day'])  # 1…N
        # find this day's phase index in the rotated list
        phase_indices.append(rotated.index(entry['phase']))

    plt.figure(figsize=(10,4))
    plt.scatter(days, phase_indices, marker='o')
    plt.yticks(range(len(rotated)), rotated)
    plt.xlabel("Day in Lunar Cycle")
    plt.ylabel("Lunar Phase")
    plt.title("Lunar Phase by Day")
    plt.grid(True, alpha=0.3)
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

def prompt_phase_with_skip(prompt, current_value):
    while True:
        print("Available phases:")
        for i, phase in enumerate(LUNAR_PHASES):
            print(f"  {i}: {phase}")
        val = input(f"{prompt} (current={current_value}, enter index or Enter to skip): ").strip()
        if not val:
            return None
        if val.isdigit():
            idx = int(val)
            if 0 <= idx < len(LUNAR_PHASES):
                return LUNAR_PHASES[idx]
        print("Invalid selection. Please enter a valid number or press Enter to skip.")

def prompt_int_with_skip(prompt, current_value):
    while True:
        val = input(f"{prompt} (current={current_value}): ").strip()
        if not val:  # skip
            return None
        try:
            return int(val)
        except ValueError:
            print("Invalid input. Please enter a valid integer or press Enter to keep current value.")


def prompt_float_with_skip(prompt, current_value):
    while True:
        val = input(f"{prompt} (current={current_value}): ").strip()
        if not val:  # skip
            return None
        try:
            return float(val)
        except ValueError:
            print("Invalid input. Please enter a valid float or press Enter to keep current value.")

def prompt_hex_with_skip(prompt, current_value):
    while True:
        val = input(f"{prompt} (current={current_value}): ").strip()
        if not val:  # skip
            return None
        try:
            return decimal_to_hex(int(val, 16))
        except ValueError:
            print("Invalid input. Please enter a valid hex value or press Enter to keep current value.")

def prompt_time_with_skip(prompt, current_value):
    while True:
        val = input(f"{prompt} (current={current_value}): ").strip()
        if not val:  # skip
            return None
        try:
            time.strptime(val, "%H:%M")
            return val
        except ValueError:
            print("Invalid input. Please enter a valid time in HH:MM format or press Enter to keep current value.")

def prompt_yes_no_with_skip(prompt, current_value):
    while True:
        val = input(f"{prompt} (Y/N) (current={current_value}): ").strip().lower()
        if val in ['y', 'yes', 'Yes']:
            return True
        elif val in ['n', 'no', 'No']:
            return False
        else:
            print("Invalid input. Please enter 'Y' or 'N'.")

def prompt_time_hours(prompt):
    while True:
        val = input(f"{prompt}: ").strip()
        # don’t allow blank—instead re‑prompt
        if not val:
            print("This field is required; please enter a time in HH:MM format.")
            continue

        try:
            hour, minute = map(int, val.split(':'))
            if 0 <= hour < 24 and 0 <= minute < 60:
                return hour * 3600 + minute * 60
        except (ValueError, TypeError):
            pass

        print("Invalid input. Please enter a valid time in HH:MM format (e.g. 02:30).")

def decimal_to_hex(decimal):
    hex_value = hex(decimal)[2:].upper()
    return hex_value.zfill(6)

def user_input_thread(command_queue, state):
    while True:
        valid_commands = ["pt", "pp", "pang", "pa",
                          "start", "change", "status", "q", ""]
        cmd = input().strip().lower()
        if cmd not in valid_commands:
            print("Unknown command. Valid commands:\n"
                  " pt, pp, pang, pa, start, change, status, q")
            continue

        if cmd == "pa":
            day_str = input("Enter a day index [0, N-1] to plot the altitude: ").strip()
            if not day_str.isdigit():
                print("Invalid day index. Command aborted.")
                continue
            command_queue.put(('pa', day_str))

        elif cmd == "change":
            drop_countdown = None
            end_feed_countdown = None
            new_cycle_length = prompt_int_with_skip(
                "Enter new lunar cycle length",
                state['user_cycle_length'])
            new_speed = prompt_float_with_skip(
                "Enter new speed factor",
                state['speed_factor'])
            new_day_length = prompt_float_with_skip(
                "Enter new real-time seconds for 24-hour sim-day",
                state['day_length_in_real_seconds'])
            new_start_time = prompt_time_with_skip(
                "Enter new cycle start time (HH:MM)",
                state['cycle_start_time'])
            new_hex_color = prompt_hex_with_skip(
                "Enter new hex color",
                state['hex_color'])
            new_feed_start_time = prompt_time_with_skip(
                "Enter new feeder start time (HH:MM)",
                state['feed_start_time'])
            new_feed_end_time = prompt_time_with_skip(
                "Enter new feeder end time (HH:MM)",
                state['feed_end_time'])
            independent_timer = prompt_yes_no_with_skip(
                "Do you want to use an independent timer for feeder?",
                state['independent_timer'])
            if independent_timer:
                drop_countdown = prompt_time_with_skip(
                    "Enter time to drop feeder (HH:MM)",
                    state['drop_countdown'])
                end_feed_countdown = prompt_time_with_skip(
                    "Enter time to end feeding (HH:MM)",
                    state['end_feed_countdown'])
            new_start_phase = prompt_phase_with_skip(
            "Enter new start phase",
            state.get('start_phase', 'Full Moon'))

            command_queue.put(('change', (
        new_cycle_length,
        new_speed,
        new_day_length,
        new_start_time,
        new_hex_color,
        new_feed_start_time,
        new_feed_end_time,
        independent_timer,
        drop_countdown,
        end_feed_countdown,
        new_start_phase,        
    )))


        elif cmd == "status":
            command_queue.put(('status', None))
        else:
            command_queue.put((cmd, None))

        if cmd == 'q':
            break

def simulation_loop(
        schedule,
        cycle_start_date,
        user_cycle_length,
        update_interval_minutes,
        speed_factor,
        day_length_in_real_seconds,
        hex_color,
        feed_start_time,
        feed_end_time,
        independent_timer,
        drop_countdown,
        end_feed_countdown,
        stop_event,
        shared_state=None
):
    real_secs_per_sim_minute = day_length_in_real_seconds / (24 * 60.0)
    sim_minutes_per_update   = 1.0 / 100.0
    real_secs_per_update     = real_secs_per_sim_minute / 100.0 / speed_factor

    # Initialize simulation clock
    simulation_time = cycle_start_date
    

    # Set up display
    disp = OLED_1in27_rgb.OLED_1in27_rgb()
    disp.Init()
    disp.clear()

    # Track whether we've drawn day or night frame
    day_frame_drawn   = False
    night_frame_drawn = False

    # State for servo + feeder threads
    servo_thread = None
    global feeder_thread
    feeder_thread = None
    global compare_alt
    compare_alt = None

    sun_arm_moved = False
    moon_reset_moved = False
    sun_reset_moved = False

    feeder_dropped = False

    


    # Determine initial mode
    prev_is_day = SUNRISE_HOUR <= simulation_time.hour < SUNSET_HOUR
    if prev_is_day:
        day_count   = 1
        night_count = 0
    else:
        day_count   = 0
        night_count = 1

    print("\n[Simulation Thread] Started.")
    print(f" Independent Timer: {independent_timer}")

    while not stop_event.is_set():
        world_time = datetime.datetime.now()
        real_world_time = datetime.datetime.now()
        #print(f"Real World Time: {real_world_time:%Y-%m-%d %H:%M}")
        
        # Determine day/night
        is_day = SUNRISE_HOUR <= simulation_time.hour < SUNSET_HOUR

        # Draw a blank frame on transition
        if is_day and not day_frame_drawn:
            img = Image.new('RGB', (disp.width, disp.height), SUN_COLOR)
            disp.ShowImage(disp.getbuffer(img))
            day_frame_drawn   = True
            night_frame_drawn = False

        elif not is_day and not night_frame_drawn:
            base_hex = "#" + hex_color
            img = Image.new('RGB', (disp.width, disp.height), base_hex)
            disp.ShowImage(disp.getbuffer(img))
            night_frame_drawn = True
            day_frame_drawn   = False

        # Update sunrise/sunset counters
        if is_day and not prev_is_day:
            night_count = day_count
            day_count  += 1
        elif not is_day and prev_is_day:
            day_count = night_count + 1
        prev_is_day = is_day

        # Find current schedule entry
        entry = find_schedule_entry_for_time(schedule, cycle_start_date, simulation_time)

        # Compute altitude & phase angle
        if is_day:
            altitude_deg = 90.0
            print(f"[Sim {simulation_time:%Y-%m-%d %H:%M}] Day {day_count} – Sun is out (alt=90°).")
        else:
            altitude_deg = calculate_current_altitude(entry, simulation_time, cycle_start_date)
            if altitude_deg > 0:
                print(f"[Sim {simulation_time:%Y-%m-%d %H:%M}] "
                      f"Night {night_count} – Phase: {entry['phase']} "
                      f"– Altitude: {altitude_deg:.1f}° – Phase Angle: {entry['phase_angle']:.2f}")
            else:
                print(f"[Sim {simulation_time:%Y-%m-%d %H:%M}] Night {night_count} – Moon not visible (alt=0).")
                
        if is_day:
            sun_reset_moved = False
            moon_reset_moved = False
            if not sun_arm_moved and (servo_thread is None or not servo_thread.is_alive()):
                compare_alt = 90
                print("GOING TO 90°")
                servo_thread = threading.Thread(
                    target=move_arm, args=(current_servo_angle, 90), daemon=True
                )
                servo_thread.start()
                sun_arm_moved = True

        elif altitude_deg > 0:
            moon_reset_moved = False
            sun_arm_moved    = False
            target = altitude_deg

            if servo_thread is None or not servo_thread.is_alive():
                # print("Moving freely with Moon")
                if target != current_servo_angle:
                    servo_thread = threading.Thread(
                        target=move_arm_zero,
                        args=(current_servo_angle, target, 0.06, 1),
                        daemon=True
                    )
                    servo_thread.start()
            elif servo_thread is None and not sun_reset_moved:
                # print("Exiting Sun Position")
                if target != current_servo_angle and target > 90:
                    servo_thread = threading.Thread(
                        target=move_arm_zero, args=(current_servo_angle, 180, 0.06, 1), daemon=True
                    )
                    servo_thread.start()
                    sun_reset_moved = True
                elif target != current_servo_angle and target < 90:
                    servo_thread = threading.Thread(
                        target=move_arm_zero, args=(current_servo_angle, 0, 0.06, 1), daemon=True
                    )
                    servo_thread.start()
                    sun_reset_moved = True

        else:
            if (servo_thread is None or not servo_thread.is_alive()) and not moon_reset_moved:
                print("Moon not Visible, ENTERING 0°")
                servo_thread = threading.Thread(
                    target=move_arm_zero, args=(current_servo_angle, 0, 0.05, 1), daemon=True
                )
                servo_thread.start()
                moon_reset_moved = True

        if simulation_time.strftime('%H:%M') == feed_start_time and not independent_timer:
            print("It's FEEDING TIME")
            feeder_thread = threading.Thread(target=drop_feeder, daemon=True)
            feeder_thread.start()

        if simulation_time.strftime('%H:%M') == feed_end_time and not independent_timer:
            feeder_thread = threading.Thread(target=shake_feeder, daemon=True)
            feeder_thread.start()
        
        

        
        if independent_timer and real_world_time.strftime('%H:%M') == drop_countdown and ((feeder_thread is None) or (not feeder_thread.is_alive())):
            print("Independent Timer Started")
            print(end_feed_countdown)
            feeder_thread = threading.Thread(target=drop_alarm, daemon=True)
            feeder_thread.start()
        if independent_timer and real_world_time.strftime('%H:%M') == end_feed_countdown and ((feeder_thread is None) or (not feeder_thread.is_alive())):
            print("Independent Timer Ended")
            feeder_thread = threading.Thread(target=feeding_alarm, daemon=True)
            feeder_thread.start()

        if shared_state is not None:
            shared_state['sim_time']            = simulation_time
            elapsed                             = simulation_time - cycle_start_date
            total_sec                           = user_cycle_length * 24 * 3600
            shared_state['progress']            = (elapsed.total_seconds() / total_sec) * 100.0
            shared_state['current_altitude']    = altitude_deg
            if altitude_deg > 0:
                shared_state['current_phase']       = entry['phase']
                shared_state['current_phase_angle'] = entry['phase_angle']
            else:
                shared_state['current_phase']       = 'Sun / No Moon'
                shared_state['current_phase_angle'] = entry['phase_angle']

        # Advance simulation clock
        simulation_time += datetime.timedelta(minutes=sim_minutes_per_update)
        time.sleep(real_secs_per_update)

    # On exit, clear display and reset hardware
    disp.clear()
    move_arm(current_servo_angle, 0)
    reset_feeder()
    print("[Simulation Thread] Exiting…")


    move_arm(current_servo_angle, 0)
    reset_feeder()





    can_move = (servo_thread is None) or (not servo_thread.is_alive())
    feeder_can_move = (feeder_thread is None) or (not feeder_thread.is_alive())
    if can_move:
        servo_thread = threading.Thread(target=move_arm, args = (current_servo_angle, 0), daemon=True)
        servo_thread.start()
    else:
        servo_thread.join()
        servo_thread = threading.Thread(target=move_arm, args = (current_servo_angle, 0), daemon=True)
        servo_thread.start()
    if feeder_can_move:
        feeder_thread = threading.Thread(target=move_feeder, args= (current_feeder_angle, 25, 0.05, 1), daemon=True)
        feeder_thread.start()
    else:
        feeder_thread.join()
        feeder_thread = threading.Thread(target=move_feeder, args=(current_feeder_angle,20,0.05, 1), daemon=True)
        feeder_thread.start()
    
    



def handle_command(cmd, arg, stop_event, state):
    if cmd == 'pt':
        plot_moon_schedule_times(state['moon_schedule'])

    elif cmd == 'pp':
        plot_moon_schedule_phases(state['moon_schedule'])

    elif cmd == 'pang':
        plot_moon_phase_angle(state['moon_schedule'])

    elif cmd == 'pa':
        day_idx = int(arg)
        if 0 <= day_idx < len(state['moon_schedule']):
            plot_hourly_altitude(state['moon_schedule'][day_idx],
                                 state['cycle_start_date'],
                                 marker_interval=30)
        else:
            print("Invalid day index!")

    elif cmd == 'start':
        if not state['simulation_started']:
            state['simulation_started'] = True
            sim_thread = threading.Thread(
                target=simulation_loop,
                args=(state['moon_schedule'], state['cycle_start_date'],
                      state['user_cycle_length'], .1, state['speed_factor'],
                      state['day_length_in_real_seconds'], state['hex_color'],
                      state['feed_start_time'], state['feed_end_time'],
                      state['independent_timer'], state['drop_countdown'],
                      state['end_feed_countdown'], stop_event),
                daemon=True)
            sim_thread.start()
            state['simulation_thread'] = sim_thread
        else:
            print("Simulation already running.")

    elif cmd == 'change':
        (new_cycle_length, new_speed, new_day_length, new_start_time,
         new_hex_color, new_feed_time, new_feed_end_time,
         independent_timer, drop_countdown, end_feed_countdown, new_start_phase) = arg

        if new_cycle_length is not None:
            state['user_cycle_length'] = new_cycle_length
        if new_speed is not None:
            state['speed_factor'] = new_speed
        if new_day_length is not None:
            state['day_length_in_real_seconds'] = new_day_length
        if new_hex_color is not None:
            state['hex_color'] = new_hex_color
        if new_feed_time is not None:
            state['feed_start_time'] = new_feed_time
        if new_feed_end_time is not None:
            state['feed_end_time'] = new_feed_end_time
        if independent_timer is not None:
            state['independent_timer'] = independent_timer
        if drop_countdown is not None:
            state['drop_countdown'] = drop_countdown
        if end_feed_countdown is not None:
            state['end_feed_countdown'] = end_feed_countdown

        if new_start_phase is not None:
            state['start_phase'] = new_start_phase

        if new_start_time is not None:
            state['cycle_start_time'] = new_start_time
            state['cycle_start_date'] = compute_cycle_start_date(new_start_time)
        else:
            state['cycle_start_date'] = datetime.datetime.now()

        state['moon_schedule'] = calculate_moonrise_times(
            state['user_cycle_length'],
            state.get('start_phase', 'Full Moon')
        )

        print("Options updated. Plot again or type 'start' to run.")
    elif cmd == 'status':
        print("Simulation Parameters")
        print(f"  Running            : {state['simulation_started']}")
        print(f"  Cycle Start Date   : {state['cycle_start_date']}")
        print(f"  Cycle Start Time   : {state['cycle_start_time']}")
        print(f"  Cycle Length (d)   : {state['user_cycle_length']}")
        print(f"  Day Length (s)     : {state['day_length_in_real_seconds']}")
        print(f"  Speed Factor       : {state['speed_factor']}")
        print(f"  Hex Color          : {state['hex_color']}")
        print(f"  Feed Start         : {state['feed_start_time']}")
        print(f"  Feed End           : {state['feed_end_time']}")
        print(f"  Independent Timer  : {state['independent_timer']}")
        print(f"  Drop Time          : {state['drop_countdown']}")
        print(f"  End Feed Time      : {state['end_feed_countdown']}")

    elif cmd == 'q':
        stop_event.set()

    elif cmd == '':
        pass
    else:
        print(f"[Main Thread] Unknown command: {cmd}")



def main():
    user_cycle_length = DEFAULT_LUNAR_CYCLE_LENGTH
    speed_factor = 1.0
    day_length_in_real_seconds = 86400
    hex_color = 'FF0000'

    start_time_str = datetime.datetime.now().strftime('%H:%M')
    cycle_start_dt = compute_cycle_start_date(start_time_str)
    moon_schedule  = calculate_moonrise_times(user_cycle_length)

    state = {
        'moon_schedule': moon_schedule,
        'cycle_start_date': cycle_start_dt,
        'cycle_start_time': start_time_str,
        'user_cycle_length': user_cycle_length,
        'speed_factor': speed_factor,
        'day_length_in_real_seconds': day_length_in_real_seconds,
        'hex_color': hex_color,
        'feed_start_time': '19:00',
        'feed_end_time': '04:00',
        'independent_timer': False,
        'drop_countdown': '06:00',
        'end_feed_countdown': '08:00',
        'simulation_thread': None,
        'simulation_started': False,
    }

    command_queue = Queue()
    stop_event = threading.Event()

    input_thread = threading.Thread(
        target=user_input_thread,
        args=(command_queue, state),
        daemon=True)
    input_thread.start()

    print("Ready. Commands: pt, pp, pang, pa, change, status, start, q")

    while not stop_event.is_set():
        while not command_queue.empty():
            cmd, arg = command_queue.get()
            handle_command(cmd, arg, stop_event, state)
        plt.pause(0.01)
        time.sleep(0.1)

    if state['simulation_thread'] is not None:
        state['simulation_thread'].join()

    print("Exiting.")




if __name__ == "__main__":
    main()
