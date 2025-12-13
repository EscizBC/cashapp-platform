# wsgi.py - исправленная версия
import os
import threading
import sys

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(__file__))

from app import app

def run_bot_in_thread():
    """Запускаем бота в отдельном потоке"""
    try:
        # Импортируем и запускаем бота
        import bot_runner
        
        # bot_runner сам запустит бота
        print("🤖 Telegram бот запущен в фоновом режиме")
    except Exception as e:
        print(f"⚠️  Не удалось запустить бота: {e}")

# Инициализация
print("=" * 60)
print("🚀 Запуск CashApp Pro Dashboard Manager")
print("=" * 60)

# Создаем папки
os.makedirs("sites", exist_ok=True)
print("📁 Папка 'sites' создана")

# Запускаем бота в отдельном потоке
bot_thread = threading.Thread(target=run_bot_in_thread, daemon=True)
bot_thread.start()

print("✅ Приложение готово к работе")
print("=" * 60)