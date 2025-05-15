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

SUNSET_HOUR  = 14
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
        print(f"Moving arm to {angle}°")
        #print(f"This is the delay: {delay}")

def move_arm_zero(start_angle, end_angle, delay, step):
    #start_angle = 180
    #end_angle = 90
    if start_angle < end_angle:
        angle_range = range(int(start_angle), int(end_angle) + 1, int(step))
    else:
        angle_range = range(int(start_angle), int(end_angle) - 1, int(-step))
    for current_servo_angle in angle_range:
        set_servo_angle(current_servo_angle)
        if math.floor(compare_alt) == math.floor(current_servo_angle):
            print(f"angles match: {compare_alt:.1f}"
            f" and {current_servo_angle:.1f}")
            return
        else:
            print(f"no match")
            time.sleep(delay) 
            print(f"Moving arm to this {current_servo_angle}°")

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

    # if stop_event is None:
    #     stop_event = threading.Event()
    
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
    timer_flag = False

def feeding_alarm():
    print(f"Feeder Reset")
    return_feeder()
    #shake_feeder()
    reset_feeder()
    timer_flag = False

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
    plt.ylim(0, 190.05)  # small padding above
    plt.grid(True, alpha=0.3)
    plt.show(block=False)


def plot_moon_schedule_times(schedule):
    def to_decimal_hour(t):
        return t.hour + t.minute / 60.0 if t else None

    days       = []
    rise_hours = []
    set_hours  = []

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
        if val in ['y', 'yes']:
            return True
        elif val in ['n', 'no']:
            return False
        else:
            print("Invalid input. Please enter 'Y' or 'N'.")

# def prompt_time_hours(prompt):
#     while True:
#         val = input(f"{prompt}: ").strip()
#         # don’t allow blank—instead re‑prompt
#         if not val:
#             print("This field is required; please enter a time in HH:MM format.")
#             continue

#         try:
#             hour, minute = map(int, val.split(':'))
#             if 0 <= hour < 24 and 0 <= minute < 60:
#                 return hour * 3600 + minute * 60
#         except (ValueError, TypeError):
#             pass

#         print("Invalid input. Please enter a valid time in HH:MM format (e.g. 02:30).")

def decimal_to_hex(decimal):
    hex_value = hex(decimal)[2:].upper()
    return hex_value.zfill(6)

def user_input_thread(command_queue, state):
    while True:
        valid_commands = ["pt", "pp", "pang", "pa", "start", "change", "status", "q", ""]
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
            print("[User Input Thread] Changing user options...")
            new_cycle_length = prompt_int_with_skip("Enter new lunar cycle length", state['user_cycle_length'])
            new_speed = prompt_float_with_skip("Enter new speed factor", state['speed_factor'])
            new_day_length = prompt_float_with_skip("Enter new real-time seconds for 24-hour sim-day", state['day_length_in_real_seconds'])
            new_hex_color = prompt_hex_with_skip("Enter new hex color", state['hex_color'])
            new_feed_start_time = prompt_time_with_skip("Enter new feeder start time (HH:MM)", state['feed_start_time'])
            new_feed_end_time = prompt_time_with_skip("Enter new feeder end time (HH:MM)", state['feed_end_time'])
            independent_timer = prompt_yes_no_with_skip("Do you want to use an independent timer for feeder?", state['independent_timer'])
            if independent_timer:
                drop_countdown = prompt_time_with_skip("Enter time to drop feeder (HH:MM)", state['drop_countdown'])
                print(f"Drop time: {drop_countdown}")
                end_feed_countdown = prompt_time_with_skip("Enter time to end feeding (HH:MM)", state['end_feed_countdown'])
                print(f"End feed time: {end_feed_countdown}")
            command_queue.put(('change', (new_cycle_length, new_speed, new_day_length, new_hex_color, new_feed_start_time,
                                           new_feed_end_time, independent_timer, drop_countdown, end_feed_countdown)))

        elif cmd == "status":
            command_queue.put(('status', None))

        #elif cmd == "reset":

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
        shared_state=None          # ← pass in the global “state” dict from app.py
):
    """
    Advance simulated time, move the servos / feeder, and (optionally)
    push live‑status metrics into a shared dictionary so the Flask
    dashboard can display them in real‑time.
    """

    real_secs_per_sim_minute = day_length_in_real_seconds / (24 * 60)

    simulation_time = cycle_start_date
    cycle_end_time  = cycle_start_date + datetime.timedelta(days=user_cycle_length)

    
    disp = OLED_1in27_rgb.OLED_1in27_rgb()
    disp.Init()
    disp.clear()

    night_frame_drawn = False
    day_frame_drawn   = False
    
    sun_arm_moved = False
    moon_reset_moved = False

    servo_thread  = None
    last_motion_type  = None 

    feeder_thread = None
    
    
    global compare_alt
    compare_alt = None

    sun_reset_moved = False

 
    feed_check = None
    drop_check = None



    print("\n[Simulation Thread] Started.")
    print(f" Independent Timer: {independent_timer}")

    while not stop_event.is_set():
        phase_angle = 0.0
        altitude_deg = 0.0

        if simulation_time >= cycle_end_time:
            print("[Simulation Thread] Reached end of the simulation.")
            break

        if servo_thread is not None and not servo_thread.is_alive():
        # Only do this once per thread
            ''' do this for all of the cases and save their last angle'''
            if last_motion_type == 'zero':
                # We just finished a zero‐reset; what's the simulation's moon altitude now?
                entry = find_schedule_entry_for_time(
                    schedule, cycle_start_date, simulation_time
                )
                if entry: 
                    last_alt = calculate_current_altitude(entry, simulation_time, cycle_start_date)
                    print(f"Last alt: {last_alt}:2f")
            servo_thread   = None
            last_motion_type = None

        # check if thread is finsihed
        can_move = (servo_thread is None) or (not servo_thread.is_alive())
        feeder_can_move = (feeder_thread is None) or (not feeder_thread.is_alive())


        current_entry = find_schedule_entry_for_time(
            schedule, cycle_start_date, simulation_time
        )
        is_day = SUNRISE_HOUR <= simulation_time.hour < SUNSET_HOUR

        if is_day:
            altitude_deg = 90.0
            print(f"[Sim {simulation_time:%Y-%m-%d %H:%M}] Sun is out (alt={altitude_deg}°).")

        elif current_entry is not None:
            '''fix when the angle starts at 180 or 0 to be a smooth transition, prob need an if statment that checks when those entries happen'''
            
            altitude_deg = calculate_current_altitude(current_entry, simulation_time, cycle_start_date)
            compare_alt = altitude_deg # compare this altitude
            print(f"Comparison Alt: {compare_alt:.2f}")
            phase_angle  = current_entry['phase_angle']
            print(f"[Sim {simulation_time:%Y-%m-%d %H:%M}] "
                  f"Day {current_entry['day']} - Phase: {current_entry['phase']} "
                  f"- Altitude: {altitude_deg:.1f}° - Phase Angle: {phase_angle:.2f}")
            
        else:
            compare_alt = 0
            print(f"[Sim {simulation_time:%Y-%m-%d %H:%M}] Moon not visible (alt=0).")



        if is_day:

            sun_reset_moved = False
            moon_reset_moved = False
            #  move to 90
            if not sun_arm_moved and can_move:
                compare_alt = 90
                print("GOING TO 90°")
                servo_thread = threading.Thread(
                    target=move_arm, args=(current_servo_angle, 90), daemon=True
                )
                servo_thread.start()
                sun_arm_moved = True

        


        elif current_entry is not None:
            # → Moon altitude
            moon_reset_moved = False
            sun_arm_moved = False
            #print(f"{altitude_deg:.2f}")
            target = altitude_deg
            #if can_move and

            if can_move:
                print("Moving freely with Moon")
                target = altitude_deg
                if target != current_servo_angle:
                    servo_thread = threading.Thread(target = move_arm_zero,
                        args=(current_servo_angle, target, 0.06, 1), daemon=True
                    )
                    servo_thread.start()
                else: 
                    servo_thread = threading.Thread(
                        target=lambda ang=target: set_servo_angle(ang),daemon=True
                    )
                    servo_thread.start()

            elif can_move and not sun_reset_moved:
                print("Exiting Sun Position")
                if target != current_servo_angle and target > 90:
                    servo_thread = threading.Thread(target=move_arm_zero, 
                        args=(current_servo_angle, 180, 0.06, 1), daemon=True
                    ) 
                    servo_thread.start()
                    sun_reset_moved = True
                elif target != current_servo_angle and target < 90:
                    servo_thread = threading.Thread(target=move_arm_zero, args=(current_servo_angle, 0, 0.06, 1), daemon=True) 
                    servo_thread.start()
                    sun_reset_moved = True
                
                
        elif can_move and not moon_reset_moved:
            sun_arm_moved = False                
            print("Moon not Visible, ENTERING 0°")
            servo_thread = threading.Thread(
                    target=move_arm_zero, args=(current_servo_angle, 0, 0.05, 1), daemon=True
                )
                #''' not always 0 cases where the angle jumps from no moon to sun, so it needs to remember last angle'''#moon_reset_moved
            last_motion_type = 'zero'
            servo_thread.start()
            moon_reset_moved = True        
                
        

        if simulation_time.strftime('%H:%M') == feed_start_time and independent_timer == False and feeder_can_move:
            print("It's FEEDING TIME")
            feeder_thread = threading.Thread(target=drop_feeder,  daemon=True)
            feeder_thread.start()

        if simulation_time.strftime('%H:%M') == feed_end_time and independent_timer == False and feeder_can_move:
            feeder_thread = threading.Thread(target=shake_feeder, daemon=True)
            feeder_thread.start()

        real_time = datetime.datetime.now()

        if simulation_time.strftime('%H:%M') == drop_countdown and independent_timer == True and feeder_can_move and drop_check == False:
            drop_check = True
            feeder_thread = threading.Thread(target=drop_alarm, daemon=True)
            feeder_thread.start()
            print(f"Independent Timer Started")

        if simulation_time.strftime('%H:%M') == end_feed_countdown and independent_timer == True and feeder_can_move and feed_check == False:
            feed_check = True
            feeder_thread = threading.Thread(target=feeding_alarm, daemon=True)
            feeder_thread.start()
            print(f"Independent Timer Ended")

        if simulation_time.strftime('%H:%M') != feed_check:
            feed_check = False
        if simulation_time.strftime('%H:%M') != drop_check:
            drop_check = False
            
            
        
        is_day   = SUNRISE_HOUR <= simulation_time.hour < SUNSET_HOUR
        is_night = not is_day

        if is_day and night_frame_drawn:
            night_frame_drawn = False
            img = Image.new('RGB', (disp.width, disp.height), SUN_COLOR)
            disp.ShowImage(disp.getbuffer(img))

        if is_night and not night_frame_drawn:
            base_hex_color = "#" + hex_color
            img = Image.new('RGB', (disp.width, disp.height), base_hex_color)
            disp.ShowImage(disp.getbuffer(img))
            night_frame_drawn = True


        if shared_state is not None:
            # sim clock
            shared_state['sim_time'] = simulation_time

            # % progress through the current cycle
            elapsed   = simulation_time - cycle_start_date
            total_sec = user_cycle_length * 24 * 3600
            shared_state['progress'] = (elapsed.total_seconds() / total_sec) * 100.0

            # what’s in the sky
            if current_entry:
                shared_state['current_phase']       = current_entry['phase']
                shared_state['current_phase_angle'] = phase_angle
            else:
                shared_state['current_phase']       = 'Sun / No Moon'
                shared_state['current_phase_angle'] = phase_angle

            shared_state['current_altitude'] = altitude_deg

        sleep_real = (update_interval_minutes * real_secs_per_sim_minute) / speed_factor
        time.sleep(sleep_real)
        simulation_time += datetime.timedelta(minutes=update_interval_minutes)

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
        print("Plotting Moonrise/Moonset times...")
        plot_moon_schedule_times(state['moon_schedule'])

    elif cmd == 'pp':
        print("Plotting Moon schedule phases...")
        plot_moon_schedule_phases(state['moon_schedule'])

    elif cmd == 'pang':
        print("Plotting Moon Phase Angles...")
        plot_moon_phase_angle(state['moon_schedule'])

    elif cmd == 'pa':
        if arg and arg.isdigit():
            day_idx = int(arg)
            if 0 <= day_idx < len(state['moon_schedule']):
                print(f"Plotting altitude for day {day_idx}...")
                plot_hourly_altitude(state['moon_schedule'][day_idx],
                                     state['cycle_start_date'],
                                     marker_interval=30)
            else:
                print("Invalid day index!")
        else:
            print("Please enter a valid integer for the day index.")

    elif cmd == 'start':
        if not state['simulation_started']:
            print("[Main Thread] Starting simulation now...")
            state['simulation_started'] = True

            sim_thread = threading.Thread(
                target=simulation_loop,
                args=(
                    state['moon_schedule'],
                    state['cycle_start_date'],
                    state['user_cycle_length'],
                    .1,  # update_interval_minutes
                    state['speed_factor'],
                    state['day_length_in_real_seconds'],
                    state['hex_color'],
                    state['feed_start_time'],
                    state['feed_end_time'],
                    state['independent_timer'],
                    state['drop_countdown'],
                    state['end_feed_countdown'],
                    stop_event
                ),
                daemon=True
            )
            sim_thread.start()
            state['simulation_thread'] = sim_thread
        else:
            print("[Main Thread] Simulation is already running.")

    elif cmd == 'change':
        new_cycle_length, new_speed, new_day_length, new_hex_color, new_feed_time, new_feed_end_time, independent_timer, drop_countdown, end_feed_countdown = arg
        # If the user typed nothing, it's None -> keep old value
        if new_cycle_length is not None:
            state['user_cycle_length'] = new_cycle_length
        if new_speed is not None:
            state['speed_factor'] = new_speed
        if new_day_length is not None:
            state['day_length_in_real_seconds'] = new_day_length
        if new_hex_color is not None:
            state['hex_color'] = new_hex_color
        if new_feed_time is not None:
            state['feed_time'] = new_feed_time
        if new_feed_end_time is not None:
            state['feed_end_time'] = new_feed_end_time
        if independent_timer is not None:
            state['independent_timer'] = independent_timer
        if drop_countdown is not None:
            state['drop_countdown'] = drop_countdown
        if end_feed_countdown is not None:
            state['end_feed_countdown'] = end_feed_countdown

        # Recompute schedule
        state['moon_schedule'] = calculate_moonrise_times(state['user_cycle_length'])
        state['cycle_start_date'] = datetime.datetime.now()

        print("[Main Thread] Options updated. You can plot again or type 'start' to run simulation.")

    elif cmd == 'status':
        print("[Main Thread] Current Simulation Parameters:")
        print(f"  Sim Started?  : {state['simulation_started']}")
        print(f"  Start Date    : {state['cycle_start_date']}")
        print(f"  Cycle Length  : {state['user_cycle_length']}")
        print(f"  Day Length (s): {state['day_length_in_real_seconds']}")
        print(f"  Speed Factor  : {state['speed_factor']}")
        print(f"  Hex Color     : {state['hex_color']}")
        print(f"  Feed Start    : {state['feed_start_time']}")
        print(f"  Feed End      : {state['feed_end_time']}")
        print(f"  Independent Timer: {state['independent_timer']}")
        print(f"  Drop Time (Real World): {state['drop_countdown']}")
        print(f"  End Feed Time (Real World): {state['end_feed_countdown']}")
        

    elif cmd == 'q':
        print("[Main Thread] User requested quit.")
        #move_arm(current_servo_angle, 0)
        stop_event.set()
        

    elif cmd == '':
        pass
    else:
        print(f"[Main Thread] Unknown command: {cmd}")


def main():
    user_cycle_length = DEFAULT_LUNAR_CYCLE_LENGTH
    speed_factor = 1.0
    day_length_in_real_seconds = 30
    hex_color = 'FF0000'  # Default color (red)

    # Build initial schedule
    moon_schedule = calculate_moonrise_times(user_cycle_length)
    cycle_start_date = datetime.datetime.now()

    # Shared state dictionary
    state = {
        'moon_schedule': moon_schedule,
        'cycle_start_date': cycle_start_date,
        'user_cycle_length': user_cycle_length,
        'speed_factor': speed_factor,
        'day_length_in_real_seconds': day_length_in_real_seconds,
        'hex_color': hex_color,
        'feed_start_time': '19:00',
        'feed_end_time' : '04:00',
        'independent_timer': False,
        'drop_countdown': '06:00',
        'end_feed_countdown': '08:00',
        'simulation_thread': None,
        'simulation_started': False,
    }

    # Create queue and threads
    command_queue = Queue()
    stop_event = threading.Event()

    # Pass state to user_input_thread so it can show current values in prompts
    input_thread = threading.Thread(
        target=user_input_thread,
        args=(command_queue, state),
        daemon=True
    )
    input_thread.start()

    print("[Main Thread] Ready. Type commands in the console:\n"
          "  pt       -> plot moonrise/moonset times\n"
          "  pp       -> plot moon schedule phases\n"
          "  pang     -> plot moon phase angles\n"
          "  pa       -> plot hourly altitude for a specific day\n"
          "  change   -> change any of the options\n"
          "  status   -> display current parameters\n"  
          "  start    -> start the simulation\n"
          "  q        -> quit the program\n")

    while not stop_event.is_set():
        while not command_queue.empty():
            cmd, arg = command_queue.get()
            handle_command(cmd, arg, stop_event, state)

        plt.pause(0.01)
        time.sleep(0.1)

    if state['simulation_thread'] is not None:
        state['simulation_thread'].join()

    print("[Main Thread] Exiting.")


if __name__ == "__main__":
    main()
