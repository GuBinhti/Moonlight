from flask import Flask, jsonify, send_from_directory, request
import threading, datetime, os, time
import matplotlib
matplotlib.use("Agg")

from simulator import (
    calculate_moonrise_times,
    plot_moon_schedule_times,
    plot_moon_schedule_phases,
    plot_moon_phase_angle,
    plot_hourly_altitude,
    simulation_loop,
    find_first_day_with_phase
)

app = Flask(__name__)
OUTPUT_DIR = "static/plots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

state = {
    "user_cycle_length": 28,
    "speed_factor": 1.0,
    "day_length_in_real_seconds": 86400,   # 24 h sim‑day in real seconds
    "hex_color": "FF0000",
    "feed_start_time": "19:00",
    "feed_end_time":   "04:00",
    "start_phase": "New Moon",             
    "start_time":  "00:00",                

    "cycle_start_date": datetime.datetime.now(),
    "moon_schedule": calculate_moonrise_times(28),

    "simulation_started": False,
    "simulation_thread": None,
    "stop_event": None,

    "sim_time": None,
    "progress": 0.0,
    "current_phase": "N/A",
    "current_phase_angle": 0.0,
    "current_altitude": 0.0,
}

def _timestamp(): return str(int(time.time()))
def _save_plot(fname):
    import matplotlib.pyplot as plt
    path = os.path.join(OUTPUT_DIR, fname)
    plt.savefig(path)
    plt.close()
    return f"/plots/{fname}"

@app.route("/")
def home():
    return send_from_directory("static", "index.html")

@app.route("/plots/<path:filename>")
def serve_plot(filename):
    return send_from_directory(OUTPUT_DIR, filename)

@app.route("/start-simulation")
def start_sim():
    if state["simulation_started"]:
        return jsonify({"message": "Simulation already running."})

    # reset start‑of‑cycle marker & stop_event
    state["cycle_start_date"] = datetime.datetime.now()
    state["stop_event"]       = threading.Event()

    # -------- translate desired phase/time to a concrete datetime ----------
    phase = state["start_phase"]
    try:
        hh, mm = (int(x) for x in state["start_time"].split(":"))
        start_clock = datetime.time(hh, mm)
    except Exception:
        start_clock = datetime.time(0, 0)

    # day‑offset of requested phase
    day_offset = find_first_day_with_phase(state["moon_schedule"], phase)
    sim_start_dt = state["cycle_start_date"] + datetime.timedelta(days=day_offset)
    sim_start_dt = sim_start_dt.replace(hour=start_clock.hour,
                                        minute=start_clock.minute)

    # --------------------- launch background thread ------------------------
    t = threading.Thread(
        target=simulation_loop,
        args=(
            state["moon_schedule"],
            state["cycle_start_date"],
            state["user_cycle_length"],
            1,                               # update_interval_minutes
            state["speed_factor"],
            state["day_length_in_real_seconds"],
            state["hex_color"],
            state["feed_start_time"],
            state["feed_end_time"],
            state["stop_event"],
            state,                           # shared_state
            sim_start_dt                 
        ),
        daemon=True
    )
    t.start()
    state["simulation_thread"] = t
    state["simulation_started"] = True
    return jsonify({"message": "Simulation started!"})

@app.route("/end-simulation")
def end_sim():
    if not state["simulation_started"]:
        return jsonify({"message": "Simulation was not running."})
    state["stop_event"].set()
    state["simulation_started"] = False
    return jsonify({"message": "Simulation ending…"})

# ---- Plots -----------------------------------------------------------------
@app.route("/plot-phase-angle")
def plot_phase():
    plot_moon_phase_angle(state["moon_schedule"])
    return jsonify({"image": _save_plot(f"phase_angle_{_timestamp()}.png")})

@app.route("/plot-rise-set")
def plot_rs():
    plot_moon_schedule_times(state["moon_schedule"])
    return jsonify({"image": _save_plot(f"rise_set_{_timestamp()}.png")})

@app.route("/plot-phases")
def plot_phs():
    plot_moon_schedule_phases(state["moon_schedule"])
    return jsonify({"image": _save_plot(f"phases_{_timestamp()}.png")})

@app.route("/plot-altitude", methods=["POST"])
def plot_alt():
    idx = int((request.get_json() or {}).get("day", 0))
    if 0 <= idx < len(state["moon_schedule"]):
        plot_hourly_altitude(state["moon_schedule"][idx],
                             state["cycle_start_date"], 30)
        return jsonify({"image": _save_plot(f"altitude_day{idx}_{_timestamp()}.png")})
    return jsonify({"error": "Invalid day index"}), 400

# ---- Settings --------------------------------------------------------------
@app.route("/change-settings", methods=["POST"])
def change_settings():
    d = request.get_json() or {}

    state["user_cycle_length"]            = d.get("cycle_length")    or state["user_cycle_length"]
    state["hex_color"]                    = d.get("hex_color")       or state["hex_color"]
    state["feed_start_time"]              = d.get("feed_start_time") or state["feed_start_time"]
    state["feed_end_time"]                = d.get("feed_end_time")   or state["feed_end_time"]
    state["start_phase"]                  = d.get("start_phase")     or state["start_phase"]
    state["start_time"]                   = d.get("start_time")      or state["start_time"]
    state["day_length_in_real_seconds"]   = d.get("day_length")      or state["day_length_in_real_seconds"]

    # recompute lunar schedule if cycle length changed
    state["moon_schedule"]    = calculate_moonrise_times(state["user_cycle_length"])
    state["cycle_start_date"] = datetime.datetime.now()

    return jsonify({"message": "Settings updated successfully!"})

# ---- Live status -----------------------------------------------------------
@app.route("/status")
def status():
    # format simulated clock
    if state["sim_time"]:
        delta = state["sim_time"] - state["cycle_start_date"]
        dd = delta.days
        hh, rem = divmod(delta.seconds, 3600)
        mm, ss = divmod(rem, 60)
        sim_str = f"{dd:02}:{hh:02}:{mm:02}:{ss:02}"
    else:
        sim_str = "--:--:--:--"

    return jsonify({
        "Simulation Started": state["simulation_started"],
        "Sim Time":           sim_str,
        "Progress (%)":       round(state.get("progress", 0.0), 2),
        "Phase":              state.get("current_phase"),
        "Phase Angle":        round(state.get("current_phase_angle", 0.0), 2),
        "Altitude (deg)":     round(state.get("current_altitude", 0.0), 1),
        "Cycle Length":       state["user_cycle_length"],
        "Hex Color":          state["hex_color"],
        "Day Length (s)":     state["day_length_in_real_seconds"],
        "Start Phase":        state["start_phase"],
        "Start Time":         state["start_time"],
    })

# ---- main ------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
