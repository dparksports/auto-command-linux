"""Connection monitor — replaces IpHlpApi P/Invoke with psutil.net_connections."""
import psutil
import threading
import time
from datetime import datetime
from collections import deque


class ConnectionMonitor:
    """Tracks active TCP/UDP connections with process resolution."""

    def __init__(self, socketio, whois_cache=None):
        self._socketio = socketio
        self._whois = whois_cache
        self._history = deque(maxlen=500)
        self._lock = threading.Lock()
        self._prev_connections = set()

    def start(self, interval=3):
        """Start periodic connection scanning."""
        thread = threading.Thread(target=self._scan_loop, args=(interval,), daemon=True)
        thread.start()

    def _scan_loop(self, interval):
        """Periodically scan connections and detect changes."""
        while True:
            try:
                current = self.get_active_connections()
                current_set = {
                    (c['protocol'], c['local_addr'], c['remote_addr'])
                    for c in current if c['remote_addr']
                }

                # Detect new connections
                new_conns = current_set - self._prev_connections
                if new_conns:
                    for conn in current:
                        key = (conn['protocol'], conn['local_addr'], conn['remote_addr'])
                        if key in new_conns and conn['remote_addr']:
                            event = {
                                **conn,
                                'event': 'opened',
                                'event_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            }
                            with self._lock:
                                self._history.appendleft(event)
                            self._socketio.emit('connection_event', event)

                # Detect closed connections
                closed_conns = self._prev_connections - current_set
                for proto, local, remote in closed_conns:
                    event = {
                        'protocol': proto,
                        'local_addr': local,
                        'remote_addr': remote,
                        'event': 'closed',
                        'event_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    }
                    with self._lock:
                        self._history.appendleft(event)

                self._prev_connections = current_set
                self._socketio.emit('connections_update', current)

            except Exception as e:
                print(f"Connection monitor error: {e}")

            time.sleep(interval)

    def get_active_connections(self):
        """Get all active TCP/UDP connections with process info."""
        connections = []

        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == 'NONE' and conn.type == 2:  # UDP
                    status = 'UDP'
                else:
                    status = conn.status or 'UNKNOWN'

                local_addr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else ""
                remote_addr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else ""

                # Process info
                process_name = ""
                if conn.pid:
                    try:
                        proc = psutil.Process(conn.pid)
                        process_name = proc.name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        process_name = f"PID {conn.pid}"

                protocol = 'TCP' if conn.type == 1 else 'UDP'

                # Remote IP lookup
                remote_ip = conn.raddr.ip if conn.raddr else ""
                whois_info = ""
                if remote_ip and self._whois and not remote_ip.startswith(('127.', '0.', '::1', '10.', '192.168.', '172.')):
                    whois_info = self._whois.lookup(remote_ip)

                connections.append({
                    'protocol': protocol,
                    'local_addr': local_addr,
                    'remote_addr': remote_addr,
                    'status': status,
                    'pid': conn.pid or 0,
                    'process': process_name,
                    'whois': whois_info,
                })
        except (psutil.AccessDenied, PermissionError):
            pass

        return connections

    def get_history(self):
        """Return recent connection events."""
        with self._lock:
            return list(self._history)
