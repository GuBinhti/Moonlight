from flask import Flask, jsonify, send_from_directory, request
import threading, datetime, os, time
import matplotlib
matplotlib.use("Agg") 

from simulator import (
    calculate_moonrise_times, plot_moon_schedule_times,
    plot_moon_schedule_phases, plot_moon_phase_angle,
    plot_hourly_altitude, simulation_loop
)

app = Flask(__name__)
OUTPUT_DIR = "static/plots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

state = {
    # configuration
    "user_cycle_length": 28,
    "speed_factor": 1.0,
    "day_length_in_real_seconds": 86400,
    "hex_color": "FF0000",
    "feed_start_time": "19:00",
    "feed_end_time": "04:00",
    # derived
    "cycle_start_date": datetime.datetime.now(),
    "moon_schedule": calculate_moonrise_times(28),
    # runtime
    "simulation_started": False,
    "simulation_thread": None,
    "stop_event": None,
    # live metrics (populated by simulation_loop)
    "sim_time": None,
    "progress": 0.0,
    "current_phase": "N/A",
    "current_phase_angle": 0.0,
    "current_altitude": 0.0,
}

# ────────────────────────── HELPERS ─────────────────────────────
def _timestamp() -> str:
    return str(int(time.time()))

def _save_current_plot(fname):
    path = os.path.join(OUTPUT_DIR, fname)
    import matplotlib.pyplot as plt
    plt.savefig(path)
    plt.close()
    return f"/plots/{fname}"

# ─────────────────────────  ROUTES  ─────────────────────────────
@app.route("/")
def home():
    return send_from_directory("static", "index.html")

@app.route("/plots/<path:filename>")
def serve_plot(filename):
    return send_from_directory(OUTPUT_DIR, filename)

# ---------- Simulation control ----------
@app.route("/start-simulation")
def start_simulation():
    if state["simulation_started"]:
        return jsonify({"message": "Simulation already running."})

    print("[Server] Starting simulation…")
    state["cycle_start_date"] = datetime.datetime.now()
    state["stop_event"] = threading.Event()

    sim_thread = threading.Thread(
        target=simulation_loop,
        args=(
            state["moon_schedule"],
            state["cycle_start_date"],
            state["user_cycle_length"],
            1,                      # update interval (min)
            state["speed_factor"],
            state["day_length_in_real_seconds"],
            state["hex_color"],
            state["feed_start_time"],
            state["feed_end_time"],
            state["stop_event"],
            state                   #  ← shared dict
        ),
        daemon=True
    )
    sim_thread.start()
    state["simulation_thread"] = sim_thread
    state["simulation_started"] = True

    return jsonify({"message": "Simulation started!"})

@app.route("/end-simulation")
def end_simulation():
    if not state["simulation_started"]:
        return jsonify({"message": "Simulation was not running."})

    print("[Server] Stopping simulation…")
    state["stop_event"].set()
    state["simulation_started"] = False
    return jsonify({"message": "Simulation ending…"})

# ---------- Plots ----------
@app.route("/plot-phase-angle")
def plot_phase_angle():
    plot_moon_phase_angle(state["moon_schedule"])
    img = _save_current_plot(f"phase_angle_{_timestamp()}.png")
    return jsonify({"image": img})

@app.route("/plot-rise-set")
def plot_rise_set():
    plot_moon_schedule_times(state["moon_schedule"])
    img = _save_current_plot(f"rise_set_{_timestamp()}.png")
    return jsonify({"image": img})

@app.route("/plot-phases")
def plot_phases():
    plot_moon_schedule_phases(state["moon_schedule"])
    img = _save_current_plot(f"phases_{_timestamp()}.png")
    return jsonify({"image": img})

@app.route("/plot-altitude", methods=["POST"])
def plot_altitude():
    data = request.get_json() or {}
    try:
        idx = int(data.get("day", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid day index"}), 400

    if 0 <= idx < len(state["moon_schedule"]):
        plot_hourly_altitude(state["moon_schedule"][idx],
                             state["cycle_start_date"],
                             marker_interval=30)
        img = _save_current_plot(f"altitude_day{idx}_{_timestamp()}.png")
        return jsonify({"image": img})
    return jsonify({"error": "Invalid day index"}), 400

@app.route("/change-settings", methods=["POST"])
def change_settings():
    data = request.get_json() or {}

    state["user_cycle_length"] = data.get("cycle_length") or state["user_cycle_length"]
    state["hex_color"]         = data.get("hex_color")   or state["hex_color"]
    state["feed_start_time"]   = data.get("feed_start_time") or state["feed_start_time"]
    state["feed_end_time"]     = data.get("feed_end_time")   or state["feed_end_time"]

    state["moon_schedule"]   = calculate_moonrise_times(state["user_cycle_length"])
    state["cycle_start_date"] = datetime.datetime.now()

    return jsonify({"message": "Settings updated successfully!"})

@app.route("/status")
def status():
    if state["sim_time"]:
        delta = state["sim_time"] - state["cycle_start_date"]
        dd = delta.days
        hh, rem = divmod(delta.seconds, 3600)
        mm, ss = divmod(rem, 60)
        sim_time_str = f"{dd:02}:{hh:02}:{mm:02}:{ss:02}"
    else:
        sim_time_str = "--:--:--:--"

    return jsonify({
        "Simulation Started": state["simulation_started"],
        "Sim Time":           sim_time_str,
        "Progress (%)":       round(state.get("progress", 0.0), 2),
        "Phase":              state.get("current_phase", "N/A"),
        "Phase Angle":        round(state.get("current_phase_angle", 0.0), 2),
        "Altitude (deg)":     round(state.get("current_altitude", 0.0), 1),
        # config (for completeness)
        "Cycle Length": state["user_cycle_length"],
        "Hex Color":    state["hex_color"],
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
