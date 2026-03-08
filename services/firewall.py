"""Firewall status service — parses ufw/iptables output."""
import subprocess
import json
import os
import re
import config


def get_firewall_status():
    """Get firewall rules and status. Tries ufw first, then iptables."""
    result = _try_ufw()
    if result:
        return result
    return _try_iptables()


def _try_ufw():
    """Parse ufw status verbose output."""
    try:
        proc = subprocess.run(
            ['ufw', 'status', 'verbose'],
            capture_output=True, text=True, timeout=5
        )
        if proc.returncode != 0:
            return None

        output = proc.stdout
        status_match = re.search(r'Status:\s+(\S+)', output)
        status = status_match.group(1) if status_match else 'unknown'

        default_match = re.search(r'Default:\s+(.*)', output)
        defaults = default_match.group(1).strip() if default_match else ''

        rules = []
        in_rules = False
        for line in output.split('\n'):
            if line.startswith('--'):
                in_rules = True
                continue
            if in_rules and line.strip():
                parts = re.split(r'\s{2,}', line.strip())
                if len(parts) >= 3:
                    rules.append({
                        'to': parts[0],
                        'action': parts[1],
                        'from': parts[2],
                        'comment': parts[3] if len(parts) > 3 else '',
                    })

        return {
            'engine': 'ufw',
            'status': status,
            'defaults': defaults,
            'rules': rules,
        }
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _try_iptables():
    """Parse iptables -L -n -v output."""
    try:
        proc = subprocess.run(
            ['iptables', '-L', '-n', '-v', '--line-numbers'],
            capture_output=True, text=True, timeout=5
        )
        if proc.returncode != 0:
            return {
                'engine': 'iptables',
                'status': 'error',
                'defaults': '',
                'rules': [],
                'error': proc.stderr.strip(),
            }

        rules = []
        current_chain = ''
        for line in proc.stdout.split('\n'):
            chain_match = re.match(r'Chain\s+(\S+)\s+\(policy\s+(\S+)', line)
            if chain_match:
                current_chain = chain_match.group(1)
                continue
            parts = line.split()
            if len(parts) >= 9 and parts[0].isdigit():
                rules.append({
                    'chain': current_chain,
                    'num': parts[0],
                    'target': parts[3],
                    'protocol': parts[4],
                    'source': parts[8],
                    'destination': parts[9] if len(parts) > 9 else '',
                    'extra': ' '.join(parts[10:]) if len(parts) > 10 else '',
                })

        return {
            'engine': 'iptables',
            'status': 'active',
            'defaults': '',
            'rules': rules,
        }
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {
            'engine': 'none',
            'status': 'unavailable',
            'defaults': '',
            'rules': [],
        }


def check_drift():
    """Compare current firewall rules against saved snapshot."""
    snapshot_file = config.FIREWALL_SNAPSHOT_FILE
    current = get_firewall_status()

    if not os.path.exists(snapshot_file):
        return {'has_drift': False, 'message': 'No snapshot saved yet'}

    try:
        with open(snapshot_file, 'r') as f:
            saved = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {'has_drift': False, 'message': 'Invalid snapshot'}

    current_rules = json.dumps(current.get('rules', []), sort_keys=True)
    saved_rules = json.dumps(saved.get('rules', []), sort_keys=True)

    if current_rules != saved_rules:
        return {
            'has_drift': True,
            'message': 'Firewall rules have changed since last snapshot',
        }
    return {'has_drift': False, 'message': 'No drift detected'}


def save_snapshot():
    """Save current firewall rules as the reference snapshot."""
    current = get_firewall_status()
    with open(config.FIREWALL_SNAPSHOT_FILE, 'w') as f:
        json.dump(current, f, indent=2)
    return {'saved': True}
