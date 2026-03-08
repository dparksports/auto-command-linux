"""Security monitor — replaces Windows EventLogWatcher on Security log."""
import threading
import subprocess
import re
from datetime import datetime
from collections import deque


class SecurityMonitor:
    """Monitors journalctl and auth.log for security-relevant events."""

    # Patterns to detect in log lines
    PATTERNS = [
        (r'sshd\[.*\]:\s+(Accepted|Failed)\s+(\S+)\s+for\s+(\S+)\s+from\s+(\S+)',
         'ssh', lambda m: {
             'result': m.group(1).lower(),
             'method': m.group(2),
             'user': m.group(3),
             'source_ip': m.group(4),
         }),
        (r'sudo:\s+(\S+)\s+:\s+.*COMMAND=(.*)',
         'sudo', lambda m: {
             'user': m.group(1),
             'command': m.group(2).strip(),
         }),
        (r'(su|login)\[.*\]:\s+(FAILED|Successful)\s+su\s+for\s+(\S+)',
         'login', lambda m: {
             'result': m.group(2).lower(),
             'user': m.group(3),
         }),
        (r'useradd\[.*\]:\s+new user:\s+name=(\S+)',
         'user_change', lambda m: {
             'action': 'user_created',
             'user': m.group(1),
         }),
        (r'userdel\[.*\]:\s+delete user\s+.(\S+).',
         'user_change', lambda m: {
             'action': 'user_deleted',
             'user': m.group(1),
         }),
        (r'passwd\[.*\]:\s+password changed for\s+(\S+)',
         'user_change', lambda m: {
             'action': 'password_changed',
             'user': m.group(1),
         }),
        (r'systemd\[1\]:\s+(Started|Stopped|Starting|Stopping)\s+(.*)',
         'service', lambda m: {
             'action': m.group(1).lower(),
             'service': m.group(2).strip().rstrip('.'),
         }),
    ]

    def __init__(self, socketio, max_events=500):
        self._socketio = socketio
        self._events = deque(maxlen=max_events)
        self._lock = threading.Lock()

    def start(self):
        """Start tailing journalctl in a background thread."""
        thread = threading.Thread(target=self._tail_journal, daemon=True)
        thread.start()

    def _tail_journal(self):
        """Follow journalctl for security-relevant messages."""
        try:
            proc = subprocess.Popen(
                ['journalctl', '-f', '-n', '50', '--no-pager',
                 '-o', 'short-iso',
                 '_COMM=sshd', '_COMM=sudo', '_COMM=su',
                 '_COMM=login', '_COMM=systemd', '_COMM=useradd',
                 '_COMM=userdel', '_COMM=passwd',
                 '+', 'SYSLOG_FACILITY=10',  # auth facility
                 '+', 'SYSLOG_FACILITY=4'],   # auth facility
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )
            for line in iter(proc.stdout.readline, ''):
                line = line.strip()
                if not line:
                    continue
                event = self._parse_line(line)
                if event:
                    with self._lock:
                        self._events.appendleft(event)
                    self._socketio.emit('security_event', event)
        except FileNotFoundError:
            # journalctl not available, try auth.log
            self._tail_auth_log()
        except Exception as e:
            print(f"Security monitor error: {e}")

    def _tail_auth_log(self):
        """Fallback: tail /var/log/auth.log."""
        try:
            proc = subprocess.Popen(
                ['tail', '-f', '-n', '50', '/var/log/auth.log'],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )
            for line in iter(proc.stdout.readline, ''):
                line = line.strip()
                if not line:
                    continue
                event = self._parse_line(line)
                if event:
                    with self._lock:
                        self._events.appendleft(event)
                    self._socketio.emit('security_event', event)
        except Exception as e:
            print(f"Auth log monitor error: {e}")

    def _parse_line(self, line):
        """Parse a log line against known patterns."""
        for pattern, category, extractor in self.PATTERNS:
            match = re.search(pattern, line)
            if match:
                details = extractor(match)
                # Extract timestamp from beginning of line
                ts = self._extract_timestamp(line)
                severity = self._determine_severity(category, details)

                return {
                    'timestamp': ts,
                    'category': category,
                    'severity': severity,
                    'details': details,
                    'raw': line[:200],
                }
        return None

    def _extract_timestamp(self, line):
        """Try to extract ISO or syslog timestamp from log line."""
        # ISO format from journalctl -o short-iso: 2024-01-15T10:30:45+0000
        iso_match = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', line)
        if iso_match:
            return iso_match.group(1).replace('T', ' ')
        # Syslog format: Jan 15 10:30:45
        syslog_match = re.match(r'([A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2})', line)
        if syslog_match:
            return syslog_match.group(1)
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def _determine_severity(self, category, details):
        """Classify event severity."""
        if category == 'ssh' and details.get('result') == 'failed':
            return 'warning'
        if category == 'login' and details.get('result') == 'failed':
            return 'warning'
        if category == 'user_change':
            return 'info'
        if category == 'sudo':
            return 'info'
        if category == 'service':
            return 'info'
        return 'info'

    def get_events(self):
        """Return current events list."""
        with self._lock:
            return list(self._events)
