# wsgi.py
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app import app

# Инициализация
print("🚀 Запуск приложения на Render")

# Создаем папки
os.makedirs("sites", exist_ok=True)

print("✅ Приложение готово")