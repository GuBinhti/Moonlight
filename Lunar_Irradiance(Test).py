import numpy as np
from skyfield.api import load, Topos
from datetime import timedelta
import os
import pandas as pd


# Function to parse the file and return the data points as a list of tuples
def parse_data_points(file_path):
    """
    Parses data points from a file.

    :param file_path: Path to the file containing the data points.
    :return: A list of tuples containing the parsed data points.
    """
    data_points = []

    try:
        with open(file_path, 'r') as file:
            for line in file:
                parts = line.split()
                if len(parts) == 2:  # file should have two columns
                    try:
                        x = float(parts[0])
                        y = float(parts[1])
                        data_points.append((x, y))
                    except ValueError:
                        print(f"Skipping invalid line: {line.strip()}")
                else:
                    print(f"Skipping malformed line: {line.strip()}")
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return data_points


file_path = '/Users/diegomateos/Downloads/Lunar_Irradiance_Github.txt'

if not os.path.exists(file_path):
    raise FileNotFoundError(f"Error: File not found at {file_path}. Please verify the path.")

# Parse the lunar phase and irradiance data using the custom function
lunar_data = parse_data_points(file_path)

# Create a DataFrame from the lunar data for easier processing
unit22 = pd.DataFrame(lunar_data, columns=['phase', 'lunar_irrad'])

# Load planets and timescale
planets = load('/Users/diegomateos/Downloads/de421.bsp')
ts = load.timescale()

latitude = 0
longitude = -82.0
location = Topos(latitude_degrees=latitude, longitude_degrees=longitude)

start_time = ts.utc(2020, 1, 24, 15, 0, 0)

earth = planets['earth']
moon = planets['moon']
sun = planets['sun']

# MOON_ALBEDO = 0.12

mean_earthsun_dist = 149597870.700  # in km
mean_earthmoon_dist = 384402.0  # in km
radius_earth = 6378.140  # in km

times = []
for i in range(0, 250):
    time_offset = timedelta(days=i)
    observation_time = start_time + time_offset
    times.append(observation_time)

illumination_fractions = []
angles_from_full_moon = []
scaled_irradiance = []

# Calculate illumination fraction, angle from full moon, and scaled lunar irradiance for each time step
for observation_time in times:
    moon_observed_from_earth = earth.at(observation_time).observe(moon)
    sun_observed_from_earth = earth.at(observation_time).observe(sun)

    moon_fraction = moon_observed_from_earth.fraction_illuminated(sun)

    angle_from_full_moon = np.arccos(2 * moon_fraction - 1) * (180 / np.pi)

    illumination_fractions.append(moon_fraction)
    angles_from_full_moon.append(angle_from_full_moon)

    search = True
    phase_prev = 0
    lunar_irrad_prev = 0
    current_phase_angle = angle_from_full_moon

    while search:
        for index, row in unit22.iterrows():
            if current_phase_angle > float(row['phase']):
                phase_prev = float(row['phase'])
                lunar_irrad_prev = float(row['lunar_irrad'])
            else:
                search = False
                frac = (float(row['phase']) - current_phase_angle) / (float(row['phase']) - phase_prev)
                delta = float(row['lunar_irrad']) - lunar_irrad_prev
                lunar_irrad_dnb_interp = float(row['lunar_irrad']) - (delta * frac)
                break

    cos_phase_angle = np.cos(np.deg2rad(current_phase_angle))

    sun_distance = earth.at(observation_time).observe(sun).distance().km
    moon_distance = earth.at(observation_time).observe(moon).distance().km

    T1 = mean_earthsun_dist ** 2.0 + mean_earthmoon_dist ** 2.0 + 2.0 * mean_earthmoon_dist * mean_earthsun_dist * cos_phase_angle
    T2 = sun_distance ** 2.0 + moon_distance ** 2.0 + 2.0 * moon_distance * sun_distance * cos_phase_angle
    T3 = ((mean_earthmoon_dist - radius_earth) / (moon_distance - radius_earth)) ** 2.0

    SCALE_FACTOR = (T1 / T2) * T3
    #print(f"T1: {T1}")
    #print(f"T2: {T2}")
    #print(f"T3: {T3}")
    #print(f"Scalar: {SCALE_FACTOR}")
    print(f"Not Adjusted Lunar Irradiance: {lunar_irrad_dnb_interp}")


    adjusted_lunar_irrad = lunar_irrad_dnb_interp * SCALE_FACTOR


    day = observation_time.utc_iso().split('T')[0]
    print(f"Date: {day} | Angle from Full Moon: {angle_from_full_moon:.2f}° | "
          f"Illumination Fraction: {moon_fraction:.2%} | "
          f"Scaled Lunar Irradiance: {adjusted_lunar_irrad:.5f} W/m²")

    scaled_irradiance.append(adjusted_lunar_irrad)


output_file = '/Users/diegomateos/Downloads/lunar_irradiance_results.txt'
with open(output_file, 'w') as file:
    file.write("Date | Angle from Full Moon (°) | Scaled Lunar Irradiance (W/m²) | Illumination Fraction\n")
    for i in range(len(times)):
        date = times[i].utc_iso().split('T')[0]
        angle = angles_from_full_moon[i]
        irradiance = scaled_irradiance[i]
        fraction = illumination_fractions[i]
        file.write(f"{date} | {angle:.2f} | {irradiance:.5f} | {fraction:.5%}\n")

print(f"Results saved to {output_file}")
print (unit22)

# '/Users/diegomateos/Downloads/lunar_irradiance_results.txt'