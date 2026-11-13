import random
import urllib.request
import json
import time
import threading
import os
from datetime import datetime, timezone
from flask import Flask

app = Flask(__name__)

TOKEN = "9237583887:AAGfUABC5pb4X8sI40If2BMm0surTrCtnRA"

# 🔒 SECURITY LOCK: Only allowed user IDs can control /live and /stop
ALLOWED_USER_IDS = [8842031370, 9063263288, 7891601316]

# 👉 TARGET GROUP CHAT ID
TARGET_GROUP_CHAT_ID = -1004469316146

# 📊 ACTIVE GROUPS STREAM TRACKER
ACTIVE_STREAMS = {"running": False}

@app.route("/")
def health_check():
    return "FB999 Non-Stop Signal Bot is Running!"

def get_1min_period(offset_minutes=1):
    now = datetime.now(timezone.utc)
    total_minutes = (now.hour * 60) + now.minute + offset_minutes
    date_prefix = now.strftime("%Y%m%d")
    period_suffix = 100010000 + total_minutes
    return f"{date_prefix}{period_suffix}"

def generate_smart_signal(session):
    if session["consecutive_losses"] >= 2 and session["last_prediction"]:
        size = "Small" if session["last_prediction"] == "Big" else "Big"
    else:
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

    accuracy = random.randint(88, 98) if session["consecutive_losses"] >= 2 else random.randint(75, 95)
    session["last_prediction"] = size

    return number, size, color, accuracy

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Error sending message to {chat_id}: {e}")

def continuous_signal_worker():
    print(">>> NON-STOP BACKGROUND WORKER STARTED <<<")
    session = {"consecutive_losses": 0, "last_prediction": None}
    last_sent_period = None

    while ACTIVE_STREAMS["running"]:
        current_period = get_1min_period(offset_minutes=1)

        if current_period != last_sent_period:
            number, size, color, accuracy = generate_smart_signal(session)

            signal_text = (
                f"🚨 **FB999 LIVE 1-MIN SIGNAL** 🚨\n\n"
                f"🔹 **Period:** `{current_period}`\n"
                f"🎯 **Prediction:** **{size.upper()}** (`{number}`)\n"
                f"🎨 **Color:** {color}\n"
                f"🔥 **Win Rate:** `{accuracy}%`\n\n"
                f"⏳ *Non-stop automated live feed active...*"
            )
            send_message(TARGET_GROUP_CHAT_ID, signal_text)
            last_sent_period = current_period

        time.sleep(3)

    print(">>> NON-STOP BACKGROUND WORKER STOPPED <<<")

def check_updates():
    offset = 0
    print(">>> BOT POLLING ACTIVE (NON-STOP STREAM MODE) <<<")
    
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

                user_id = message["from"]["id"]
                chat_id = message["chat"]["id"]
                text = message["text"].strip().lower().split("@")[0]

                if user_id not in ALLOWED_USER_IDS:
                    continue

                if text == "/live":
                    if ACTIVE_STREAMS["running"]:
                        send_message(chat_id, "ℹ️ **Live signal stream is already running non-stop!**")
                        continue

                    ACTIVE_STREAMS["running"] = True
                    send_message(TARGET_GROUP_CHAT_ID, "🚀 **NON-STOP LIVE SIGNALS STARTED!**\nSignals will drop every minute continuously until you send `/stop`.")
                    if chat_id != TARGET_GROUP_CHAT_ID:
                        send_message(chat_id, "✅ Non-stop stream successfully activated in your group!")

                    threading.Thread(target=continuous_signal_worker, daemon=True).start()

                elif text == "/stop":
                    if not ACTIVE_STREAMS["running"]:
                        send_message(chat_id, "ℹ️ No active stream is currently running.")
                        continue

                    ACTIVE_STREAMS["running"] = False
                    send_message(TARGET_GROUP_CHAT_ID, "🛑 **Live signal stream stopped by admin.**")
                    if chat_id != TARGET_GROUP_CHAT_ID:
                        send_message(chat_id, "✅ Live stream has been successfully halted.")

                elif text == "/start":
                    send_message(
                        chat_id,
                        "👋 **FB999 Non-Stop Bot Ready!**\n\n"
                        "Type `/live` to start continuous signals in your group.\n"
                        "Type `/stop` anytime to halt the stream."
                    )

        except Exception as e:
            print(f"Network glitch ({e}), retrying in 3 seconds...")
            time.sleep(3)

# --- MODULE-LEVEL STARTUP GUARD (FOR RENDER / GUNICORN) ---
_polling_started = False
if not _polling_started:
    _polling_started = True
    threading.Thread(target=check_updates, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
