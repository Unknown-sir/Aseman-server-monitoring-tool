from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import psutil
import time
import os
import logging
from flask_babel import Babel, gettext as _

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# تنظیمات بین‌المللی‌سازی
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['LANGUAGES'] = ['en', 'fa']
babel = Babel(app)

@babel.localeselector
def get_locale():
    return session.get('lang', 'en')

# بقیه کدها بدون تغییر
# متغیرهای سیستمی
network_offset_sent = 0
network_offset_recv = 0
network_limit = None

def get_system_info():
    global network_offset_sent, network_offset_recv

    # اطلاعات CPU
    cpu_usage = psutil.cpu_percent(interval=0.5)
    
    # اطلاعات RAM
    memory_info = psutil.virtual_memory()
    memory_usage = memory_info.percent
    
    # اطلاعات شبکه
    net_io = psutil.net_io_counters()
    bytes_sent = net_io.bytes_sent - network_offset_sent
    bytes_recv = net_io.bytes_recv - network_offset_recv
    total_network_usage = bytes_sent + bytes_recv
    
    # اطلاعات دیسک
    disk_usage = psutil.disk_usage('/')
    
    # پردازش‌ها
    processes = [proc.info for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent'])]
    
    # Uptime
    uptime = time.time() - psutil.boot_time()
    
    return {
        'cpu_usage': cpu_usage,
        'memory_usage': memory_usage,
        'bytes_sent': bytes_sent,
        'bytes_recv': bytes_recv,
        'total_network_usage': total_network_usage,
        'disk_usage': disk_usage,
        'processes': processes,
        'uptime': uptime
    }

@app.route('/')
def index():
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Server Monitor</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body { background: #121212; color: white; }
                .stat { background: #1e1e1e; }
                .chart-container { background: #1e1e1e; }
            </style>
        </head>
        <body>
            <h1>{{ _('Server Monitoring') }}</h1>
            <div class="stats">
                <!-- آمار CPU، RAM، شبکه و ... -->
            </div>
            <div class="charts">
                <canvas id="cpuChart"></canvas>
                <canvas id="memoryChart"></canvas>
            </div>
            <button onclick="showAdminPanel()">{{ _('Admin Panel') }}</button>
            <!-- مودال‌های مدیریتی -->
        </body>
        </html>
    ''')

@app.route('/data')
def data():
    system_info = get_system_info()
    # بررسی لیمیت شبکه
    global network_limit
    if network_limit and network_limit > 0:
        total_usage_tb = system_info['total_network_usage'] / (1024 ** 4)
        if total_usage_tb >= network_limit:
            os.system('shutdown now')
    return jsonify(system_info)

@app.route('/reset', methods=['POST'])
def reset():
    global network_offset_sent, network_offset_recv
    data = request.json
    if data.get('password') == 'M2903293538m#':
        net_io = psutil.net_io_counters()
        network_offset_sent = net_io.bytes_sent
        network_offset_recv = net_io.bytes_recv
        logging.info('Network usage reset by admin')
        return jsonify({'success': True})
    else:
        return jsonify({'success': False})

@app.route('/set_limit', methods=['POST'])
def set_limit():
    global network_limit
    data = request.json
    limit = data.get('limit')
    if limit is not None and limit >= 0:
        network_limit = limit
        return jsonify({'success': True})
    else:
        return jsonify({'success': False})

@app.route('/set_language/<lang>')
def set_language(lang):
    session['lang'] = lang
    return redirect(url_for('index'))

@app.route('/manage_service', methods=['POST'])
def manage_service():
    service_name = request.json.get('service')
    action = request.json.get('action')
    os.system(f'systemctl {action} {service_name}')
    return jsonify({'success': True})

@app.route('/list_files', methods=['POST'])
def list_files():
    path = request.json.get('path', '/')
    files = os.listdir(path)
    return jsonify({'files': files})

if __name__ == '__main__':
    logging.basicConfig(filename='server_monitor.log', level=logging.INFO)
    app.run(host='0.0.0.0', port=5000, debug=True)
