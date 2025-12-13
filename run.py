# run.py - для локального запуска на Windows
import os
import threading
import asyncio
import sys
from app import app

def run_bot():
    """Запускаем бота из main.py"""
    try:
        import main
        
        # Создаем новую event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Запускаем бота
        print("🤖 Запуск Telegram бота...")
        loop.run_until_complete(main.main())
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Запуск CashApp Pro Dashboard Manager (Windows)")
    print("=" * 60)
    
    # Создаем папку sites если её нет
    os.makedirs("sites", exist_ok=True)
    
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем веб-сервер с waitress
    from waitress import serve
    port = int(os.getenv("PORT", 5000))
    
    print(f"🌐 Веб-сервер запущен на порту {port}")
    print(f"🔗 Доступ по адресу: http://localhost:{port}")
    print("=" * 60)
    
    serve(app, host='0.0.0.0', port=port)