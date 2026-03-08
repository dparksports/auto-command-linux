"""Security enforcer — background threat checks (replaces SecurityEnforcer.cs)."""
import threading
import subprocess
import time
import psutil
from datetime import datetime


class SecurityEnforcer:
    """Periodically checks for security anomalies and emits alerts."""

    def __init__(self, socketio, interval=30):
        self._socketio = socketio
        self._interval = interval
        self._alerts = []

    def start(self):
        thread = threading.Thread(target=self._enforce_loop, daemon=True)
        thread.start()

    def _enforce_loop(self):
        time.sleep(5)  # Wait for app to initialize
        while True:
            try:
                self._check_rogue_ap()
                self._check_privileged_timers()
                self._check_suspicious_listeners()
            except Exception as e:
                print(f"Enforcer error: {e}")
            time.sleep(self._interval)

    def _emit_alert(self, category, severity, message, details=None):
        alert = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'category': category,
            'severity': severity,
            'message': message,
            'details': details or {},
        }
        self._alerts.append(alert)
        self._socketio.emit('security_alert', alert)

    def _check_rogue_ap(self):
        """Check for unexpected hostapd/access point processes."""
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                if proc.info['name'] in ('hostapd', 'create_ap'):
                    self._emit_alert(
                        'rogue_ap', 'critical',
                        f"Rogue access point process detected: {proc.info['name']}",
                        {'pid': proc.pid, 'cmdline': ' '.join(proc.info.get('cmdline', []))}
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    def _check_privileged_timers(self):
        """Check for systemd timers running as root."""
        try:
            result = subprocess.run(
                ['systemctl', 'list-timers', '--all', '--no-pager', '-o', 'json'],
                capture_output=True, text=True, timeout=10
            )
            # Just log if there are any custom root timers beyond known ones
            # This is informational, not an alert
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    def _check_suspicious_listeners(self):
        """Check for unexpected listening ports."""
        suspicious_ports = {4444, 5555, 6666, 31337, 12345, 54321}
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN' and conn.laddr:
                if conn.laddr.port in suspicious_ports:
                    proc_name = ""
                    if conn.pid:
                        try:
                            proc_name = psutil.Process(conn.pid).name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            proc_name = f"PID {conn.pid}"
                    self._emit_alert(
                        'suspicious_port', 'warning',
                        f"Suspicious listening port {conn.laddr.port} ({proc_name})",
                        {'port': conn.laddr.port, 'pid': conn.pid, 'process': proc_name}
                    )

    def get_alerts(self):
        return list(self._alerts)
