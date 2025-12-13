# app.py
import asyncio
import threading
import os
from flask import Flask, send_from_directory
from waitress import serve

# Импортируем вашего бота
from main import main as bot_main, setup_static_routes, site_manager

# Создаем Flask приложение для обслуживания статических файлов
app = Flask(__name__)

# Маршрут для главной страницы
@app.route('/')
def index():
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
            <p>Для управления используйте Telegram бота</p>
            <a href="/sites" class="btn">Просмотреть все дашборды</a>
        </div>
    </body>
    </html>
    """

# Маршрут для отображения списка сайтов
@app.route('/sites')
def sites_list():
    sites = site_manager.sites if 'site_manager' in globals() else {}
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Дашборды - CashApp Pro</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #0A0F0A; color: #fff; }
            .container { max-width: 1200px; margin: 0 auto; }
            h1 { color: #00D632; }
            .site-card { background: #111511; padding: 20px; margin: 15px 0; border-radius: 10px; border: 1px solid #1C231C; }
            .btn { display: inline-block; padding: 8px 16px; background: #00D632; color: white; 
                   text-decoration: none; border-radius: 5px; margin: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Список дашбордов</h1>
    """
    
    if not sites:
        html += "<p>Нет созданных дашбордов</p>"
    else:
        for site_id, site in sites.items():
            html += f"""
            <div class="site-card">
                <h3>{site.name}</h3>
                <p>{site.description}</p>
                <p>Создан: {site.created_at.strftime('%d.%m.%Y %H:%M')}</p>
                <p>Аккаунтов: {len(site.accounts)}</p>
                <a href="/sites/site_{site_id}.html" class="btn" target="_blank">Открыть дашборд</a>
            </div>
            """
    
    html += """
        </div>
    </body>
    </html>
    """
    return html

# Обслуживание статических файлов из папки sites
@app.route('/sites/<path:filename>')
def serve_site(filename):
    return send_from_directory('sites', filename)

# Обслуживание лендинга
@app.route('/landing')
def serve_landing():
    return send_from_directory('sites', 'landing_page.html')

def run_bot():
    """Запускаем бота в отдельном потоке"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_main())

def run_web():
    """Запускаем веб-сервер"""
    port = int(os.getenv("PORT", 5000))
    print(f"🌐 Веб-сервер запущен на порту {port}")
    serve(app, host='0.0.0.0', port=port)

if __name__ == "__main__":
    print("🚀 Запуск CashApp Pro Dashboard Manager...")
    
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем веб-сервер в основном потоке
    run_web()