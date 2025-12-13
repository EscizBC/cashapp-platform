# bot_runner.py - только для запуска бота
import asyncio
import os
import sys

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(__file__))

async def run_bot():
    """Запускает только бота без веб-сервера"""
    try:
        from main import main as bot_main
        await bot_main()
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🤖 Запуск Telegram бота...")
    asyncio.run(run_bot())