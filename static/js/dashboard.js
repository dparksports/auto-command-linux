/* ═══════════════════════════════════════════════════════════════
   Auto Command — Dashboard Charts (Chart.js + SocketIO)
   Real-time CPU, RAM, Network, Disk graphs with 60s history
   ═══════════════════════════════════════════════════════════════ */

const HISTORY_LEN = 60;
const labels = Array.from({ length: HISTORY_LEN }, (_, i) => '');

/* ── Chart defaults ──────────────────────────────────────────── */
Chart.defaults.color = '#94A3B8';
Chart.defaults.borderColor = '#1E293B';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 11;
Chart.defaults.animation.duration = 400;

function makeDataset(label, color, data) {
    return {
        label,
        data: data || new Array(HISTORY_LEN).fill(0),
        borderColor: color,
        backgroundColor: color + '18',
        borderWidth: 2,
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        pointHitRadius: 8,
    };
}

function makeChartConfig(datasets, yMax, yLabel) {
    return {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    display: datasets.length > 1,
                    position: 'top',
                    labels: { boxWidth: 10, padding: 12, font: { size: 11 } }
                },
                tooltip: {
                    backgroundColor: '#141B2D',
                    borderColor: '#1E293B',
                    borderWidth: 1,
                    titleFont: { weight: '500' },
                    padding: 10,
                    cornerRadius: 8,
                }
            },
            scales: {
                x: { display: false },
                y: {
                    min: 0,
                    max: yMax || undefined,
                    title: { display: !!yLabel, text: yLabel || '', font: { size: 10 } },
                    grid: { color: '#1E293B40' },
                    ticks: { font: { family: "'JetBrains Mono', monospace", size: 10 } }
                }
            }
        }
    };
}

/* ── Create charts ───────────────────────────────────────────── */
const cpuChart = new Chart(
    document.getElementById('cpu-chart'),
    makeChartConfig([makeDataset('CPU %', '#00F0FF')], 100, '%')
);

const ramChart = new Chart(
    document.getElementById('ram-chart'),
    makeChartConfig([makeDataset('RAM %', '#B388FF')], 100, '%')
);

const netChart = new Chart(
    document.getElementById('net-chart'),
    makeChartConfig([
        makeDataset('Send', '#00E676'),
        makeDataset('Recv', '#00F0FF'),
    ], undefined, 'KB/s')
);

const diskChart = new Chart(
    document.getElementById('disk-chart'),
    makeChartConfig([
        makeDataset('Read', '#FFAE00'),
        makeDataset('Write', '#FF5252'),
    ], undefined, 'KB/s')
);

/* ── Push data helper ────────────────────────────────────────── */
function pushData(chart, datasetIndex, value) {
    const ds = chart.data.datasets[datasetIndex].data;
    ds.push(value);
    if (ds.length > HISTORY_LEN) ds.shift();
}

/* ── GPU info renderer ───────────────────────────────────────── */
let gpuRendered = false;

function renderGpuInfo(gpus) {
    const container = document.getElementById('gpu-info');
    if (!container || gpus.length === 0) return;

    let html = '';
    gpus.forEach(g => {
        const memPercent = g.total_mb > 0 ? ((g.used_mb / g.total_mb) * 100).toFixed(0) : 0;
        html += `
            <div class="info-item">
                <span class="info-label">GPU</span>
                <span class="info-value">${g.name}</span>
            </div>
            <div class="info-item">
                <span class="info-label">VRAM</span>
                <span class="info-value">${g.used_mb.toFixed(0)} / ${g.total_mb.toFixed(0)} MB (${memPercent}%)</span>
            </div>
            <div class="info-item">
                <span class="info-label">GPU Load</span>
                <span class="info-value">${g.utilization.toFixed(0)}%</span>
            </div>
        `;
    });
    container.innerHTML = html;
    gpuRendered = true;
}

/* ── Partition info renderer ─────────────────────────────────── */
let partitionsRendered = false;

function renderPartitions(parts) {
    const container = document.getElementById('partition-info');
    if (!container || parts.length === 0) return;

    let html = '';
    parts.forEach(p => {
        html += `
            <div class="info-item">
                <span class="info-label">${p.mountpoint}</span>
                <span class="info-value">${p.used_gb} / ${p.total_gb} GB (${p.percent}%)</span>
            </div>
        `;
    });
    container.innerHTML = html;
    partitionsRendered = true;
}

/* ── Metrics handler ─────────────────────────────────────────── */
socket.on('metrics', (data) => {
    // Stats cards
    document.getElementById('cpu-value').textContent = data.cpu + '%';
    document.getElementById('cpu-bar').style.width = data.cpu + '%';
    if (data.cpu > 85) {
        document.getElementById('cpu-bar').className = 'progress-fill warn';
    } else {
        document.getElementById('cpu-bar').className = 'progress-fill';
    }

    document.getElementById('ram-value').textContent = data.ram_percent + '%';
    const usedGb = (data.ram_total_gb - data.ram_available_gb).toFixed(1);
    document.getElementById('ram-detail').textContent = `${usedGb} / ${data.ram_total_gb} GB`;
    document.getElementById('ram-bar').style.width = data.ram_percent + '%';
    if (data.ram_percent > 85) {
        document.getElementById('ram-bar').className = 'progress-fill warn';
    } else {
        document.getElementById('ram-bar').className = 'progress-fill';
    }

    document.getElementById('net-send').textContent = formatRateShort(data.net_send_kbs);
    document.getElementById('net-recv').textContent = formatRateShort(data.net_recv_kbs);

    // Disk
    if (data.disk_io && data.disk_io.length > 0) {
        document.getElementById('disk-read').textContent = formatRateShort(data.disk_io[0].read_speed);
        document.getElementById('disk-write').textContent = formatRateShort(data.disk_io[0].write_speed);
    }

    // Charts
    pushData(cpuChart, 0, data.cpu);
    cpuChart.update('none');

    pushData(ramChart, 0, data.ram_percent);
    ramChart.update('none');

    pushData(netChart, 0, data.net_send_kbs);
    pushData(netChart, 1, data.net_recv_kbs);
    netChart.update('none');

    if (data.disk_io && data.disk_io.length > 0) {
        pushData(diskChart, 0, data.disk_io[0].read_speed);
        pushData(diskChart, 1, data.disk_io[0].write_speed);
        diskChart.update('none');
    }

    // GPU (render once, update values)
    if (!gpuRendered && data.gpu && data.gpu.length > 0) {
        renderGpuInfo(data.gpu);
    }

    // Partitions (render once)
    if (!partitionsRendered && data.disk_partitions && data.disk_partitions.length > 0) {
        renderPartitions(data.disk_partitions);
    }
});
