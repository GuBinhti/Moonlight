from flask import Flask, jsonify, send_from_directory, request
import threading
import os
import datetime

# Import your full moonlight simulator here
from simulator import calculate_moonrise_times, plot_moon_schedule_times, plot_moon_schedule_phases
from simulator import plot_moon_phase_angle, plot_hourly_altitude, simulation_loop, handle_command

app = Flask(__name__)
OUTPUT_DIR = 'static/plots'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Global simulation state
state = {
    'moon_schedule': calculate_moonrise_times(28),
    'cycle_start_date': datetime.datetime.now(),
    'user_cycle_length': 28,
    'speed_factor': 1.0,
    'day_length_in_real_seconds': 86400,
    'hex_color': 'FF0000',
    'simulation_started': False,
    'simulation_thread': None,
}

stop_event = threading.Event()

@app.route('/')
def home():
    return send_from_directory('static', 'index.html')

@app.route('/start-simulation')
def start_simulation():
    if not state['simulation_started']:
        state['simulation_started'] = True
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
                stop_event
            ),
            daemon=True
        )
        sim_thread.start()
        state['simulation_thread'] = sim_thread
        return jsonify({'message': 'Simulation started!'})
    else:
        return jsonify({'message': 'Simulation already running.'})

@app.route('/plot-phase-angle')
def plot_phase_angle():
    plot_moon_phase_angle(state['moon_schedule'])
    filepath = os.path.join(OUTPUT_DIR, 'phase_angle.png')
    # Save plot
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

@app.route('/plots/<filename>')
def serve_plot(filename):
    return send_from_directory(OUTPUT_DIR, filename)

@app.route('/status')
def status():
    return jsonify({
        'Cycle Length': state['user_cycle_length'],
        'Speed Factor': state['speed_factor'],
        'Day Length (s)': state['day_length_in_real_seconds'],
        'Hex Color': state['hex_color'],
        'Simulation Started': state['simulation_started'],
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
