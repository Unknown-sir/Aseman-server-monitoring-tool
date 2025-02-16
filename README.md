# Server Monitoring Tool
<div align="center"><img src="https://uploadkon.ir/uploads/d62516_25Screenshot-2025-02-16-225447.png" width="500"></div>
<div align="center"><br>

برای توضیحات <a href="https://github.com/Unknown-sir/server-monitoring-tool/blob/main/README-fa.md"> فارسی اینجا بزنید </a>
</div>
<br><br>
A simple yet powerful server monitoring tool built with Flask and psutil.

## Features
- Real-time monitoring of CPU, RAM, Disk, and Network usage.
- Admin panel for managing network limits and services.
- Historical data storage and visualization.
- Multi-language support (English, Persian).

# Installation script
To install, simply run the following commands on your server

```
git clone https://github.com/Unknown-sir/server-monitoring-tool.git
```
```
cd server-monitoring-tool
```
```
sudo apt install python3-pip
```
```
pip install -r requirements.txt
```
```
pip install flask psutil
```
```
pip install apscheduler
```
```
pip install flask psutil flask-limiter werkzeug
```
```
apt install npm
```
```
npm install pm2 -g
```
Modify the sec.json file with your desired username and password
Replace your username for "yourusername"
And replace your password for "yourpassword"
```
sudo nano sec.json
```
```
pm2 start server_monitor.py  -i max
```
```
chmod 600 sec.json
```

