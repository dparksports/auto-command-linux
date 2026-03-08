"""Auto Command — Flask application entry point with SocketIO."""
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import config
from monitors.performance import PerformanceMonitor
from monitors.devices import DeviceMonitor
from monitors.security import SecurityMonitor
from monitors.connections import ConnectionMonitor
from monitors.enforcer import SecurityEnforcer
from services.system_info import get_system_info
from services.whois_cache import WhoisCache
from services import firewall as firewall_svc
from services import gemini_client
from services import systemd_svc

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")

# Initialize monitors
perf_monitor = PerformanceMonitor()
whois_cache = WhoisCache()
device_monitor = DeviceMonitor(socketio)
security_monitor = SecurityMonitor(socketio)
connection_monitor = ConnectionMonitor(socketio, whois_cache)
enforcer = SecurityEnforcer(socketio)


# ── Routes ───────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    sys_info = get_system_info()
    return render_template("dashboard.html", sys_info=sys_info, page="dashboard")


@app.route("/security")
def security():
    return render_template("security.html", page="security")


@app.route("/devices")
def devices():
    return render_template("devices.html", page="devices")


@app.route("/connections")
def connections():
    return render_template("connections.html", page="connections")


@app.route("/firewall")
def firewall_page():
    return render_template("firewall.html", page="firewall")


@app.route("/services_page")
def services_page():
    return render_template("services.html", page="services")


@app.route("/settings")
def settings():
    return render_template("settings.html", page="settings")


# ── API Endpoints ────────────────────────────────────────────────────────

@app.route("/api/metrics")
def api_metrics():
    return jsonify(perf_monitor.get_metrics())


@app.route("/api/system-info")
def api_system_info():
    return jsonify(get_system_info())


@app.route("/api/security-events")
def api_security_events():
    return jsonify(security_monitor.get_events())


@app.route("/api/device-events")
def api_device_events():
    return jsonify(device_monitor.get_events())


@app.route("/api/network-adapters")
def api_network_adapters():
    return jsonify(device_monitor.get_network_adapters())


@app.route("/api/connections")
def api_connections():
    return jsonify(connection_monitor.get_active_connections())


@app.route("/api/connection-history")
def api_connection_history():
    return jsonify(connection_monitor.get_history())


@app.route("/api/firewall")
def api_firewall():
    return jsonify(firewall_svc.get_firewall_status())


@app.route("/api/firewall/drift")
def api_firewall_drift():
    return jsonify(firewall_svc.check_drift())


@app.route("/api/firewall/snapshot", methods=["POST"])
def api_firewall_snapshot():
    return jsonify(firewall_svc.save_snapshot())


@app.route("/api/enforcer/alerts")
def api_enforcer_alerts():
    return jsonify(enforcer.get_alerts())


@app.route("/api/services")
def api_services():
    return jsonify(systemd_svc.get_services())


@app.route("/api/ai/analyze", methods=["POST"])
def api_ai_analyze():
    data = request.get_json()
    description = data.get("description", "")
    if not description:
        return jsonify({"error": "No description provided"}), 400
    return jsonify(gemini_client.analyze_threat(description))


# ── SocketIO Background Task ────────────────────────────────────────────

def emit_metrics():
    """Background thread that pushes performance metrics every second."""
    while True:
        try:
            metrics = perf_monitor.get_metrics()
            socketio.emit("metrics", metrics)
        except Exception as e:
            print(f"Metrics emit error: {e}")
        eventlet.sleep(config.PERF_INTERVAL)


@socketio.on("connect")
def handle_connect():
    print("Client connected")


@socketio.on("disconnect")
def handle_disconnect():
    print("Client disconnected")


# ── Start ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Start background monitors
    socketio.start_background_task(emit_metrics)
    device_monitor.start()
    security_monitor.start()
    connection_monitor.start(interval=config.CONNECTION_REFRESH_INTERVAL)
    enforcer.start()

    print(f"\n  Auto Command running at http://localhost:{config.PORT}\n")
    socketio.run(app, host=config.HOST, port=config.PORT, debug=config.DEBUG,
                 use_reloader=False, log_output=True)
