# app.py - Flask приложение
import os
from flask import Flask, send_from_directory

app = Flask(__name__)

# Главная страница
@app.route('/')
def index():
    try:
        # Пытаемся прочитать index.html
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # Запасная страница
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>CashApp Pro Dashboard Manager</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #0A0F0A; color: #fff; }
                .container { max-width: 800px; margin: 0 auto; }
                h1 { color: #00D632; }
                .btn { display: inline-block; padding: 10px 20px; background: #00D632; color: white; 
                       text-decoration: none; border-radius: 5px; margin: 10px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>CashApp Pro Dashboard Manager</h1>
                <p>Система управления CashApp дашбордами через Telegram бота</p>
                <p>Бот запущен и работает!</p>
                <a href="/sites" class="btn">Просмотреть дашборды</a>
                <a href="/landing" class="btn">Лендинг</a>
            </div>
        </body>
        </html>
        """

# Список дашбордов
@app.route('/sites')
def sites_list():
    try:
        import main
        sites = main.site_manager.sites if hasattr(main, 'site_manager') else {}
    except:
        sites = {}
    
    html = """<!DOCTYPE html><html><head><title>Дашборды</title>
    <style>body{font-family:Arial;margin:40px;background:#0A0F0A;color:#fff;}
    .container{max-width:1200px;margin:0 auto;}h1{color:#00D632;}
    .site-card{background:#111511;padding:20px;margin:15px 0;border-radius:10px;border:1px solid #1C231C;}
    .btn{padding:8px 16px;background:#00D632;color:white;text-decoration:none;border-radius:5px;margin:5px;display:inline-block;}</style>
    </head><body><div class="container"><h1>Список дашбордов</h1>"""
    
    if not sites:
        html += "<p>Нет созданных дашбордов</p>"
    else:
        for site_id, site in sites.items():
            name = getattr(site, 'name', 'Без названия')
            desc = getattr(site, 'description', 'Нет описания')
            created = getattr(site, 'created_at', 'Неизвестно')
            if hasattr(created, 'strftime'):
                created = created.strftime('%d.%m.%Y %H:%M')
            accounts = len(getattr(site, 'accounts', []))
            
            html += f"""
            <div class="site-card">
                <h3>{name}</h3>
                <p>{desc}</p>
                <p>Создан: {created}</p>
                <p>Аккаунтов: {accounts}</p>
                <a href="/sites/site_{site_id}.html" class="btn" target="_blank">Открыть</a>
            </div>
            """
    
    html += "</div></body></html>"
    return html

# Статические файлы
@app.route('/sites/<path:filename>')
def serve_site(filename):
    return send_from_directory('sites', filename)

@app.route('/landing')
def serve_landing():
    return send_from_directory('sites', 'landing_page.html')

# Health check для Render
@app.route('/health')
def health():
    return {"status": "ok", "service": "CashApp Pro"}, 200

# Статические файлы из корня
@app.route('/<path:filename>')
def serve_root(filename):
    if os.path.exists(filename):
        return send_from_directory('.', filename)
    return "Not found", 404