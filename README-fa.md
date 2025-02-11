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
pip install -r requirements.txt
```
```
apt install npm
```
```
pm2 start server_monitor.py  -i max
```


