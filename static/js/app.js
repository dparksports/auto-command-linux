/* ═══════════════════════════════════════════════════════════════
   Auto Command — Shared App Logic (SocketIO, navigation)
   ═══════════════════════════════════════════════════════════════ */

const socket = io();

socket.on('connect', () => {
    document.getElementById('connection-status').className = '';
    const dot = document.getElementById('status-dot');
    if (dot) dot.style.background = 'var(--green)';
    const txt = document.getElementById('status-text');
    if (txt) txt.textContent = 'Monitoring Active';
});

socket.on('disconnect', () => {
    document.getElementById('connection-status').className = 'disconnected';
    const dot = document.getElementById('status-dot');
    if (dot) dot.style.background = 'var(--red)';
    const txt = document.getElementById('status-text');
    if (txt) txt.textContent = 'Disconnected';
});

/* Utility: format number with appropriate unit */
function formatRate(kbs) {
    if (kbs >= 1024) return (kbs / 1024).toFixed(1) + ' MB/s';
    return kbs.toFixed(0) + ' KB/s';
}

function formatRateShort(kbs) {
    if (kbs >= 1024) return (kbs / 1024).toFixed(1);
    return kbs.toFixed(0);
}
