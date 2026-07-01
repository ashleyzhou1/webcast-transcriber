"""
serve.py

Local development server for the Earnings Call Player web app.
Supports HTTP range requests (needed for audio seeking in browser).

Run from the repo root:
    python web/serve.py

Then open: http://127.0.0.1:8000
"""

from flask import Flask, send_from_directory, request, Response, abort
import os

app = Flask(__name__)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(ROOT, 'web')
SAMPLES_DIR = os.path.join(ROOT, 'samples')


@app.route('/')
def index():
    return send_from_directory(WEB_DIR, 'index.html')


@app.route('/config.js')
def config():
    return send_from_directory(WEB_DIR, 'config.js')


@app.route('/data/<path:path>')
def caption_data(path):
    return send_from_directory(os.path.join(WEB_DIR, 'data'), path)


@app.route('/samples/<path:path>')
def sample_files(path):
    return send_from_directory(SAMPLES_DIR, path)


if __name__ == '__main__':
    print(f"Serving from: {ROOT}")
    print(f"Open: http://127.0.0.1:8000")
    app.run(port=8000, debug=False)