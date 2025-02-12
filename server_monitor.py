from flask import Flask, render_template_string, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import psutil
import time
import os
import logging
import json

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey')

# تنظیمات فایل‌های ذخیره‌سازی
LIMIT_FILE = 'network_limit.json'
SECURITY_FILE = 'sec.json'

def load_security_config():
    try:
        with open(SECURITY_FILE, 'r') as f:
            config = json.load(f)
            if not all(key in config for key in ['username', 'password']):
                raise ValueError("Invalid security config file")
            
            # هش کردن رمز عبور و حذف نسخه متنی
            config['password_hash'] = generate_password_hash(config['password'])
            del config['password']
            return config
            
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        logging.error(f"خطای پیکربندی امنیتی: {str(e)}")
        exit(1)

def load_limit():
    try:
        with open(LIMIT_FILE, 'r') as f:
            return json.load(f).get('limit')
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def save_limit(limit):
    with open(LIMIT_FILE, 'w') as f:
        json.dump({'limit': limit}, f)

# بارگذاری تنظیمات امنیتی
security_config = load_security_config()
ADMIN_USERNAME = security_config['username']
ADMIN_PASSWORD_HASH = security_config['password_hash']

# مقداردهی اولیه
network_offset_sent = 0
network_offset_recv = 0
network_limit = load_limit() or None

# Rate Limiting
limiter = Limiter(app=app, key_func=get_remote_address)

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
                .footer {
                    text-align: center;
                    margin-top: 20px;
                    font-weight: bold;
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
                        <span id="network-usage">0 TB</span>
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
                    const limitDisplay = currentLimit !== null ? 
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
                        data: { 
                            labels: [], 
                            datasets: [{
                                label: 'CPU Usage (%)',
                                data: [],
                                borderColor: '#00cc88',
                                tension: 0.1
                            }]
                        }
                    });

                    memoryChart = new Chart(memoryCtx, {
                        type: 'line',
                        data: { 
                            labels: [], 
                            datasets: [{
                                label: 'Memory Usage (%)',
                                data: [],
                                borderColor: '#ff6b6b',
                                tension: 0.1
                            }]
                        }
                    });
                }

                // Main update loop
                let currentNetworkUsage = 0;
                setInterval(async () => {
                    const data = await fetch('/data').then(res => res.json());
                    
                    // Update stats
                    document.getElementById('cpu-usage').textContent = `${data.cpu_usage.toFixed(1)}%`;
                    document.getElementById('memory-usage').textContent = `${data.memory_usage.toFixed(1)}%`;
                    
                    currentNetworkUsage = (data.bytes_sent + data.bytes_recv) / 1024 ** 4;
                    document.getElementById('network-usage').textContent = `${currentNetworkUsage.toFixed(4)} TB`;
                    document.getElementById('adminNetworkUsage').textContent = `${currentNetworkUsage.toFixed(4)} TB`;

                    // Update charts
                    const timeLabel = new Date().toLocaleTimeString();
                    
                    updateChart(cpuChart, data.cpu_usage, timeLabel);
                    updateChart(memoryChart, data.memory_usage, timeLabel);
                    
                    // Check limit
                    if(currentLimit && currentNetworkUsage >= currentLimit) {
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
            <div class="footer">Powered by <a href="https://t.me/sirrskhi">Rskhi-TeaM</a></div>
        </body>
        </html>
    ''', network_limit=network_limit)

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    data = request.json
    if data.get('username') == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, data.get('password')):
        return jsonify({'success': True})
    logging.warning(f"Failed login attempt from IP: {request.remote_addr}")
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
    
    # بررسی وجود فایل امنیتی
    if not os.path.exists(SECURITY_FILE):
        logging.error(f"فایل امنیتی '{SECURITY_FILE}' یافت نشد!")
        exit(1)
    
    # ایجاد فایل لیمیت در صورت عدم وجود
    if not os.path.exists(LIMIT_FILE):
        save_limit(None)
    
    app.run(host='0.0.0.0', port=5000, debug=False)
