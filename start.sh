#!/bin/bash
# start.sh

# Запускаем Flask веб-сервер в фоне
gunicorn wsgi:application --bind 0.0.0.0:$PORT &

# Запускаем Telegram бота
python main.py