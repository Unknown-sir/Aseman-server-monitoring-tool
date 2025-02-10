from flask import Flask, render_template_string, request, jsonify, session
import psutil
import time
import os
import logging
import json

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# ذخیره لیمیت در فایل
LIMIT_FILE = 'network_limit.json'

# بارگذاری لیمیت از فایل
def load_limit():
    try:
        with open(LIMIT_FILE, 'r') as f:
            return json.load(f).get('limit')
    except:
        return None

# ذخیره لیمیت در فایل
def save_limit(limit):
    with open(LIMIT_FILE, 'w') as f:
        json.dump({'limit': limit}, f)

# متغیرهای مانیتورینگ
network_offset_sent = 0
network_offset_recv = 0
network_limit = load_limit()

def get_system_info():
    global network_offset_sent, network_offset_recv

    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    net_io = psutil.net_io_counters()
    disk = psutil.disk_usage('/')
    uptime = time.time() - psutil.boot_time()

    return {
        'cpu_usage': cpu_usage,
        'memory_usage': memory.percent,
        'bytes_sent': net_io.bytes_sent - network_offset_sent,
        'bytes_recv': net_io.bytes_recv - network_offset_recv,
        'disk_usage': disk.percent,
        'uptime': uptime
    }

@app.route('/')
def index():
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Server Monitor</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body { 
                    background: #1a1a1a; 
                    color: #fff;
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                }
                .stats {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }
                .stat-box {
                    background: #2d2d2d;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                }
                .chart-container {
                    background: #2d2d2d;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 30px;
                }
                button {
                    background: #00cc88;
                    color: #fff;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    cursor: pointer;
                }
                .modal {
                    display: none;
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: #333;
                    padding: 20px;
                    border-radius: 8px;
                    z-index: 1000;
                }
                .modal input {
                    display: block;
                    margin: 10px 0;
                    padding: 8px;
                    width: 200px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Server Monitoring</h1>
                
                <div class="stats">
                    <div class="stat-box">
                        <h3>CPU Usage</h3>
                        <span id="cpu-usage">0%</span>
                    </div>
                    <div class="stat-box">
                        <h3>Memory Usage</h3>
                        <span id="memory-usage">0%</span>
                    </div>
                    <div class="stat-box">
                        <h3>Network Usage</h3>
                        <span id="network-usage">0 MB</span>
                        <div id="network-limit-display"></div>
                    </div>
                </div>

                <div class="chart-container">
                    <canvas id="cpuChart"></canvas>
                </div>
                <div class="chart-container">
                    <canvas id="memoryChart"></canvas>
                </div>
                
                <button onclick="showLoginModal()">Admin Panel</button>
            </div>

            <!-- Login Modal -->
            <div id="loginModal" class="modal">
                <h3>Admin Login</h3>
                <input type="text" id="username" placeholder="Username">
                <input type="password" id="password" placeholder="Password">
                <button onclick="login()">Login</button>
            </div>

            <!-- Admin Panel Modal -->
            <div id="adminModal" class="modal">
                <h3>Admin Panel</h3>
                <div>
                    <input type="number" id="networkLimit" placeholder="Network Limit (TB)">
                    <button onclick="setLimit()">Set Limit</button>
                </div>
                <div>
                    <h4>Current Network Usage: <span id="adminNetworkUsage">0 TB</span></h4>
                </div>
            </div>

            <script>
                let cpuChart, memoryChart;
                let currentLimit = {{ network_limit|tojson|safe }};

                // Login functions
                function showLoginModal() {
                    document.getElementById('loginModal').style.display = 'block';
                }

                function login() {
                    const username = document.getElementById('username').value;
                    const password = document.getElementById('password').value;
                    
                    fetch('/login', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({username, password})
                    })
                    .then(res => res.json())
                    .then(data => {
                        if(data.success) {
                            document.getElementById('loginModal').style.display = 'none';
                            document.getElementById('adminModal').style.display = 'block';
                        } else {
                            alert('Invalid credentials!');
                        }
                    });
                }

                // Admin functions
                function setLimit() {
                    const limit = parseFloat(document.getElementById('networkLimit').value);
                    fetch('/set_limit', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({limit})
                    })
                    .then(() => {
                        currentLimit = limit;
                        updateLimitDisplay();
                    });
                }

                // Update UI
                function updateLimitDisplay() {
                    const limitDisplay = currentLimit ? 
                        `${currentLimit} TB (${((currentNetworkUsage / currentLimit) * 100).toFixed(1)}%)` : 
                        '∞';
                    document.getElementById('network-limit-display').textContent = `Limit: ${limitDisplay}`;
                }

                // Charts initialization
                function initCharts() {
                    const cpuCtx = document.getElementById('cpuChart').getContext('2d');
                    const memoryCtx = document.getElementById('memoryChart').getContext('2d');
                    
                    cpuChart = new Chart(cpuCtx, {
                        type: 'line',
                        data: { labels: [], datasets: [{
                            label: 'CPU Usage (%)',
                            data: [],
                            borderColor: '#00cc88',
                            tension: 0.1
                        }]}
                    });

                    memoryChart = new Chart(memoryCtx, {
                        type: 'line',
                        data: { labels: [], datasets: [{
                            label: 'Memory Usage (%)',
                            data: [],
                            borderColor: '#ff6b6b',
                            tension: 0.1
                        }]}
                    });
                }

                // Main update loop
                setInterval(async () => {
                    const data = await fetch('/data').then(res => res.json());
                    
                    // Update stats
                    document.getElementById('cpu-usage').textContent = `${data.cpu_usage.toFixed(1)}%`;
                    document.getElementById('memory-usage').textContent = `${data.memory_usage.toFixed(1)}%`;
                    
                    const networkMB = (data.bytes_sent + data.bytes_recv) / 1024 / 1024 / 1024 / 1024;
                    document.getElementById('network-usage').textContent = `${networkMB.toFixed(4)} TB`;
                    document.getElementById('adminNetworkUsage').textContent = `${networkMB.toFixed(4)} TB`;

                    // Update charts
                    const timeLabel = new Date().toLocaleTimeString();
                    
                    updateChart(cpuChart, data.cpu_usage, timeLabel);
                    updateChart(memoryChart, data.memory_usage, timeLabel);
                    
                    // Check limit
                    if(currentLimit && networkMB >= currentLimit) {
                        fetch('/shutdown', {method: 'POST'});
                    }
                    
                    updateLimitDisplay();
                }, 1000);

                function updateChart(chart, value, label) {
                    if(chart.data.labels.length > 15) chart.data.labels.shift();
                    chart.data.labels.push(label);
                    
                    if(chart.data.datasets[0].data.length > 15) chart.data.datasets[0].data.shift();
                    chart.data.datasets[0].data.push(value);
                    
                    chart.update();
                }

                window.onload = initCharts;
            </script>
        </body>
        </html>
    ''')

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    if data.get('username') == 'sirrskhi' and data.get('password') == 'M2903293538m#':
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/set_limit', methods=['POST'])
def set_limit():
    global network_limit
    network_limit = request.json.get('limit')
    save_limit(network_limit)
    return jsonify({'success': True})

@app.route('/shutdown', methods=['POST'])
def shutdown():
    global network_offset_sent, network_offset_recv
    net_io = psutil.net_io_counters()
    network_offset_sent = net_io.bytes_sent
    network_offset_recv = net_io.bytes_recv
    os.system('shutdown now')
    return jsonify({'success': True})

@app.route('/data')
def data():
    return jsonify(get_system_info())

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(host='0.0.0.0', port=5000, debug=True)
