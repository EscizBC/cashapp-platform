# wsgi.py - главный файл для Render
import os
import threading
import asyncio
import sys

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(__file__))

from app import app

def run_bot():
    """Запускаем Telegram бота в отдельном потоке"""
    try:
        import main
        
        # Создаем новую event loop для асинхронного кода
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        print("🤖 Запуск Telegram бота...")
        loop.run_until_complete(main.main())
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        import traceback
        traceback.print_exc()

# Инициализация при старте
print("=" * 60)
print("🚀 Инициализация CashApp Pro Dashboard Manager")
print("=" * 60)

# Создаем необходимые папки
os.makedirs("sites", exist_ok=True)
print("📁 Папка 'sites' создана")

# Запускаем бота в отдельном потоке (daemon=True - поток закроется при завершении основного)
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()
print("✅ Telegram бот запущен в фоновом режиме")
print("=" * 60)

# Приложение для gunicorn
if __name__ == "__main__":
    # Для локального тестирования (не используется на Render)
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)