# wsgi.py
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app import app

# Инициализация
print("=" * 60)
print("🚀 Запуск приложения на Render")
print("=" * 60)

# Создаем папки
os.makedirs("sites", exist_ok=True)
print("📁 Папка 'sites' создана")

print("✅ Приложение готово")
print("=" * 60)

# Для gunicorn
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)