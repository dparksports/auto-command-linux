"""Systemd service and timer listing."""
import subprocess
import re


def get_services():
    """List systemd services and timers."""
    services = _list_services()
    timers = _list_timers()
    return {'services': services, 'timers': timers}


def _list_services():
    """Parse systemctl list-units output."""
    try:
        proc = subprocess.run(
            ['systemctl', 'list-units', '--type=service', '--all', '--no-pager',
             '--plain', '--no-legend'],
            capture_output=True, text=True, timeout=10
        )
        services = []
        for line in proc.stdout.strip().split('\n'):
            if not line.strip():
                continue
            parts = line.split(None, 4)
            if len(parts) >= 4:
                name = parts[0].replace('.service', '')
                services.append({
                    'name': name,
                    'load': parts[1],
                    'active': parts[2],
                    'sub': parts[3],
                    'description': parts[4] if len(parts) > 4 else '',
                })
        return services
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def _list_timers():
    """Parse systemctl list-timers output."""
    try:
        proc = subprocess.run(
            ['systemctl', 'list-timers', '--all', '--no-pager', '--no-legend'],
            capture_output=True, text=True, timeout=10
        )
        timers = []
        for line in proc.stdout.strip().split('\n'):
            if not line.strip():
                continue
            # Example: Wed 2024-01-15 10:00:00 UTC  1h left  ... snapd.snap-repair.timer snapd.snap-repair.service
            parts = line.rsplit(None, 2)
            if len(parts) >= 2:
                timer_name = parts[-2] if len(parts) >= 2 else ''
                unit_name = parts[-1] if len(parts) >= 1 else ''
                # Try to extract next/last times
                timers.append({
                    'timer': timer_name.replace('.timer', ''),
                    'unit': unit_name.replace('.service', ''),
                    'next': '',
                    'last': '',
                })
        return timers
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
