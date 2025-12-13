# app.py - исправленная версия
import os
import sys
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, send_from_directory, request, jsonify

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(__file__))

# Конфигурация
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8534738281:AAGrXV_OEEKdP1hEGKWNTzD1WzStkF6d2Ys")
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME", "")
WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"
WEBHOOK_URL = f"https://{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else ""

app = Flask(__name__)

# Глобальный executor для обработки вебхуков
executor = ThreadPoolExecutor(max_workers=3)

# Импортируем бота (ленивая загрузка)
def get_bot_and_dp():
    """Ленивая загрузка бота и диспетчера"""
    try:
        from main import bot, dp
        return bot, dp
    except ImportError as e:
        print(f"❌ Ошибка импорта бота: {e}")
        return None, None

# Главная страница
@app.route('/')
def index():
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>CashApp Pro Dashboard</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background: #0A0F0A; color: #fff; }}
                .container {{ max-width: 800px; margin: 0 auto; }}
                h1 {{ color: #00D632; }}
                .status {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
                .success {{ background: #00D63220; border: 1px solid #00D632; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>CashApp Pro Dashboard Manager</h1>
                <div class="status success">
                    <strong>Статус:</strong> Система работает
                </div>
                <p>Telegram бот: {'Активен' if WEBHOOK_HOST else 'В разработке'}</p>
                <p>Вебхук: {WEBHOOK_URL if WEBHOOK_HOST else 'Не настроен'}</p>
                <p><a href="/sites">Просмотреть дашборды</a> | <a href="/landing">Лендинг</a></p>
            </div>
        </body>
        </html>
        """

# ВЕБХУК для Telegram - ОСНОВНОЙ ОБРАБОТЧИК
@app.route(WEBHOOK_PATH, methods=['POST'])
def handle_telegram_webhook():  # ИЗМЕНИЛ ИМЯ ФУНКЦИИ
    """Основной обработчик вебхука от Telegram"""
    try:
        update_data = request.get_json()
        
        if not update_data:
            return jsonify({"error": "No JSON data"}), 400
        
        # Запускаем обработку в фоне через ThreadPoolExecutor
        executor.submit(process_webhook_background, update_data)
        
        return '', 200
        
    except Exception as e:
        print(f"❌ Ошибка получения вебхука: {e}")
        return jsonify({"error": str(e)}), 500

def process_webhook_background(update_data):
    """Фоновая обработка вебхука в отдельном потоке"""
    try:
        # Импортируем здесь, чтобы избежать проблем с импортами
        import sys
        import os
        sys.path.insert(0, os.path.dirname(__file__))
        
        from main import bot, dp
        from aiogram.types import Update
        
        # Создаем новую event loop для этого потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        update = Update(**update_data)
        
        # Обрабатываем обновление
        loop.run_until_complete(dp.feed_update(bot, update))
        
        print(f"✅ Вебхук обработан в фоне")
        
        # Аккуратно закрываем loop
        loop.stop()
        loop.close()
        
    except Exception as e:
        print(f"❌ Ошибка фоновой обработки: {e}")
        import traceback
        traceback.print_exc()

# Список дашбордов
@app.route('/sites')
def list_sites():  # ИЗМЕНИЛ ИМЯ ФУНКЦИИ
    try:
        from main import site_manager
        sites = site_manager.sites
    except:
        sites = {}
    
    html = """<!DOCTYPE html><html><head><title>Дашборды</title>
    <style>body{font-family:Arial;margin:40px;background:#0A0F0A;color:#fff;}
    .container{max-width:1200px;margin:0 auto;}h1{color:#00D632;}
    .site-card{background:#111511;padding:20px;margin:15px 0;border-radius:10px;border:1px solid #1C231C;}
    .btn{padding:8px 16px;background:#00D632;color:white;text-decoration:none;border-radius:5px;margin:5px;display:inline-block;}
    </style></head><body><div class="container"><h1>Список дашбордов</h1>"""
    
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
def serve_site_file(filename):  # ИЗМЕНИЛ ИМЯ ФУНКЦИИ
    return send_from_directory('sites', filename)

@app.route('/landing')
def serve_landing_page():  # ИЗМЕНИЛ ИМЯ ФУНКЦИИ
    return send_from_directory('sites', 'landing_page.html')

# Health check
@app.route('/health')
def health_check():  # ИЗМЕНИЛ ИМЯ ФУНКЦИИ
    bot, dp = get_bot_and_dp()
    return {
        "status": "ok",
        "bot_initialized": bool(bot and dp),
        "webhook_url": WEBHOOK_URL,
        "webhook_path": WEBHOOK_PATH
    }, 200

# Тестовая страница для проверки вебхука
@app.route('/webhook_test')
def webhook_test_page():  # ИЗМЕНИЛ ИМЯ ФУНКЦИИ
    return f"""
    <html>
    <head><title>Webhook Test</title></head>
    <body>
        <h1>Webhook Test Page</h1>
        <p>Token: {TELEGRAM_TOKEN[:15]}...</p>
        <p>Webhook URL: {WEBHOOK_URL}</p>
        <p>Webhook Path: {WEBHOOK_PATH}</p>
        <p>Host: {WEBHOOK_HOST}</p>
        <p><a href="/">На главную</a></p>
    </body>
    </html>
    """

# Функция для установки вебхука при запуске
def setup_webhook_on_start():
    """Установка вебхука при запуске приложения"""
    if not WEBHOOK_HOST:
        print("⚠️  WEBHOOK_HOST не установлен, вебхук не будет настроен")
        return
    
    try:
        # Импортируем бота
        bot, _ = get_bot_and_dp()
        if not bot:
            print("❌ Бот не инициализирован для установки вебхука")
            return
        
        # Устанавливаем вебхук асинхронно
        async def set_webhook_async():
            try:
                await bot.delete_webhook(drop_pending_updates=True)
                await bot.set_webhook(
                    url=WEBHOOK_URL,
                    drop_pending_updates=True
                )
                print(f"✅ Вебхук установлен: {WEBHOOK_URL}")
            except Exception as e:
                print(f"❌ Ошибка установки вебхука: {e}")
        
        # Запускаем в отдельном потоке
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(set_webhook_async())
        
    except Exception as e:
        print(f"❌ Ошибка при настройке вебхука: {e}")

# Инициализация при старте
print("=" * 60)
print("🚀 Запуск Flask приложения")
print("=" * 60)
print(f"🤖 Токен: {TELEGRAM_TOKEN[:10]}...")
print(f"🌐 Хост: {WEBHOOK_HOST or 'Не указан'}")
print(f"🔗 Вебхук URL: {WEBHOOK_URL or 'Не настроен'}")
print("=" * 60)

# Устанавливаем вебхук при запуске (если указан хост)
if WEBHOOK_HOST:
    # Запускаем в отдельном потоке с задержкой
    threading.Timer(5.0, setup_webhook_on_start).start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)