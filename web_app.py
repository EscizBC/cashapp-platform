# web_app.py
from flask import Flask, send_from_directory
import os

app = Flask(__name__)

# Импортируем менеджер сайтов для показа списка
try:
    from main import site_manager
    print("✅ Менеджер сайтов загружен в веб-приложение.")
except ImportError:
    print("⚠️  Менеджер сайтов не найден.")
    site_manager = None

@app.route('/')
def index():
    """Главная страница."""
    try:
        return send_from_directory('.', 'index.html')
    except:
        return """
        <html><body style='margin:40px;font-family:Arial;'>
            <h1>CashApp Pro Dashboard Manager</h1>
            <p>🤖 Бот запущен в отдельном процессе.</p>
            <p>🌐 Сайт работает на Flask.</p>
            <p><a href='/sites'>Список дашбордов</a></p>
        </body></html>
        """

@app.route('/sites')
def list_sites():
    """Страница со списком всех дашбордов."""
    sites = site_manager.sites if site_manager else {}
    
    html = """<html><head><title>Дашборды</title><style>
        body{font-family:Arial;margin:40px;background:#0A0F0A;color:#fff;}
        .container{max-width:1200px;margin:0 auto;} h1{color:#00D632;}
        .site-card{background:#111511;padding:20px;margin:15px 0;border-radius:10px;border:1px solid #1C231C;}
        .btn{padding:8px 16px;background:#00D632;color:white;text-decoration:none;border-radius:5px;margin:5px;}
    </style></head><body><div class='container'><h1>Дашборды</h1>"""
    
    if not sites:
        html += "<p>Нет созданных дашбордов.</p>"
    else:
        for site_id, site in sites.items():
            html += f"""
            <div class='site-card'>
                <h3>{getattr(site, 'name', 'Без названия')}</h3>
                <p>{getattr(site, 'description', 'Нет описания')}</p>
                <p>Аккаунтов: {len(getattr(site, 'accounts', []))}</p>
                <a href='/sites/site_{site_id}.html' class='btn' target='_blank'>Открыть</a>
            </div>
            """
    html += "</div></body></html>"
    return html

@app.route('/sites/<path:filename>')
def serve_site(filename):
    """Отдает HTML-файлы дашбордов."""
    return send_from_directory('sites', filename)

@app.route('/landing')
def landing():
    """Отдает лендинг-страницу."""
    return send_from_directory('sites', 'landing_page.html')

@app.route('/health')
def health():
    """Проверка здоровья для Render."""
    return {"status": "ok", "service": "web"}, 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)