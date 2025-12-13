# app.py

from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__, static_folder='static', template_folder='.')

# Главная страница - отдаем index.html
@app.route('/')
def index():
    return render_template('index.html')

# Статические файлы (CSS, JS, изображения)
@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)