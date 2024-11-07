from skyfield.api import Loader
from skyfield.almanac import moon_phase
from calendar import monthrange
import collections
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

PHASE_IMAGES = {
    'Waxing Crescent': 'Moon Phase/Waxing Crescent.png',
    'First Quarter': 'Moon Phase/First Quarter.png',
    'Waxing Gibbous': 'Moon Phase/Waxing Gibbous.png',
    'Full Moon': 'Moon Phase/Full Moon.png',
    'Waning Gibbous': 'Moon Phase/Waning Gibbous.png',
    'Last Quarter': 'Moon Phase/Last Quarter.png',
    'Waning Crescent': 'Moon Phase/Waning Crescent.png',
    'New Moon': 'Moon Phase/New Moon.png'
}

PHASE_BRIGHTNESS = {
    'Waxing Crescent': 0.3,
    'First Quarter': 0.5,
    'Waxing Gibbous': 0.7,
    'Full Moon': 1.0,
    'Waning Gibbous': 0.7,
    'Last Quarter': 0.5,
    'Waning Crescent': 0.3,
    'New Moon': 0.1
}

def plot_moon_phases(days, phases, month, year):
    fig, ax = plt.subplots(figsize=(15, 5))
    scaled_days = [day * 1.5 for day in days]

    for i, day in enumerate(scaled_days):
        image_path = PHASE_IMAGES[phases[i]]
        image = plt.imread(image_path)
        imagebox = OffsetImage(image, zoom=0.3)
        alpha = PHASE_BRIGHTNESS[phases[i]]
        ab = AnnotationBbox(imagebox, (day, 0), frameon=False, box_alignment=(0.5, -0.2), alpha=alpha)
        ax.add_artist(ab)
        ax.text(day, -1, str(days[i]), ha='center', va='top', fontsize=10)

    ax.set_xlim(0, scaled_days[-1] + 1)
    ax.set_ylim(-3, 2)
    ax.axis('off')
    ax.set_title(f'Moon Phases for {month}/{year}')
    plt.show()

def plot_moon_phases_by_minute(month, day, year, hour):
    load = Loader('~/skyfield-data')
    ts = load.timescale()
    eph = load('de421.bsp')

    minutes = []
    phases = []

    for minute in range(60):
        date = ts.utc(year, month, day, hour, minute)
        phase = moon_phase(eph, date)
        phase_degrees = phase.degrees

        if 0 <= phase_degrees < 45:
            phases.append('Waxing Crescent')
        elif 45 <= phase_degrees < 90:
            phases.append('First Quarter')
        elif 90 <= phase_degrees < 135:
            phases.append('Waxing Gibbous')
        elif 135 <= phase_degrees < 180:
            phases.append('Full Moon')
        elif 180 <= phase_degrees < 225:
            phases.append('Waning Gibbous')
        elif 225 <= phase_degrees < 270:
            phases.append('Last Quarter')
        elif 270 <= phase_degrees < 315:
            phases.append('Waning Crescent')
        else:
            phases.append('New Moon')

        minutes.append(minute)

    fig, ax = plt.subplots(figsize=(15, 5))
    scaled_minutes = [minute * 1.5 for minute in minutes]

    for i, minute in enumerate(scaled_minutes):
        image_path = PHASE_IMAGES[phases[i]]
        image = plt.imread(image_path)
        imagebox = OffsetImage(image, zoom=0.2)
        alpha = PHASE_BRIGHTNESS[phases[i]]
        ab = AnnotationBbox(imagebox, (minute, 0), frameon=False, box_alignment=(0.5, -0.2), alpha=alpha)
        ax.add_artist(ab)
        ax.text(minute, -1, f"{minutes[i]:02d}", ha='center', va='top', fontsize=8)

    ax.set_xlim(0, scaled_minutes[-1] + 1)
    ax.set_ylim(-3, 2)
    ax.axis('off')
    ax.set_title(f'Moon Phases for Each Minute of {month}/{day}/{year} {hour}:00')
    plt.show()

def get_moon_phases(month, year, hour, minute):
    load = Loader('~/skyfield-data')
    ts = load.timescale()
    eph = load('de421.bsp')
    days_in_month = monthrange(year, month)[1]
    days, phases = [], []

    for day in range(1, days_in_month + 1):
        date = ts.utc(year, month, day, hour, minute)
        phase = moon_phase(eph, date)
        phase_degrees = phase.degrees

        if 0 <= phase_degrees < 45:
            phases.append('Waxing Crescent')
        elif 45 <= phase_degrees < 90:
            phases.append('First Quarter')
        elif 90 <= phase_degrees < 135:
            phases.append('Waxing Gibbous')
        elif 135 <= phase_degrees < 180:
            phases.append('Full Moon')
        elif 180 <= phase_degrees < 225:
            phases.append('Waning Gibbous')
        elif 225 <= phase_degrees < 270:
            phases.append('Last Quarter')
        elif 270 <= phase_degrees < 315:
            phases.append('Waning Crescent')
        else:
            phases.append('New Moon')

        days.append(day)

    return days, phases

def get_custom_lunar_cycle(month, year, hour, minute, target_cycle_length):
    days, phases = get_moon_phases(month, year, hour, minute)
    
    if len(phases) <= target_cycle_length:
        print("The current month already has fewer or equal days than the target cycle length.")
        return days, phases
    
    phase_counts = collections.Counter(phases)
    while len(phases) > target_cycle_length:
        # Sort phases by count, starting with the most common
        sorted_phases = phase_counts.most_common()
        for phase, count in sorted_phases:
            # Remove the phase if it has more than one occurrence and if length exceeds target
            if phase_counts[phase] > 1 and len(phases) > target_cycle_length:
                index = phases.index(phase)
                phases.pop(index)
                days.pop(index)
                phase_counts[phase] -= 1

    return days, phases

def get_user_input():
    while True:
        view_option = input("Do you want to view moon phases for the entire month or by each minute of a specific hour? (month/hour/quit): ").strip().lower()
        if view_option == 'month':
            month = int(input("Enter the month (1-12): "))
            year = int(input("Enter the year: "))
            hour = int(input("Enter the hour (0-23): "))
            minute = int(input("Enter the minute (0-59): "))
            custom_cycle = input("Do you want to set a custom lunar cycle length? (yes/no): ").strip().lower()
            
            if custom_cycle == 'yes':
                target_cycle_length = int(input("Enter the desired lunar cycle length (e.g., 20): "))
                days, phases = get_custom_lunar_cycle(month, year, hour, minute, target_cycle_length)
            else:
                days, phases = get_moon_phases(month, year, hour, minute)
            
            plot_moon_phases(days, phases, month, year)
        
        elif view_option == 'hour':
            month = int(input("Enter the month (1-12): "))
            day = int(input("Enter the day (1-31): "))
            year = int(input("Enter the year: "))
            hour = int(input("Enter the hour (0-23): "))
            plot_moon_phases_by_minute(month, day, year, hour)
        
        elif view_option == 'quit':
            print("Exiting program.")
            break
        
        else:
            print("Invalid option. Please enter 'month', 'hour', or 'quit'.")

# input_thread = threading.Thread(target=get_user_input)
# input_thread.start()
# input_thread.join()

get_user_input()
