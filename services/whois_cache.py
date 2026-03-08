"""WhoIs / IP lookup with disk-based JSON cache."""
import json
import os
import threading
import time
import requests
import config


class WhoisCache:
    """Caches IP → org/location lookups using ipinfo.io."""

    def __init__(self, cache_file=None):
        self._cache_file = cache_file or config.WHOIS_CACHE_FILE
        self._cache = self._load_cache()
        self._lock = threading.Lock()
        self._pending = set()

    def _load_cache(self):
        try:
            if os.path.exists(self._cache_file):
                with open(self._cache_file, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return {}

    def _save_cache(self):
        try:
            with open(self._cache_file, 'w') as f:
                json.dump(self._cache, f, indent=2)
        except IOError:
            pass

    def lookup(self, ip):
        """Return cached org name for IP, or schedule a background lookup."""
        with self._lock:
            if ip in self._cache:
                return self._cache[ip]

            if ip not in self._pending:
                self._pending.add(ip)
                thread = threading.Thread(target=self._fetch, args=(ip,), daemon=True)
                thread.start()

        return ""

    def _fetch(self, ip):
        """Fetch IP info from ipinfo.io (rate-limited)."""
        try:
            time.sleep(0.2)  # Rate limit
            resp = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                org = data.get('org', '')
                city = data.get('city', '')
                country = data.get('country', '')
                label = org
                if city and country:
                    label = f"{org} ({city}, {country})"
                elif country:
                    label = f"{org} ({country})"

                with self._lock:
                    self._cache[ip] = label
                    self._pending.discard(ip)
                    self._save_cache()
        except Exception:
            with self._lock:
                self._cache[ip] = "Unknown"
                self._pending.discard(ip)
