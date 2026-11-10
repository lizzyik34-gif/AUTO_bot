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

# 1. Unlimited Admin IDs
UNLIMITED_USER_IDS = ["8842031370", "7891601316"]

# 2. Authorized User ID for `/live`
LIVE_USER_IDS = ["1028206063"]

DATA_FILE = "live_sessions.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving data file: {e}")

NOTIFIED_USERS = set()

def get_current_wingo_period(offset_seconds=0):
    """Calculates the exact live Wingo period number based on current UTC time & 60s intervals."""
    now = datetime.now(timezone.utc)
    date_prefix = now.strftime("%Y%m%d")
    total_secs = (now.hour * 3600) + (now.minute * 60) + now.second + offset_seconds
    period_index = total_secs // 60 + 100010001
    return f"{date_prefix}{period_index}"

def get_big_small_prediction():
    """Generates BIG or SMALL prediction with corresponding numbers."""
    category = random.choice(["SMAL", "BIGG"])
    if category == "SMAL":
        num = random.randint(0, 4)
    else:
        num = random.randint(5, 9)
    return category, num

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload_dict = {
        "chat_id": chat_id,
        "text": text
    }
    payload = json.dumps(payload_dict).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"Error sending message to Telegram: {e}")

def notify_admin_about_user(user_id, first_name, username):
    all_allowed = UNLIMITED_USER_IDS + LIVE_USER_IDS
    if user_id not in all_allowed and user_id not in NOTIFIED_USERS:
        NOTIFIED_USERS.add(user_id)
        admin_msg = (
            f"🔔 Unauthorized User Attempt!\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Name: {first_name}\n"
            f"🔗 Username: @{username if username else 'None'}\n"
            f"🆔 User ID: {user_id}\n"
            f"🚫 Status: Blocked"
        )
        send_message("8842031370", admin_msg)

def run_live_session(chat_id, user_id):
    try:
        data = load_data()
        today_str = str(date.today())

        if user_id not in data or data[user_id]["date"] != today_str:
            data[user_id] = {"date": today_str, "batches_run": 0}

        if data[user_id]["batches_run"] >= 2 and user_id not in UNLIMITED_USER_IDS:
            send_message(chat_id, "⛔ Daily Limit Reached: You have completed your 2 daily live sessions (100 wins total). Try again tomorrow!")
            return

        data[user_id]["batches_run"] += 1
        save_data(data)

        send_message(chat_id, "🚀 Starting Wingo 1-Minute Live Session... (Target: 50 Wins)")

        target_wins = 50
        current_wins = 0
        history_log = []

        while current_wins < target_wins:
            current_period = get_current_wingo_period(0)
            next_period = get_current_wingo_period(60)

            cat, num = get_big_small_prediction()
            
            # Simulated result check matching your screenshot format
            is_win = random.choice([True, True, False, True])
            if is_win:
                current_wins += 1
                status_str = f"{num} WINN 🍾"
            else:
                status_str = f"{num} LOSS 🙈"

            line_item = f"PEREOD :- {current_period} {cat} {status_str}"
            history_log.append(line_item)
            if len(history_log) > 5:
                history_log.pop(0)

            next_cat, next_num = get_big_small_prediction()
            history_text = "\n".join(history_log)

            signal_msg = (
                f"WINGO_AUTO_PREDICT_AI\n"
                f"(((( WINGO 1 MINUTE ))))\n\n"
                f"{history_text}\n\n"
                f"📥 NEXT PREDICTION 📥\n"
                f"{next_period} : [ {next_cat} ]\n"
                f"NUMBER - [ {next_num} ]\n\n"
                f"📊 Progress: {current_wins}/50 Wins"
            )
            
            send_message(chat_id, signal_msg)
            
            # Wait precisely for 60 seconds for the next 1-minute period cycle
            time.sleep(60)

        send_message(chat_id, f"🎉 Batch Complete! Reached 50 wins. Type /live to start your next batch.")
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
                        first_name = user_info.get("first_name", "Unknown")
                        username = user_info.get("username", "")
                        text = message.get("text", "").strip()

                        if chat_id:
                            if user_id not in UNLIMITED_USER_IDS and user_id not in LIVE_USER_IDS:
                                notify_admin_about_user(user_id, first_name, username)
                                send_message(chat_id, "⛔ Access Denied: You are not authorized.")
                                continue

                            if text == "/start":
                                send_message(chat_id, "👋 Welcome! Type /live to start your automatic 1-minute live Big/Small prediction stream.")
                            elif text == "/live":
                                t = threading.Thread(target=run_live_session, args=(chat_id, user_id), daemon=True)
                                t.start()

        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

@app.route("/")
def home():
    return "<h3>Wingo Big/Small Auto Predict AI Bot is Live & Running!</h3>"

if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
    bot_thread = threading.Thread(target=telegram_bot_loop, daemon=True)
    bot_thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
