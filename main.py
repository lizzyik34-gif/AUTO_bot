import time
import json
import random
import urllib.request
import threading
import os
from datetime import datetime, timezone, date
from flask import Flask

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-win-go-key-2026")

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "9036832422:AAFkFnEZF_dbXupkkQ2cJ9DCxpfXyXPvXuM"

# Unlimited Admin & Live Users
UNLIMITED_USER_IDS = [
    "8842031370",
    "7891601316",
    "9063263288",
    "1028206063"
]

ACTIVE_SESSIONS = {}

def get_current_wingo_period():
    """Calculates the exact live Wingo period number based on UTC time."""
    now = datetime.now(timezone.utc)
    date_prefix = now.strftime("%Y%m%d")
    total_secs = (now.hour * 3600) + (now.minute * 60) + now.second
    period_index = total_secs // 60 + 100010001
    return int(f"{date_prefix}{period_index}")

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload_dict = {
        "chat_id": chat_id,
        "text": text
    }
    payload = json.dumps(payload_dict).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Error sending message to Telegram: {e}")

def run_live_session(chat_id, user_id, display_name):
    try:
        send_message(chat_id, f"🚀 Starting Wingo 1-Minute Live Session for @{display_name}...")
        
        history_log = []
        current_period = get_current_wingo_period()
        
        next_cat = random.choice(["SMAL", "BIGG"])
        next_num = random.randint(0, 4) if next_cat == "SMAL" else random.randint(5, 9)

        while ACTIVE_SESSIONS.get(user_id) == threading.current_thread():
            target_period = current_period
            predicted_cat = next_cat
            predicted_num = next_num

            current_period = get_current_wingo_period()
            while current_period <= target_period and ACTIVE_SESSIONS.get(user_id) == threading.current_thread():
                time.sleep(1)
                current_period = get_current_wingo_period()

            if ACTIVE_SESSIONS.get(user_id) != threading.current_thread():
                break

            actual_num = random.randint(0, 9)
            actual_cat = "BIGG" if actual_num >= 5 else "SMAL"
            
            is_win = (predicted_cat == actual_cat)
            status_str = f"{actual_num} WINN 🍾" if is_win else f"{actual_num} LOSS 🙈"

            line_item = f"PEREOD :- {target_period} {predicted_cat} {status_str}"
            history_log.append(line_item)
            if len(history_log) > 5:
                history_log.pop(0)

            next_cat = random.choice(["SMAL", "BIGG"])
            next_num = random.randint(0, 4) if next_cat == "SMAL" else random.randint(5, 9)

            history_text = "\n".join(history_log)

            signal_msg = (
                f"👑 **Stream Host**: @{display_name}\n"
                f"WINGO_AUTO_PREDICT_AI\n"
                f"(((( WINGO 1 MINUTE ))))\n\n"
                f"{history_text}\n\n"
                f"📥 NEXT PREDICTION 📥\n"
                f"{current_period} : [ {next_cat} ]\n"
                f"NUMBER - [ {next_num} ]\n\n"
                f"📊 Mode: 24/7 Synchronized Stream"
            )
            
            send_message(chat_id, signal_msg)
            
    except Exception as e:
        print(f"Error in run_live_session: {e}")

def telegram_bot_loop():
    print("Telegram Bot polling worker is starting...")
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=5)
    except Exception as e:
        print(f"Webhook delete error: {e}")

    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={offset}&timeout=30"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=35) as response:
                result_data = json.loads(response.read().decode("utf-8"))
                for result in result_data.get("result", []):
                    offset = result["update_id"] + 1

                    if "message" in result:
                        message = result["message"]
                        chat_id = message.get("chat", {}).get("id")
                        user_info = message.get("from", {})
                        user_id = str(user_info.get("id", ""))
                        username = user_info.get("username") or user_info.get("first_name", "User")
                        text = message.get("text", "").strip()

                        if chat_id:
                            if user_id not in UNLIMITED_USER_IDS:
                                send_message(chat_id, "⛔ Access Denied: You are not authorized.")
                                continue

                            if text == "/start":
                                send_message(chat_id, f"👋 Welcome @{username}! Type `/live` to start your 24/7 synchronized stream.")
                            elif text == "/live":
                                t = threading.Thread(target=run_live_session, args=(chat_id, user_id, username), daemon=True)
                                ACTIVE_SESSIONS[user_id] = t
                                t.start()

        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

@app.route("/")
def home():
    return "<h3>Wingo Big/Small Auto Predict AI Bot is Live & Running 24/7!</h3>"

if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
    bot_thread = threading.Thread(target=telegram_bot_loop, daemon=True)
    bot_thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
