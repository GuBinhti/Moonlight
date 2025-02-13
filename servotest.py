from skyfield.api import load, Topos
from datetime import datetime, timedelta
import RPi.GPIO as GPIO
import time
#import datetime

servo_pin = 24
def setup_servo(pin):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.OUT)
    

    # Using frequency 50 Hz
    pwm = GPIO.PWM(pin, 50)
    pwm.start(0) 
    return pwm


def set_servo_angle(pwm, angle):
    duty_cycle = (500 + 1500(angle)/20000)*100  # Map angle to servo range (2% to 12%)
    pwm.ChangeDutyCycle(duty_cycle)
    time.sleep(0.5)  # Allow the servo to reach the position
    pwm.ChangeDutyCycle(0)  # Stop sending signal to prevent jitter


def moon_placement_azimuth(year, month, day, hour, minute, second, pwm):
    planets = load('/home/moonlight/skyfield-data/de421.bsp')
    ts = load.timescale()
    local_time = datetime(year, month, day, hour, minute, second)

    # Convert local time to UTC (adjust for your timezone offset, if any)
    utc_time = local_time + timedelta(minutes=0)  # Adjust this based on your timezone
    t = ts.utc(utc_time.year, utc_time.month, utc_time.day, utc_time.hour, utc_time.minute, utc_time.second)

    # Observation location (latitude and longitude)
    latitude = 0
    longitude = -119.8610
    location = Topos(latitude_degrees=latitude, longitude_degrees=longitude)

    moon = planets['moon']
    earth = planets['earth']

    astrometric = earth + location



    # Compute azimuth for 28 days
    i = 0
    while True:
        i += 1
        current_time = local_time + timedelta(minutes=2*(i))
        utc_time = current_time
        t = ts.utc(utc_time.year, utc_time.month, utc_time.day, utc_time.hour, utc_time.minute, utc_time.second)

        # Calculate the position of the Moon relative to the given location on Earth
        moon_position = astrometric.at(t).observe(moon).apparent()
        alt,_, _ = moon_position.altaz()
        altitude = alt.degrees
        zenith_angle = 90 - altitude

        # Print the azimuth data
        print(f"Time: {current_time:} Zenith = {zenith_angle:.2f}°")

        # Adjust the servo to the azimuth angle
        angle_percent = (min(180, zenith_angle))/180
        print(f"Angle Percent: {angle_percent:}")
        servo_angle = max(0, angle_percent) # Clamp azimuth to servo's range (0° to 180°)
        set_servo_angle(pwm, servo_angle)
        time.sleep(1)  # Wait for 1 second before the next adjustment




try:
    servo_pwm = setup_servo(servo_pin)
    set_servo_angle(servo_pwm, 0)
    print("Enter date and time:\n")
    year = int(input("Year: "))
    month = int(input("Month: "))
    day = int(input("Day: "))
    hour = int(input("Hour: "))
    minute = int(input("Minute: "))
    second = int(input("Seconds: "))

    # Set up the servo
    #servo_pwm = setup_servo(servo_pin)

    # Run the Moon azimuth function
    moon_placement_azimuth(year, month, day, hour, minute, second, servo_pwm)
    print

finally:
    # Clean up GPIO resources
    servo_pwm.stop()
    GPIO.cleanup()
