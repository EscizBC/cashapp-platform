# app.py - полная версия с вебхуком
import os
import sys
from flask import Flask, send_from_directory, request
import asyncio
import threading

# Импортируем бота из main
sys.path.insert(0, os.path.dirname(__file__))

# Конфигурация
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8534738281:AAGrXV_OEEKdP1hEGKWNTzD1WzStkF6d2Ys")
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME", "")
WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"
WEBHOOK_URL = f"https://{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else ""

app = Flask(__name__)

# Глобальные переменные для бота
bot = None
dp = None

def init_bot():
    """Инициализация бота в фоновом режиме"""
    global bot, dp
    
    try:
        from main import bot as main_bot, dp as main_dp
        bot = main_bot
        dp = main_dp
        print("✅ Бот инициализирован в app.py")
        
        # Устанавливаем вебхук при запуске
        if WEBHOOK_HOST and bot:
            async def set_webhook():
                try:
                    await bot.delete_webhook(drop_pending_updates=True)
                    await bot.set_webhook(
                        url=WEBHOOK_URL,
                        drop_pending_updates=True
                    )
                    print(f"✅ Вебхук установлен: {WEBHOOK_URL}")
                except Exception as e:
                    print(f"❌ Ошибка установки вебхука: {e}")
            
            # Запускаем асинхронно
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(set_webhook())
            
    except Exception as e:
        print(f"⚠️ Не удалось инициализировать бота: {e}")

# Главная страница
@app.route('/')
def index():
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """
        <!DOCTYPE html>
        <html>
        <head><title>CashApp Pro</title>
        <style>body{font-family:Arial;margin:40px;background:#0A0F0A;color:#fff;}
        .container{max-width:800px;margin:0 auto;}h1{color:#00D632;}
        .btn{display:inline-block;padding:10px 20px;background:#00D632;color:white;
        text-decoration:none;border-radius:5px;margin:10px;}</style>
        </head>
        <body><div class="container">
        <h1>CashApp Pro Dashboard Manager</h1>
        <p>🤖 Бот работает: <span style="color:#00D632">●</span> Активен</p>
        <p>🌐 Вебхук: {}</p>
        <a href="/sites" class="btn">Просмотреть дашборды</a>
        <a href="/landing" class="btn">Лендинг</a>
        </div></body></html>
        """.format("Настроен" if WEBHOOK_HOST else "Не настроен")

# Вебхук для Telegram
@app.route(WEBHOOK_PATH, methods=['POST'])
async def telegram_webhook():
    """Обработчик вебхука от Telegram"""
    if not bot or not dp:
        return 'Bot not initialized', 503
    
    try:
        # Получаем обновление
        update_data = request.get_json()
        
        # Обрабатываем через диспетчер
        from aiogram.types import Update
        update = Update(**update_data)
        
        # Запускаем обработку
        await dp.feed_update(bot, update)
        
        return '', 200
    except Exception as e:
        print(f"❌ Ошибка обработки вебхука: {e}")
        import traceback
        traceback.print_exc()
        return '', 500

# Список дашбордов
@app.route('/sites')
def sites_list():
    try:
        from main import site_manager
        sites = site_manager.sites if hasattr(site_manager, 'sites') else {}
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
            accounts = len(getattr(site, 'accounts', []))
            
            html += f"""
            <div class="site-card">
                <h3>{name}</h3>
                <p>{desc}</p>
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

# Health check
@app.route('/health')
def health():
    return {"status": "ok", "bot": "active" if bot else "inactive", "webhook": WEBHOOK_URL}, 200

# Проверка вебхука
@app.route('/webhook_test')
def webhook_test():
    return f"""
    <h1>Проверка вебхука</h1>
    <p>Токен: {TELEGRAM_TOKEN[:10]}...</p>
    <p>Хост: {WEBHOOK_HOST}</p>
    <p>Полный URL: {WEBHOOK_URL}</p>
    <p>Путь: {WEBHOOK_PATH}</p>
    <a href="/">На главную</a>
    """

# Инициализируем бота при запуске
print("🚀 Инициализация Flask приложения...")
init_bot()