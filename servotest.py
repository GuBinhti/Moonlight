from skyfield.api import load, wgs84
from datetime import datetime, timedelta
import RPi.GPIO as GPIO
import time
import math

servo_pin = 24

def setup_servo(pin):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.OUT)
    pwm = GPIO.PWM(pin, 50)
    pwm.start(0)
    return pwm

def set_servo_angle(pwm, angle):
    duty_cycle = ((angle / 180) * 10) + 2.5  # Maps 0°-180° to 2.5%-12.5% duty cycle
    pwm.ChangeDutyCycle(duty_cycle)
    time.sleep(0.5)
    pwm.ChangeDutyCycle(0)

def moon_placement_azimuth(year, month, day, hour, minute, second, pwm):
    planets = load('/home/moonlight/skyfield-data/de421.bsp')
    ts = load.timescale()
    local_time = datetime(year, month, day, hour, minute, second)
    utc_time = local_time
    t = ts.utc(utc_time.year, utc_time.month, utc_time.day, utc_time.hour, utc_time.minute, utc_time.second)

    latitude = 0
    longitude = -119.8610
    location = wgs84.latlon(latitude, longitude)

    moon = planets['moon']
    earth = planets['earth']
    astrometric = earth + location
    next_print_time = local_time + timedelta(seconds=5)

    while True:
        local_time += timedelta(seconds=1)
        t = ts.utc(local_time.year, local_time.month, local_time.day, local_time.hour, local_time.minute, local_time.second)

        moon_position = astrometric.at(t).observe(moon).apparent()
        alt, _, _ = moon_position.altaz()
        altitude = alt.degrees
        zenith_angle = 90 - altitude
        zen = math.floor(zenith_angle)

        if local_time >= next_print_time:
            print(f"Time: {local_time} | Zenith = {zenith_angle:.2f}°")
            print(f"Altitude = {altitude:.2f}°")
            angle_percent = min(180, zen) / 180
            print(f"Angle Percent: {angle_percent:.2f}\n")
            servo_angle = max(0, angle_percent * 180)
            set_servo_angle(pwm, servo_angle)
            next_print_time += timedelta(seconds=5)

        time.sleep(1)

if __name__ == '__main__':
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

        moon_placement_azimuth(year, month, day, hour, minute, second, servo_pwm)

    finally:
        servo_pwm.stop()
        GPIO.cleanup()
