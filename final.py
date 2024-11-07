from skyfield.api import Loader
from skyfield.almanac import moon_phase
from calendar import monthrange
import collections
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

def plot_moon_phases(days, phases, month, year):
    phase_images = {
        'Waxing Crescent': 'Moonlight/Moon Phase/Waxing Crescent.png',
        'First Quarter': 'Moonlight/Moon Phase/First Quarter.png',
        'Waxing Gibbous': 'Moonlight/Moon Phase/Waxing Gibbous.png',
        'Full Moon': 'Moonlight/Moon Phase/Full Moon.png',
        'Waning Gibbous': 'Moonlight/Moon Phase/Waning Gibbous.png',
        'Last Quarter': 'Moonlight/Moon Phase/Last Quarter.png',
        'Waning Crescent': 'Moonlight/Moon Phase/Waning Crescent.png',
        'New Moon': 'Moonlight/Moon Phase/New Moon.png'
    }

    phase_brightness = {
        'Waxing Crescent': 0.3,
        'First Quarter': 0.5,
        'Waxing Gibbous': 0.7,
        'Full Moon': 1.0,
        'Waning Gibbous': 0.7,
        'Last Quarter': 0.5,
        'Waning Crescent': 0.3,
        'New Moon': 0.1  # Almost invisible
    }

    fig, ax = plt.subplots(figsize=(15, 5))
    scaled_days = [day * 1.5 for day in days]  # Scale days for better visual spacing

    for i, day in enumerate(scaled_days):
        image_path = phase_images[phases[i]]
        image = plt.imread(image_path)
        imagebox = OffsetImage(image, zoom=0.3)  # Adjust zoom as necessary
        alpha = phase_brightness[phases[i]]  # Adjust alpha based on the phase
        ab = AnnotationBbox(imagebox, (day, 0), frameon=False, box_alignment=(0.5, -0.2), alpha=alpha)
        ax.add_artist(ab)
        ax.text(day, -1, str(days[i]), ha='center', va='top', fontsize=10)

    ax.set_xlim(0, scaled_days[-1] + 1)
    ax.set_ylim(-3, 2)
    ax.axis('off')
    ax.set_title(f'Moon Phases for {month}/{year}')
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


month = int(input("Enter the month (1-12): "))
year = 2016  
hour = int(input("Enter the hour (0-23): "))
minute = int(input("Enter the minute (0-59): "))
custom = input("Do you want to create a custom lunar phase (yes/no)? ")

days, phases = get_moon_phases(month, year, hour, minute) # Longitude of the Sun Longitude of the moon
if custom.lower() == 'yes':
    cycle_length = int(input("Enter the desired cycle length (e.g., 20): "))
    while len(phases) > cycle_length:
        phase_counts = collections.Counter(phases)
        mode_phase = phase_counts.most_common(1)[0][0]
        for i in reversed(range(len(phases))):  # Use reversed to avoid skipping indices after pop
            if phases[i] == mode_phase and len(phases) > cycle_length:
                phases.pop(i)
                days.pop(i)

plot_moon_phases(days, phases, month, year)


