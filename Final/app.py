from flask import Flask, jsonify, send_from_directory, request
import threading
import os
import datetime

# Import your full simulator code
from simulator import calculate_moonrise_times, plot_moon_schedule_times, plot_moon_schedule_phases
from simulator import plot_moon_phase_angle, plot_hourly_altitude, simulation_loop

app = Flask(__name__)
OUTPUT_DIR = 'static/plots'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# State to track simulation parameters
state = {
    'moon_schedule': calculate_moonrise_times(28),
    'cycle_start_date': datetime.datetime.now(),
    'user_cycle_length': 28,
    'speed_factor': 1.0,
    'day_length_in_real_seconds': 86400,
    'hex_color': 'FF0000',
    'feed_start_time': '19:00',
    'feed_end_time': '04:00',
    'feed_end_real_time': None,  # backup
    'simulation_started': False,
    'simulation_thread': None,
    'stop_event': None,
}

@app.route('/')
def home():
    return send_from_directory('static', 'index.html')

@app.route('/start-simulation')
def start_simulation():
    if not state['simulation_started']:
        print("[Server] Starting simulation...")

        state['cycle_start_date'] = datetime.datetime.now()
        state['feed_end_real_time'] = state['cycle_start_date'] + datetime.timedelta(days=state['user_cycle_length'])

        stop_event = threading.Event()
        state['stop_event'] = stop_event

        sim_thread = threading.Thread(
            target=simulation_loop,
            args=(
                state['moon_schedule'],
                state['cycle_start_date'],
                state['user_cycle_length'],
                1,  # update_interval_minutes
                state['speed_factor'],
                state['day_length_in_real_seconds'],
                state['hex_color'],
                state['feed_start_time'],
                state['feed_end_time'],
                stop_event
            ),
            daemon=True
        )
        sim_thread.start()

        state['simulation_thread'] = sim_thread
        state['simulation_started'] = True

        return jsonify({'message': 'Simulation started!'})
    else:
        return jsonify({'message': 'Simulation already running.'})

@app.route('/end-simulation')
def end_simulation():
    if state['simulation_started']:
        if state['stop_event'] is not None:
            print("[Server] Stopping simulation...")
            state['stop_event'].set()
        state['simulation_started'] = False
        return jsonify({'message': 'Simulation ending...'})
    else:
        return jsonify({'message': 'Simulation was not running.'})

@app.route('/plot-phase-angle')
def plot_phase_angle():
    plot_moon_phase_angle(state['moon_schedule'])
    filepath = os.path.join(OUTPUT_DIR, 'phase_angle.png')
    import matplotlib.pyplot as plt
    plt.savefig(filepath)
    plt.close()
    return jsonify({'image': f'/plots/phase_angle.png'})

@app.route('/plot-rise-set')
def plot_rise_set():
    plot_moon_schedule_times(state['moon_schedule'])
    filepath = os.path.join(OUTPUT_DIR, 'rise_set.png')
    import matplotlib.pyplot as plt
    plt.savefig(filepath)
    plt.close()
    return jsonify({'image': f'/plots/rise_set.png'})

@app.route('/plot-phases')
def plot_phases():
    plot_moon_schedule_phases(state['moon_schedule'])
    filepath = os.path.join(OUTPUT_DIR, 'phases.png')
    import matplotlib.pyplot as plt
    plt.savefig(filepath)
    plt.close()
    return jsonify({'image': f'/plots/phases.png'})

@app.route('/plot-altitude', methods=['POST'])
def plot_altitude():
    data = request.get_json()
    day_idx = data.get('day', 0)
    if 0 <= day_idx < len(state['moon_schedule']):
        plot_hourly_altitude(state['moon_schedule'][day_idx], state['cycle_start_date'], marker_interval=30)
        filepath = os.path.join(OUTPUT_DIR, f'altitude_day{day_idx}.png')
        import matplotlib.pyplot as plt
        plt.savefig(filepath)
        plt.close()
        return jsonify({'image': f'/plots/altitude_day{day_idx}.png'})
    else:
        return jsonify({'error': 'Invalid day index'}), 400

@app.route('/change-settings', methods=['POST'])
def change_settings():
    data = request.get_json()
    cycle_length = data.get('cycle_length')
    speed_factor = data.get('speed_factor')
    day_length = data.get('day_length')
    hex_color = data.get('hex_color')
    feed_start = data.get('feed_start_time')
    feed_end = data.get('feed_end_time')

    if cycle_length:
        state['user_cycle_length'] = cycle_length
    if speed_factor:
        state['speed_factor'] = speed_factor
    if day_length:
        state['day_length_in_real_seconds'] = day_length
    if hex_color:
        state['hex_color'] = hex_color
    if feed_start:
        state['feed_start_time'] = feed_start
    if feed_end:
        state['feed_end_time'] = feed_end

    # Update moon schedule
    state['moon_schedule'] = calculate_moonrise_times(state['user_cycle_length'])
    state['cycle_start_date'] = datetime.datetime.now()
    state['feed_end_real_time'] = state['cycle_start_date'] + datetime.timedelta(days=state['user_cycle_length'])

    return jsonify({'message': 'Settings updated successfully!'})

@app.route('/status')
def status():
    return jsonify({
        'Cycle Length': state['user_cycle_length'],
        'Speed Factor': state['speed_factor'],
        'Day Length (s)': state['day_length_in_real_seconds'],
        'Hex Color': state['hex_color'],
        'Feed Start Time': state['feed_start_time'],
        'Feed End Time': state['feed_end_time'],
        'Simulation Started': state['simulation_started'],
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
