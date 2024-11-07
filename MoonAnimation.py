from skyfield.api import load, Topos
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
from matplotlib.offsetbox import OffsetImage, AnnotationBbox


def moon_placement(year, month, day, hour, minute, second):
    planets = load('/Users/diegomateos/Downloads/de421.bsp')
    ts = load.timescale()
    local_time = datetime(year, month, day, hour, minute, second)

    # Convert local time to UTC (add 7 hours for PDT)
    # Since we are picking a date/time on "PDT," we need to convert our "PDT" time into UTC.
    # Therefore, we add 7 hours before daylight savings (PDT), 8 after but might not be necessary.
    # If we are considering the Caribbean, we will add 4 or 5 (might not matter which).
    pdt_time = local_time + timedelta(hours=0)
    t = ts.utc(pdt_time.year, pdt_time.month, pdt_time.day, pdt_time.hour, pdt_time.minute, pdt_time.second)

    # IV Coordinates
    latitude = 34.4133
    longitude = -119.8610
    location = Topos(latitude_degrees=latitude, longitude_degrees=longitude)

    moon = planets['moon']
    earth = planets['earth']

    # position of the Moon relative to the given location
    astrometric = earth + location

    dates = []
    altitudes = []

    for i in range(24):
        local_time = datetime(year, month, day, hour, minute, second) + timedelta(hours=i)
        pdt_time = local_time + timedelta(hours=0)
        t = ts.utc(pdt_time.year, pdt_time.month, pdt_time.day, pdt_time.hour, pdt_time.minute, pdt_time.second)

        # Calculate the position of the Moon relative to the given location on Earth
        moon_position = astrometric.at(t).observe(moon).apparent()
        alt, az, _ = moon_position.altaz()


        dates.append(t.utc_strftime('%H'))
        altitudes.append(alt.degrees)

    fig, ax = plt.subplots()
    ax.set_xlim(0, 24)
    ax.set_ylim(-90, 90)


    line, = ax.plot([], [], marker='', color='blue')  # Initial empty plot

    # List to store existing annotation artists (markers) for removal
    annotations = []

    def animate(i):
        def getImage(path):
            return OffsetImage(plt.imread(path, format="jpeg"), zoom=.07)
        image_path = 'moonpic.jpeg'
        # Update the line data
        line.set_data(np.arange(i + 1), altitudes[:i + 1])

        # used to only print 1 image a time, comment out if you want an image for all points
        if annotations:
            annotations[0].remove()

        ab = AnnotationBbox(getImage(image_path), (i, altitudes[i]), frameon=False)
        ax.add_artist(ab)
        annotations.clear()
        annotations.append(ab)  # Store the current annotation
        return line,

    ani = animation.FuncAnimation(fig, animate, frames=len(altitudes), interval=10000, repeat=False)

    ax.set_title('Moon Altitude over a Full Day', fontsize=16)
    ax.set_xlabel('Hour', fontsize=14)
    ax.set_ylabel('Moon Altitude (degrees)', fontsize=14)

    plt.xticks(np.arange(0, 24, 1), labels=dates[::1], rotation=45)  # Only show a subset of dates for clarity
    plt.axhline(y=0, color='gray', linestyle='--', label='Horizon')
    plt.grid()
    plt.legend()
    plt.tight_layout()

    writer = animation.PillowWriter(fps=0.2, metadata=dict(artist='Me'), bitrate=2400) # 0.5,
    # 1 frame per 5 seconds, each day is updated every 5 seconds
    ani.save('moon_altitude_animation.gif', writer=writer)

    plt.show()


print("Enter data and time:\n")
year = int(input("Year: "))
month = int(input("Month: "))
day = int(input("Day: "))
hour = int(input("Hour: "))
minute = int(input("Minute: "))
second = int(input("Seconds: "))

moon_placement(year, month, day, hour, minute, second)
