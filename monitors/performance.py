"""Performance monitor using psutil — replaces Windows PerformanceCounters/WMI."""
import psutil
import subprocess
import time
import threading


class PerformanceMonitor:
    """Collects system metrics using psutil with delta-based rate calculations."""

    def __init__(self):
        self._prev_net = psutil.net_io_counters()
        self._prev_disk = psutil.disk_io_counters()
        self._prev_time = time.time()
        self._lock = threading.Lock()
        # Prime the CPU counter (first call always returns 0)
        psutil.cpu_percent(interval=None)

    def get_metrics(self):
        """Return a dict of current performance metrics."""
        now = time.time()

        with self._lock:
            dt = now - self._prev_time
            if dt < 0.1:
                dt = 0.1
            self._prev_time = now

            # CPU
            cpu = psutil.cpu_percent(interval=None)

            # RAM
            mem = psutil.virtual_memory()
            total_gb = mem.total / (1024 ** 3)
            available_gb = mem.available / (1024 ** 3)
            ram_percent = mem.percent

            # Network (delta-based KB/s)
            net = psutil.net_io_counters()
            net_send = (net.bytes_sent - self._prev_net.bytes_sent) / dt / 1024
            net_recv = (net.bytes_recv - self._prev_net.bytes_recv) / dt / 1024
            self._prev_net = net

            # Disk (delta-based KB/s)
            disk_metrics = []
            try:
                disk = psutil.disk_io_counters()
                disk_read = (disk.read_bytes - self._prev_disk.read_bytes) / dt / 1024
                disk_write = (disk.write_bytes - self._prev_disk.write_bytes) / dt / 1024
                self._prev_disk = disk
                disk_metrics.append({
                    "name": "Total",
                    "read_speed": round(max(0, disk_read), 1),
                    "write_speed": round(max(0, disk_write), 1),
                })
            except Exception:
                pass

            # Per-partition usage (filter out snap/loop mounts)
            partitions = []
            for p in psutil.disk_partitions(all=False):
                if '/snap/' in p.mountpoint or '/loop' in p.device:
                    continue
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    partitions.append({
                        "device": p.device,
                        "mountpoint": p.mountpoint,
                        "total_gb": round(usage.total / (1024 ** 3), 1),
                        "used_gb": round(usage.used / (1024 ** 3), 1),
                        "percent": usage.percent,
                    })
                except (PermissionError, OSError):
                    pass

            # GPU (nvidia-smi — same approach as Windows version)
            gpu_metrics = self._get_gpu_metrics()

        return {
            "cpu": round(cpu, 1),
            "ram_total_gb": round(total_gb, 1),
            "ram_available_gb": round(available_gb, 1),
            "ram_percent": round(ram_percent, 1),
            "net_send_kbs": round(max(0, net_send), 1),
            "net_recv_kbs": round(max(0, net_recv), 1),
            "disk_io": disk_metrics,
            "disk_partitions": partitions,
            "gpu": gpu_metrics,
        }

    def _get_gpu_metrics(self):
        """Query nvidia-smi for GPU stats (works on both Linux and Windows)."""
        try:
            result = subprocess.run(
                ["nvidia-smi",
                 "--query-gpu=name,memory.total,memory.used,utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                return []

            gpus = []
            for line in result.stdout.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4:
                    gpus.append({
                        "name": parts[0],
                        "total_mb": float(parts[1]),
                        "used_mb": float(parts[2]),
                        "utilization": float(parts[3]),
                    })
            return gpus
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []
