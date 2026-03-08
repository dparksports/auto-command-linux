# Auto Command Linux

A real-time Linux system monitoring dashboard built with Python, Flask, and SocketIO.

## Features

- **Dashboard** — Live CPU, memory, disk, and network metrics via WebSocket
- **Security Monitor** — Auth log scanning, failed login detection, sudo events
- **Device Monitor** — USB/PCI hotplug events via udev
- **Connection Monitor** — Active network connections with WHOIS lookups
- **Firewall Manager** — UFW/iptables status, drift detection, and snapshots
- **Service Manager** — Systemd unit status and control
- **Security Enforcer** — Automated threat alerting
- **AI Analysis** — Optional Gemini-powered threat analysis

## Requirements

- Python 3.10+
- Linux (Ubuntu/Debian recommended)

## Quick Start

```bash
python -m venv env
source env/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000` in your browser.

## Configuration

Edit `config.py` to change host, port, debug mode, and polling intervals.

## License

See [LICENSE](LICENSE) for details.
