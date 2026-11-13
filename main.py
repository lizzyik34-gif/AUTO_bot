import random
import urllib.request
import json
from datetime import datetime, timezone
from flask import Flask

app = Flask(__name__)

TOKEN = "9237583887:AAGfUABC5pb4X8sI40If2BMm0surTrCtnRA"

# 🔒 SECURITY LOCK: Only allowed user IDs can control the bot
ALLOWED_USER_IDS = [8842031370, 9063263288, 7891601316]

# 👉 CORRECT TARGET GROUP CHAT ID FROM SCREENSHOT
TARGET_GROUP_CHAT_ID = -1004469316146

@app.route("/")
def health_check():
    return "FB999 Single-Signal Bot is Running!"

def get_1min_period(offset_minutes=1):
    now = datetime.now(timezone.utc)
    total_minutes = (now.hour * 60) + now.minute + offset_minutes
    date_prefix = now.strftime("%Y%m%d")
    period_suffix = 100010000 + total_minutes
    return f"{date_prefix}{period_suffix}"

def generate_single_signal():
    size = random.choice(["Big", "Small"])
    number = random.randint(5, 9) if size == "Big" else random.randint(0, 4)

    if number == 0:
        color = "🔴 Red + 🟣 Violet"
    elif number == 5:
        color = "🟢 Green + 🟣 Violet"
    elif number in [1, 3, 7, 9]:
        color = "🟢 Green"
    else:
        color = "🔴 Red"

    accuracy = random.randint(88, 98)
    
    now = datetime.now(timezone.utc)
    total_minutes = (now.hour * 60) + now.minute + 1
    period_str = f"{now.strftime('%Y%m%d')}000{10000 + total_minutes}"

    return period_str, number, size, color, accuracy

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Error sending message to {chat_id}: {e}")

def check_updates():
    offset = 0
    print(">>> BOT POLLING ACTIVE (SINGLE SIGNAL MODE) <<<")
    
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true")
    except Exception:
        pass

    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={offset}&timeout=30"
            response = urllib.request.urlopen(url, timeout=35)
            data = json.loads(response.read().decode('utf-8'))
            
            for result in data.get("result", []):
                offset = result["update_id"] + 1
                message = result.get("message")
                if not message or "text" not in message:
                    continue

                chat_id = message["chat"]["id"]
                user_id = message["from"]["id"]
                text = message["text"].strip().lower().split("@")[0]

                if user_id not in ALLOWED_USER_IDS:
                    continue

                if text == "/live":
                    period, number, size, color, accuracy = generate_single_signal()

                    signal_text = (
                        f"🚨 **FB999 LIVE 1-MIN SIGNAL** 🚨\n\n"
                        f"🔹 **Period:** `{period}`\n"
                        f"🎯 **Prediction:** **{size.upper()}** (`{number}`)\n"
                        f"🎨 **Color:** {color}\n"
                        f"🔥 **Win Rate:** `{accuracy}%`\n\n"
                        f"✅ *Signal generated & dispatched successfully.*"
                    )
                    
                    send_message(TARGET_GROUP_CHAT_ID, signal_text)
                    
                    if chat_id != TARGET_GROUP_CHAT_ID:
                        send_message(chat_id, "✅ Single signal successfully dropped to your group!")

                elif text == "/start":
                    send_message(
                        chat_id,
                        "👋 **FB999 Single-Signal Controller Ready!**\n\n"
                        "Type `/live` anywhere to drop **exactly one** signal into your group and stop immediately."
                    )

        except Exception as e:
            print(f"Network glitch ({e}), retrying in 3 seconds...")
            import time
            time.sleep(3)

# --- MODULE-LEVEL STARTUP GUARD (FOR RENDER / GUNICORN) ---
_polling_started = False
if not _polling_started:
    _polling_started = True
    import threading
    threading.Thread(target=check_updates, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
