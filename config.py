"""Auto Command configuration."""
import os

DATA_DIR = os.path.expanduser("~/.local/share/auto-command")
os.makedirs(DATA_DIR, exist_ok=True)

# Performance monitor
PERF_INTERVAL = 1  # seconds between metrics updates

# Security monitor
SECURITY_LOG_MAX = 500  # max events to keep in memory

# Connections
CONNECTION_REFRESH_INTERVAL = 3  # seconds
WHOIS_CACHE_FILE = os.path.join(DATA_DIR, "ip_cache.json")
CONNECTION_HISTORY_FILE = os.path.join(DATA_DIR, "connection_history.json")

# Firewall
FIREWALL_SNAPSHOT_FILE = os.path.join(DATA_DIR, "firewall_snapshot.json")

# Gemini AI
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Flask
SECRET_KEY = os.environ.get("SECRET_KEY", "auto-command-secret-key")
HOST = "0.0.0.0"
PORT = 5000
DEBUG = True
