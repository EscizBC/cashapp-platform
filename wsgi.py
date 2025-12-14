# wsgi.py - исправленная версия
from web_app import app as application  # переименовываем для gunicorn

if __name__ == "__main__":
    application.run()