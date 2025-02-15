یک ابزار ساده و در عین حال قدرتمند برای نظارت بر سرور که با Flask و psutil ساخته شده است.
ویژگی ها:
- نظارت بر زمان واقعی استفاده از CPU، RAM، دیسک و شبکه.
- پنل مدیریت برای مدیریت محدودیت های شبکه و خدمات.
- ذخیره سازی و تجسم داده های تاریخی
- پشتیبانی از چند زبان (انگلیسی، فارسی).
# اسکریپت نصب
برای نصب کافیست دستورات زیر را روی سرور خود اجرا کنید

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
فایل sec.json را با توجه به نام کاربری و پسورد دلخواه خود تغییر دهید
نام کاربری خود را به جای "yourusername" جایگذاری کنید
و پسورد خود را به جای "yourpassword" جایگذاری کنید
```
sudo nano sec.json
```
```
pm2 start server_monitor.py  -i max
```
```
chmod 600 sec.json
```

