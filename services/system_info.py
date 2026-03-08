"""System information service — hostname, OS, kernel, uptime, Secure Boot."""
import platform
import subprocess
import psutil
from datetime import datetime


def get_system_info():
    """Return a dict of static system information."""
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time

    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, _ = divmod(remainder, 60)

    info = {
        "hostname": platform.node(),
        "os": _get_os_release(),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "uptime": f"{hours}h {minutes}m",
        "boot_time": boot_time.strftime("%Y-%m-%d %H:%M"),
        "cpu_model": _get_cpu_model(),
        "cpu_cores": psutil.cpu_count(logical=False) or "?",
        "cpu_threads": psutil.cpu_count(logical=True) or "?",
        "secure_boot": _get_secure_boot_status(),
    }
    return info


def _get_os_release():
    """Get pretty OS name from /etc/os-release."""
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
    except FileNotFoundError:
        pass
    return f"{platform.system()} {platform.release()}"


def _get_cpu_model():
    """Get CPU model name from /proc/cpuinfo."""
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except FileNotFoundError:
        pass
    return platform.processor() or "Unknown"


def _get_secure_boot_status():
    """Check Secure Boot status via mokutil."""
    try:
        result = subprocess.run(
            ["mokutil", "--sb-state"],
            capture_output=True, text=True, timeout=5
        )
        output = result.stdout.strip().lower()
        if "enabled" in output:
            return "Enabled"
        elif "disabled" in output:
            return "Disabled"
        return output
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "Unknown"
