import numpy as np
import matplotlib.pyplot as plt
from skyfield.api import Loader, Topos
from skyfield.almanac import moon_phase

# Load data
load = Loader('~/skyfield-data')
ts = load.timescale()
eph = load('de421.bsp')

# Isla Vista coordinates
latitude = 34.4133
longitude = -119.8610
location = Topos(latitude_degrees=latitude, longitude_degrees=longitude)

# Specify the date and time for which you want the moon phase
date = ts.utc(2022, 7, 22, 20)  # Year, Month, Day, Hour (24h format, UTC time)

# Calculate the moon phase
phase = moon_phase(eph, date)
phase_degrees = phase.degrees

# Interpret the moon phase
if phase_degrees < 90:
    description = 'New Moon'
    shadow_angle = phase_degrees
    shadow_offset = 1  # The offset for the crescent shadow
elif phase_degrees < 180:
    description = 'First Quarter'
    shadow_angle = phase_degrees - 90
    shadow_offset = 1  # The offset for the crescent shadow
elif phase_degrees < 270:
    description = 'Full Moon'
    shadow_angle = 0
    shadow_offset = 0  # No shadow
else:
    description = 'Last Quarter'
    shadow_angle = phase_degrees - 270
    shadow_offset = 1  # The offset for the crescent shadow

# Print the moon phase information
print(f'Moon phase: {phase_degrees:.2f} degrees, which is approximately {description}.')

# Plot the moon phase
fig, ax = plt.subplots(figsize=(6, 6))
fig.patch.set_facecolor('white')
ax.set_xlim(-1.5, 1.5)
ax.set_ylim(-1.5, 1.5)
ax.set_aspect('equal')
ax.axis('off')  # Turn off the axis

# Draw the full moon (black circle)
full_moon = plt.Circle((0, 0), 1, color='white')
ax.add_artist(full_moon)

# Draw the shadow based on the phase
if description == 'New Moon':
    # Do nothing should be completely dark
    pass
elif description in ['First Quarter', 'Last Quarter']:
    # Draw the shadow for First and Last Quarter
    shadow_circle = plt.Circle((-shadow_offset * np.cos(np.radians(90 - shadow_angle)),
                                 -shadow_offset * np.sin(np.radians(90 - shadow_angle))),
                                 1, color='grey')
    ax.add_artist(shadow_circle)
else:
    # For gibbous phases, draw the shadow to the right
    shadow_circle = plt.Circle((-shadow_offset * np.cos(np.radians(shadow_angle)),
                                 -shadow_offset * np.sin(np.radians(shadow_angle))),
                                 1, color='grey')
    ax.add_artist(shadow_circle)

# Customize the plot title
ax.set_title(f'Moon Phase: {description} ({phase_degrees:.2f}°)', va='bottom', color = 'black')

# Show the plot
plt.show()
