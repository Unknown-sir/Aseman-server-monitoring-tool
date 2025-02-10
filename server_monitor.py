from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import psutil
import time
import os
import logging
from flask_babel import Babel, gettext as _

# تنظیمات اولیه
app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['LANGUAGES'] = {'en': 'English', 'fa': 'Persian'}

# مقداردهی Babel
babel = Babel(app)

@babel.localeselector
def get_locale():
    return session.get('lang', app.config['BABEL_DEFAULT_LOCALE'])

# متغیرهای مانیتورینگ
network_offset_sent = 0
network_offset_recv = 0
network_limit = None

def get_system_info():
    global network_offset_sent, network_offset_recv

    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    net_io = psutil.net_io_counters()
    disk = psutil.disk_usage('/')

    return {
        'cpu_usage': cpu_usage,
        'memory_usage': memory.percent,
        'bytes_sent': net_io.bytes_sent - network_offset_sent,
        'bytes_recv': net_io.bytes_recv - network_offset_recv,
        'disk_usage': disk.percent,
        'uptime': time.time() - psutil.boot_time()
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
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{{ _('Server Monitoring') }}</h1>
                
                <div class="stats">
                    <div class="stat-box">
                        <h3>{{ _('CPU Usage') }}</h3>
                        <span id="cpu-usage">0%</span>
                    </div>
                    <div class="stat-box">
                        <h3>{{ _('Memory Usage') }}</h3>
                        <span id="memory-usage">0%</span>
                    </div>
                    <div class="stat-box">
                        <h3>{{ _('Network Usage') }}</h3>
                        <span id="network-usage">0 MB</span>
                    </div>
                </div>

                <div class="chart-container">
                    <canvas id="cpuChart"></canvas>
                </div>
                
                <button onclick="showAdminPanel()">{{ _('Admin Panel') }}</button>
            </div>

            <script>
                let cpuChart;
                
                async function fetchData() {
                    const response = await fetch('/data');
                    return await response.json();
                }

                function updateUI(data) {
                    document.getElementById('cpu-usage').textContent = `${data.cpu_usage.toFixed(1)}%`;
                    document.getElementById('memory-usage').textContent = `${data.memory_usage.toFixed(1)}%`;
                    
                    const networkUsage = 
                        ((data.bytes_sent + data.bytes_recv) / 1024 / 1024).toFixed(2);
                    document.getElementById('network-usage').textContent = `${networkUsage} MB`;
                }

                function initCharts() {
                    const ctx = document.getElementById('cpuChart').getContext('2d');
                    cpuChart = new Chart(ctx, {
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
                }

                setInterval(async () => {
                    const data = await fetchData();
                    updateUI(data);
                    
                    // Update chart
                    const labels = cpuChart.data.labels;
                    const newLabel = new Date().toLocaleTimeString();
                    
                    if (labels.length > 15) labels.shift();
                    labels.push(newLabel);
                    
                    cpuChart.data.datasets[0].data.push(data.cpu_usage);
                    if (cpuChart.data.datasets[0].data.length > 15) {
                        cpuChart.data.datasets[0].data.shift();
                    }
                    
                    cpuChart.update();
                }, 1000);

                window.onload = initCharts;
            </script>
        </body>
        </html>
    ''')

@app.route('/data')
def data():
    return jsonify(get_system_info())

@app.route('/reset', methods=['POST'])
def reset_network():
    global network_offset_sent, network_offset_recv
    net_io = psutil.net_io_counters()
    network_offset_sent = net_io.bytes_sent
    network_offset_recv = net_io.bytes_recv
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(host='0.0.0.0', port=5000, debug=True)
