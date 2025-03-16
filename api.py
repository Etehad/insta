from flask import Flask
import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)

@app.route('/')
def ping():
    return "API is alive!", 200

def start_api_server():
    logger.info("Starting API server...")
    app.run(host='0.0.0.0', port=5000)
