# app.py
from web_app import app

# Это нужно для gunicorn
application = app

if __name__ == "__main__":
    app.run()