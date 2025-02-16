from flask import Flask, render_template_string, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import psutil
import time
import os
import logging
import json
import atexit
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey')

# ========================= rskhi-permiuim Start =========================
INSTALL_TIME_FILE = 'install_time.json'
LIMIT_FILE = 'network_limit.json'
SECURITY_FILE = 'sec.json'
TRAFFIC_FILE = 'traffic_data.json'

def get_install_time():
    try:
        with open(INSTALL_TIME_FILE, 'r') as f:
            return json.load(f).get('install_time')
    except (FileNotFoundError, json.JSONDecodeError):
        install_time = time.time()
        with open(INSTALL_TIME_FILE, 'w') as f:
            json.dump({'install_time': install_time}, f)
        return install_time

def check_self_destruct():
    install_time = get_install_time()
    elapsed = time.time() - install_time
    return elapsed > 432000  # 5 days in seconds

def self_destruct():
    try:
        files_to_delete = [__file__, LIMIT_FILE, SECURITY_FILE, TRAFFIC_FILE, INSTALL_TIME_FILE]
        for f in files_to_delete:
            if os.path.exists(f):
                os.remove(f)
        logging.info("Self-destruct completed")
        os._exit(0)
    except Exception as e:
        logging.error(f"Self-destruct failed: {str(e)}")
        os._exit(1)

if check_self_destruct():
    self_destruct()

def check_self_destruct_job():
    if check_self_destruct():
        self_destruct()
# ========================= rskhi-permiuim End =========================

def load_traffic_data():
    try:
        with open(TRAFFIC_FILE, 'r') as f:
            data = json.load(f)
            return data.get('total_sent', 0), data.get('total_recv', 0)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0, 0

def save_traffic_data():
    current_net_io = psutil.net_io_counters()
    delta_sent = current_net_io.bytes_sent - initial_sent
    delta_recv = current_net_io.bytes_recv - initial_recv
    total_sent, total_recv = load_traffic_data()
    with open(TRAFFIC_FILE, 'w') as f:
        json.dump({
            'total_sent': total_sent + delta_sent,
            'total_recv': total_recv + delta_recv
        }, f)

total_sent, total_recv = load_traffic_data()
initial_net_io = psutil.net_io_counters()
initial_sent = initial_net_io.bytes_sent - (total_sent % (1024 ** 4))
initial_recv = initial_net_io.bytes_recv - (total_recv % (1024 ** 4))

scheduler = BackgroundScheduler()
scheduler.add_job(func=save_traffic_data, trigger="interval", minutes=5)
scheduler.add_job(func=check_self_destruct_job, trigger="interval", hours=1)
scheduler.start()

atexit.register(lambda: [save_traffic_data(), scheduler.shutdown()])

def load_security_config():
    try:
        with open(SECURITY_FILE, 'r') as f:
            config = json.load(f)
            if not all(key in config for key in ['username', 'password']):
                raise ValueError("Invalid security config file")
            
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

security_config = load_security_config()
ADMIN_USERNAME = security_config['username']
ADMIN_PASSWORD_HASH = security_config['password_hash']

network_limit = load_limit() or None

limiter = Limiter(app=app, key_func=get_remote_address)

prev_net_io = psutil.net_io_counters()
prev_disk_io = psutil.disk_io_counters()
last_update = time.time()

CPU_CORES = psutil.cpu_count(logical=False)
TOTAL_RAM = round(psutil.virtual_memory().total / (1024 ** 3), 2)

def get_system_info():
    global prev_net_io, prev_disk_io, last_update

    current_net_io = psutil.net_io_counters()
    time_diff = time.time() - last_update
    
    delta_sent = current_net_io.bytes_sent - prev_net_io.bytes_sent
    delta_recv = current_net_io.bytes_recv - prev_net_io.bytes_recv
    
    sent_speed = (delta_sent * 8) / (time_diff * 1e6)
    recv_speed = (delta_recv * 8) / (time_diff * 1e6)
    total_speed = sent_speed + recv_speed

    current_disk_io = psutil.disk_io_counters()
    read_speed = (current_disk_io.read_bytes - prev_disk_io.read_bytes) / (time_diff * 1024**2)
    write_speed = (current_disk_io.write_bytes - prev_disk_io.write_bytes) / (time_diff * 1024**2)

    prev_net_io = current_net_io
    prev_disk_io = current_disk_io
    last_update = time.time()

    current_total_sent = total_sent + (current_net_io.bytes_sent - initial_sent)
    current_total_recv = total_recv + (current_net_io.bytes_recv - initial_recv)

    install_time = get_install_time()
    time_remaining = 432000 - (time.time() - install_time)

    return {
        'cpu_usage': psutil.cpu_percent(interval=1),
        'cpu_cores': CPU_CORES,
        'memory_usage': psutil.virtual_memory().percent,
        'total_ram': TOTAL_RAM,
        'bytes_sent': current_total_sent,
        'bytes_recv': current_total_recv,
        'sent_speed': sent_speed,
        'recv_speed': recv_speed,
        'total_speed': total_speed,
        'read_speed': read_speed,
        'write_speed': write_speed,
        'disk_usage': psutil.disk_usage('/').percent,
        'uptime': time.time() - psutil.boot_time(),
        'time_remaining': max(0, time_remaining)
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
                    position: relative;
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
                #loginModal {
                    display: none;
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: #333;
                    padding: 30px;
                    border-radius: 10px;
                    z-index: 1000;
                    box-shadow: 0 0 20px rgba(0,0,0,0.5);
                }
                .login-input {
                    margin: 10px 0;
                    padding: 10px;
                    width: 250px;
                    border-radius: 5px;
                    border: 1px solid #444;
                    background: #222;
                    color: #fff;
                }
                .login-btn {
                    background: #00cc88;
                    color: #fff;
                    border: none;
                    padding: 12px 25px;
                    border-radius: 5px;
                    cursor: pointer;
                    margin-top: 15px;
                }
                #errorMessage {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    background: #ff4444;
                    color: white;
                    padding: 15px;
                    border-radius: 8px;
                    display: none;
                }
                .admin-panel {
                    display: none;
                }
                #countdown {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    background: #ff4444;
                    color: white;
                    padding: 15px;
                    border-radius: 8px;
                    font-family: monospace;
                    z-index: 3000;
                }
                .chart-popup {
                    display: none;
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.7);
                    z-index: 2000;
                }
                .popup-content {
                    position: relative;
                    background: #2d2d2d;
                    margin: 5% auto;
                    padding: 40px 20px 20px;
                    width: 80%;
                    max-width: 800px;
                    border-radius: 8px;
                }
                .close-btn {
                    position: absolute;
                    top: 10px;
                    right: 20px;
                    color: #fff;
                    font-size: 28px;
                    cursor: pointer;
                }
                .Sabc-copyright { 
                    margin-left:50%;  
                    background: #222 -webkit-gradient(linear, left top, right top, from(#222), to(#222), color-stop(0.5, #fff)) 0 0 no-repeat;
                    -webkit-background-size: 80px;
                    color: rgba(255, 255, 255, 0.1);
                    -webkit-background-clip: text;
                    -webkit-animation-name: shine;
                    -webkit-animation-duration: 5s;
                    -webkit-animation-iteration-count: infinite;
                    text-shadow: 0 0px 0px rgba(255, 255, 255, 0.5);
                    text-align: left;
                    font-size:.9rem
                }
                .Sabc-copyright a {color: rgba(255, 255, 255, 0.1);}
                .Sabc-copyright a:hover {color: rgba(62, 80, 180, 1);}
                @-webkit-keyframes shine {
                    0%, 10% {background-position: -1000px;}
                    20% {background-position: top left;}
                    90% {background-position: top right;}
                    100% {background-position: 1000px;}
                }
            </style>
        </head>
        <body>
            <div id="loginModal">
                <h2 style="text-align: center; margin-bottom: 20px;">Login</h2>
                <input type="text" id="username" class="login-input" placeholder="username"></br>
                <input type="password" id="password" class="login-input" placeholder="password"></br>
                <center><button onclick="login()" class="login-btn">Login</button></center>
            </div>

            <div id="errorMessage">شما به صفحه کلاینت وارد شدید</div>

            <div id="countdown">Until the end of the free subscription :
		</br></br>
		 5d 00:00:00</div>

            <div class="container">
                <h1>Aseman Server Monitoring</h1>
                
                <div class="stats">
                    <div class="stat-box">
                        <h3 class="chart-title" onclick="showPopup('cpuPopup')">CPU Usage</h3>
                        <span id="cpu-usage">0%</span>
                        <div class="stat-details">
                            Cores: {{ cpu_cores }}
                        </div>
                    </div>
                    
                    <div class="stat-box">
                        <h3 class="chart-title" onclick="showPopup('memoryPopup')">Memory Usage</h3>
                        <span id="memory-usage">0%</span>
                        <div class="stat-details">
                            Total: {{ total_ram }} GB
                        </div>
                    </div>
                    
                    <div class="stat-box">
                        <h3 class="chart-title" onclick="showPopup('networkPopup')">Network bandwidth</h3>
                        <div class="network-stats">
                            <span id="download-speed">0 Mbps ↓</span>
                            <span id="upload-speed">0 Mbps ↑</span>
                            <span id="total-speed">0 Mbps ↔</span>
                        </div>
                    </div>
                    
                    <div class="stat-box">
                        <h3 class="chart-title" onclick="showPopup('ioPopup')">I/O</h3>
                        <div class="io-stats">
                            <span id="read-speed">0 MB/s Read</span>
                            <span id="write-speed">0 MB/s Write</span>
                        </div>
                    </div>
                    
                    <div class="stat-box">
                        <h3>Traffic</h3>
                        <span id="network-usage">0 TB</span>
                        <div id="network-limit-display"></div>
                    </div>
                    
                    <div class="stat-box admin-panel" id="adminPanel">
                        <h3>Limit</h3>
                        <input type="number" id="networkLimit" placeholder="Limit (TB)" style="margin: 10px 0; padding: 8px;">
                        <button onclick="setLimit()" style="background: #00cc88;">تنظیم محدودیت</button>
                    </div>
                </div>

                <div class="chart-container">
                    <canvas id="cpuChart"></canvas>
                </div>
                <div class="chart-container">
                    <canvas id="memoryChart"></canvas>
                </div>
                <div class="chart-container">
                    <canvas id="networkChart"></canvas>
                </div>
                <div class="chart-container">
                    <canvas id="ioChart"></canvas>
                </div>
            </div>

            <div id="cpuPopup" class="chart-popup">
                <div class="popup-content">
                    <span class="close-btn" onclick="closePopup('cpuPopup')">&times;</span>
                    <canvas id="cpuPopupChart"></canvas>
                </div>
            </div>

            <div id="memoryPopup" class="chart-popup">
                <div class="popup-content">
                    <span class="close-btn" onclick="closePopup('memoryPopup')">&times;</span>
                    <canvas id="memoryPopupChart"></canvas>
                </div>
            </div>

            <div id="networkPopup" class="chart-popup">
                <div class="popup-content">
                    <span class="close-btn" onclick="closePopup('networkPopup')">&times;</span>
                    <canvas id="networkPopupChart"></canvas>
                </div>
            </div>

            <div id="ioPopup" class="chart-popup">
                <div class="popup-content">
                    <span class="close-btn" onclick="closePopup('ioPopup')">&times;</span>
                    <canvas id="ioPopupChart"></canvas>
                </div>
            </div>

            <script>
                let cpuChart, memoryChart, networkChart, ioChart;
                let cpuPopupChart, memoryPopupChart, networkPopupChart, ioPopupChart;
                let currentLimit = {{ network_limit|tojson|safe }};
                let currentCredentials = null;

                window.onload = () => {
                    document.getElementById('loginModal').style.display = 'block';
                }

                async function login() {
                    const username = document.getElementById('username').value;
                    const password = document.getElementById('password').value;
                    
                    const response = await fetch('/login', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({username, password})
                    });
                    
                    const data = await response.json();
                    
                    if(data.success) {
                        document.getElementById('loginModal').style.display = 'none';
                        document.getElementById('adminPanel').style.display = 'block';
                        currentCredentials = {username, password};
                    } else {
                        document.getElementById('loginModal').style.display = 'none';
                        document.getElementById('errorMessage').style.display = 'block';
                        setTimeout(() => {
                            document.getElementById('errorMessage').style.display = 'none';
                        }, 3000);
                    }
                }

                function showPopup(popupId) {
                    document.getElementById(popupId).style.display = 'block';
                    switch(popupId) {
                        case 'cpuPopup':
                            if(!cpuPopupChart) initPopupChart('cpu');
                            break;
                        case 'memoryPopup':
                            if(!memoryPopupChart) initPopupChart('memory');
                            break;
                        case 'networkPopup':
                            if(!networkPopupChart) initPopupChart('network');
                            break;
                        case 'ioPopup':
                            if(!ioPopupChart) initPopupChart('io');
                            break;
                    }
                }

                function closePopup(popupId) {
                    document.getElementById(popupId).style.display = 'none';
                }

                function initPopupChart(type) {
                    const ctx = document.getElementById(`${type}PopupChart`).getContext('2d');
                    let mainChart;
                    switch(type) {
                        case 'cpu': mainChart = cpuChart; break;
                        case 'memory': mainChart = memoryChart; break;
                        case 'network': mainChart = networkChart; break;
                        case 'io': mainChart = ioChart; break;
                    }

                    const newChart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: [...mainChart.data.labels],
                            datasets: mainChart.data.datasets.map(dataset => ({
                                ...dataset,
                                data: [...dataset.data]
                            }))
                        },
                        options: {
                            maintainAspectRatio: false,
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    title: {
                                        display: true,
                                        text: type === 'network' ? 'Mbps' : 
                                              type === 'io' ? 'MB/s' : '%'
                                    }
                                }
                            }
                        }
                    });

                    switch(type) {
                        case 'cpu': cpuPopupChart = newChart; break;
                        case 'memory': memoryPopupChart = newChart; break;
                        case 'network': networkPopupChart = newChart; break;
                        case 'io': ioPopupChart = newChart; break;
                    }
                }

                function updateChart(chart, values, label) {
                    if(chart.data.labels.length > 15) chart.data.labels.shift();
                    chart.data.labels.push(label);
					
                    if(Array.isArray(values)) {
                        values.forEach((value, index) => {
                            if(chart.data.datasets[index].data.length > 15) chart.data.datasets[index].data.shift();
                            chart.data.datasets[index].data.push(value);
                        });
                    } else {
                        if(chart.data.datasets[0].data.length > 15) chart.data.datasets[0].data.shift();
                        chart.data.datasets[0].data.push(values);
                    }
                    
                    chart.update();
                    switch(chart) {
                        case cpuChart:
                            if(cpuPopupChart) updateChart(cpuPopupChart, values, label);
                            break;
                        case memoryChart:
                            if(memoryPopupChart) updateChart(memoryPopupChart, values, label);
                            break;
                        case networkChart:
                            if(networkPopupChart) updateChart(networkPopupChart, values, label);
                            break;
                        case ioChart:
                            if(ioPopupChart) updateChart(ioPopupChart, values, label);
                            break;
                    }
                }

                async function setLimit() {
                    const limit = parseFloat(document.getElementById('networkLimit').value);
                    
                    const response = await fetch('/set_limit', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            limit: limit,
                            username: currentCredentials.username,
                            password: currentCredentials.password
                        })
                    });
                    
                    if(response.ok) {
                        currentLimit = limit;
                        updateLimitDisplay();
                    }
                }

                function updateLimitDisplay() {
                    const limitDisplay = currentLimit !== null ? 
                        `${currentLimit} TB (${((currentNetworkUsage / currentLimit) * 100).toFixed(1)}%)` : 
                        '∞';
                    document.getElementById('network-limit-display').textContent = `Limit: ${limitDisplay}`;
                }

                let currentNetworkUsage = 0;
                
                function formatTime(seconds) {
                    const days = Math.floor(seconds / 86400);
                    seconds %= 86400;
                    const hours = Math.floor(seconds / 3600);
                    seconds %= 3600;
                    const minutes = Math.floor(seconds / 60);
                    seconds = Math.floor(seconds % 60);
                    return `${days}d ${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
                }
                
                function initCharts() {
                    const cpuCtx = document.getElementById('cpuChart').getContext('2d');
                    const memoryCtx = document.getElementById('memoryChart').getContext('2d');
                    const networkCtx = document.getElementById('networkChart').getContext('2d');
                    const ioCtx = document.getElementById('ioChart').getContext('2d');
                    
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

                    networkChart = new Chart(networkCtx, {
                        type: 'line',
                        data: {
                            labels: [],
                            datasets: [
                                {
                                    label: 'Download Speed (Mbps)',
                                    data: [],
                                    borderColor: '#00cc88',
                                    tension: 0.1
                                },
                                {
                                    label: 'Upload Speed (Mbps)',
                                    data: [],
                                    borderColor: '#ff6b6b',
                                    tension: 0.1
                                },
                                {
                                    label: 'Total Speed (Mbps)',
                                    data: [],
                                    borderColor: '#4dabf7',
                                    tension: 0.1
                                }
                            ]
                        },
                        options: {
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    title: {
                                        display: true,
                                        text: 'Mbps'
                                    }
                                }
                            }
                        }
                    });

                    ioChart = new Chart(ioCtx, {
                        type: 'line',
                        data: {
                            labels: [],
                            datasets: [
                                {
                                    label: 'Read Speed (MB/s)',
                                    data: [],
                                    borderColor: '#4dabf7',
                                    tension: 0.1
                                },
                                {
                                    label: 'Write Speed (MB/s)',
                                    data: [],
                                    borderColor: '#ff922b',
                                    tension: 0.1
                                }
                            ]
                        },
                        options: {
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    title: {
                                        display: true,
                                        text: 'MB/s'
                                    }
                                }
                            }
                        }
                    });

                    setInterval(async () => {
                        const data = await fetch('/data').then(res => res.json());
                        
                        document.getElementById('cpu-usage').textContent = `${data.cpu_usage.toFixed(1)}%`;
                        document.getElementById('memory-usage').textContent = `${data.memory_usage.toFixed(1)}%`;
                        
                        currentNetworkUsage = (data.bytes_sent + data.bytes_recv) / 1024 ** 4;
                        document.getElementById('network-usage').textContent = `${currentNetworkUsage.toFixed(4)} TB`;

                        document.getElementById('download-speed').textContent = `${data.recv_speed.toFixed(2)} Mbps ↓`;
                        document.getElementById('upload-speed').textContent = `${data.sent_speed.toFixed(2)} Mbps ↑`;
                        document.getElementById('total-speed').textContent = `${data.total_speed.toFixed(2)} Mbps ↔`;

                        document.getElementById('read-speed').textContent = `${data.read_speed.toFixed(2)} MB/s Read`;
                        document.getElementById('write-speed').textContent = `${data.write_speed.toFixed(2)} MB/s Write`;

                        document.getElementById('countdown').textContent = `Until the end of the free subscription: ${formatTime(data.time_remaining)}`;
                        
                        if(data.time_remaining <= 0) {
                            document.getElementById('countdown').textContent = "Self-destructing...";
                            setTimeout(() => {
                                window.location.reload();
                            }, 1000);
                        }

                        const timeLabel = new Date().toLocaleTimeString();
                        
                        updateChart(cpuChart, data.cpu_usage, timeLabel);
                        updateChart(memoryChart, data.memory_usage, timeLabel);
                        updateChart(networkChart, [
                            data.recv_speed,
                            data.sent_speed,
                            data.total_speed
                        ], timeLabel);
                        updateChart(ioChart, [
                            data.read_speed,
                            data.write_speed
                        ], timeLabel);
                        
                        if(currentLimit && currentNetworkUsage >= currentLimit) {
                            if(currentCredentials) {
                                fetch('/shutdown', {
                                    method: 'POST',
                                    headers: {'Content-Type': 'application/json'},
                                    body: JSON.stringify(currentCredentials)
                                });
                            }
                        }
                        
                        updateLimitDisplay();
                    }, 1000);
                }

                initCharts();
            </script>
            <center><div class="Sabc-copyright">Powered by <a href="https://t.me/unknown_eng" data-wpel-link="internal" rel="follow noopener noreferrer">Rskhi</a></center></div>
        </body>
        </html>
    ''', network_limit=network_limit, cpu_cores=CPU_CORES, total_ram=TOTAL_RAM)

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
    data = request.json
    if data.get('username') != ADMIN_USERNAME or not check_password_hash(ADMIN_PASSWORD_HASH, data.get('password')):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    global network_limit
    network_limit = data.get('limit')
    save_limit(network_limit)
    return jsonify({'success': True})

@app.route('/shutdown', methods=['POST'])
def shutdown():
    data = request.json
    if data.get('username') != ADMIN_USERNAME or not check_password_hash(ADMIN_PASSWORD_HASH, data.get('password')):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    save_traffic_data()
    os.system('shutdown now')
    return jsonify({'success': True})

@app.route('/data')
def data():
    return jsonify(get_system_info())

if __name__ == '__main__':
    if check_self_destruct():
        self_destruct()
    
    logging.basicConfig(level=logging.INFO)
    
    if not os.path.exists(SECURITY_FILE):
        logging.error(f"فایل امنیتی '{SECURITY_FILE}' یافت نشد!")
        exit(1)
    
    if not os.path.exists(LIMIT_FILE):
        save_limit(None)
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    finally:
        save_traffic_data()
