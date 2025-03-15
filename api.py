from flask import Flask, jsonify

api_app = Flask(__name__)

@api_app.route('/api/status')
def status():
    return jsonify({'status': 'online'})

def start_api_server():
    # این تابع در صورت نیاز به API جداگانه استفاده می‌شود
    # در حالت فعلی نیازی به اجرای آن نیست
    pass
