"""Device monitor using pyudev — replaces WndProc WM_DEVICECHANGE + WMI."""
import threading
import time
from datetime import datetime


class DeviceMonitor:
    """Watches for USB/device hotplug events via pyudev and tracks network adapters."""

    def __init__(self, socketio):
        self._socketio = socketio
        self._events = []
        self._lock = threading.Lock()
        self._max_events = 200

    def start(self):
        """Start the udev monitor in a background thread."""
        thread = threading.Thread(target=self._watch_udev, daemon=True)
        thread.start()

    def _watch_udev(self):
        """Monitor udev events for device add/remove."""
        try:
            import pyudev
            context = pyudev.Context()
            monitor = pyudev.Monitor.from_netlink(context)
            monitor.filter_by(subsystem='usb')
            monitor.filter_by(subsystem='block')
            monitor.filter_by(subsystem='net')
            monitor.filter_by(subsystem='input')

            for device in iter(monitor.poll, None):
                event = self._format_event(device)
                if event:
                    with self._lock:
                        self._events.insert(0, event)
                        if len(self._events) > self._max_events:
                            self._events.pop()
                    self._socketio.emit('device_event', event)
        except ImportError:
            print("pyudev not available — device monitoring disabled")
        except Exception as e:
            print(f"Device monitor error: {e}")

    def _format_event(self, device):
        """Convert a pyudev device event into a dict."""
        action = device.action
        if action not in ('add', 'remove', 'change'):
            return None

        # Get a useful name
        name = (device.get('ID_MODEL', '') or
                device.get('ID_FS_LABEL', '') or
                device.get('INTERFACE', '') or
                device.sys_name or 'Unknown')
        name = name.replace('_', ' ')

        vendor = device.get('ID_VENDOR', '') or ''
        vendor = vendor.replace('_', ' ')

        subsystem = device.subsystem or 'unknown'
        dev_type = device.device_type or subsystem

        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'action': action,
            'name': name,
            'vendor': vendor,
            'subsystem': subsystem,
            'type': dev_type,
            'path': device.device_path or '',
        }

    def get_events(self):
        """Return current event list."""
        with self._lock:
            return list(self._events)

    def get_network_adapters(self):
        """List network interfaces and their status."""
        import psutil
        adapters = []
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()

        for iface, st in stats.items():
            addr_list = addrs.get(iface, [])
            ipv4 = ''
            mac = ''
            for a in addr_list:
                if a.family.name == 'AF_INET':
                    ipv4 = a.address
                elif a.family.name == 'AF_PACKET':
                    mac = a.address

            adapters.append({
                'name': iface,
                'is_up': st.isup,
                'speed': st.speed if st.speed > 0 else None,
                'mtu': st.mtu,
                'ipv4': ipv4,
                'mac': mac,
            })

        return adapters
