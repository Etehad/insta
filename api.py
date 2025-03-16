from flask import Flask
import logging
import os

app = Flask(__name__)
logger = logging.getLogger(__name__)

@app.route('/')
def ping():
    return "API is alive!", 200

def start_api_server():
    port = int(os.getenv("PORT", 5000))  # Render.com پورت رو از متغیر PORT می‌گیره
    logger.info(f"Starting API server on port {port}...")
    app.run(host='0.0.0.0', port=port)
