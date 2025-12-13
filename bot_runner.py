# bot_runner.py
import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from main import bot, dp, site_manager

async def main():
    """Запускает только Telegram бота в режиме polling."""
    os.makedirs("sites", exist_ok=True)
    site_manager.load_from_json()
    
    print("=" * 60)
    print("🤖 ЗАПУСК ТЕЛЕГРАМ БОТА (Polling Mode)")
    print("=" * 60)
    
    # КРИТИЧЕСКИ ВАЖНО: удаляем старый вебхук
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Старый вебхук удален.")
    except Exception as e:
        print(f"⚠️  Предупреждение: {e}")
    
    # Запускаем long-polling
    print("🔄 Бот запущен и ожидает сообщений...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())