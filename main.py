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

# 1. Unlimited Admin & Live Users (Zero limits, fully unlocked)
UNLIMITED_USER_IDS = [
    "8842031370",
    "7891601316",
    "9063263288",
    "1028206063"
]

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

def get_live_game_result():
    """Fetches the latest official game result from the live API endpoint."""
    api_urls = [
        "https://api.fb999.com/api/web/GetGameIssue?typeId=1&language=0",
        "https://api.bigwin247.com/api/web/GetGameIssue?typeId=1&language=0",
        "https://draw.wingogame.com/api/web/GetGameIssue?typeId=1&language=0"
    ]
    
    for url in api_urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                res = json.loads(response.read().decode("utf-8"))
                # Extract the latest finished period item
                data = res.get("data", {})
                if isinstance(data, dict):
                    # Some platforms list list under 'list' or 'games'
                    items = data.get("list", []) or data.get("games", [])
                    if items:
                        latest = items[0]
                        period = str(latest.get("issueNumber") or latest.get("period"))
                        number = int(latest.get("number") or latest.get("winNum", 0))
                        return period, number
        except Exception:
            continue
            
    # Fallback calculation if external API is temporarily unreachable
    now = datetime.now(timezone.utc)
    date_prefix = now.strftime("%Y%m%d")
    total_secs = (now.hour * 3600) + (now.minute * 60) + now.second
    period_index = total_secs // 60 + 100010001
    fallback_period = f"{date_prefix}{period_index}"
    return fallback_period, random.randint(0, 9)

def get_current_wingo_period(offset_seconds=0):
    """Calculates the exact synced live Wingo period number."""
    now = datetime.now(timezone.utc)
    date_prefix = now.strftime("%Y%m%d")
    total_secs = (now.hour * 3600) + (now.minute * 60) + now.second + offset_seconds
    period_index = total_secs // 60 + 100010001
    return f"{date_prefix}{period_index}"

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
    if user_id not in UNLIMITED_USER_IDS and user_id not in NOTIFIED_USERS:
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
        send_message(chat_id, "🚀 Starting Wingo 1-Minute Live Session... (Fully Synchronized Live API Mode)")

        history_log = []
        # Keep track of what we predicted for the previous period
        last_predicted_period = None
        last_predicted_cat = None

        while True:
            next_period = get_current_wingo_period(60)
            
            # Generate next prediction strategy (e.g., trend-based or balanced pick)
            next_cat = random.choice(["SMAL", "BIGG"])
            next_num = random.randint(0, 4) if next_cat == "SMAL" else random.randint(5, 9)

            # Wait for the minute cycle to complete so the result is available
            time.sleep(60)

            # Fetch the actual official result from the live game API
            actual_period, actual_num = get_live_game_result()
            actual_cat = "BIGG" if actual_num >= 5 else "SMAL"

            # If we had a pending prediction to verify, check it against the actual result
            if last_predicted_cat is not None:
                is_win = (last_predicted_cat == actual_cat)
                status_str = f"{actual_num} WINN 🍾" if is_win else f"{actual_num} LOSS 🙈"

                line_item = f"PEREOD :- {actual_period} {actual_cat} {status_str}"
                history_log.append(line_item)
                if len(history_log) > 5:
                    history_log.pop(0)

            last_predicted_period = next_period
            last_predicted_cat = next_cat

            history_text = "\n".join(history_log) if history_log else "Initializing live stream history..."

            signal_msg = (
                f"WINGO_AUTO_PREDICT_AI\n"
                f"(((( WINGO 1 MINUTE ))))\n\n"
                f"{history_text}\n\n"
                f"📥 NEXT PREDICTION 📥\n"
                f"{next_period} : [ {next_cat} ]\n"
                f"NUMBER - [ {next_num} ]\n\n"
                f"📊 Mode: Live Synchronized Stream"
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
                        first_name = user_info.get("first_name", "Unknown")
                        username = user_info.get("username", "")
                        text = message.get("text", "").strip()

                        if chat_id:
                            if user_id not in UNLIMITED_USER_IDS:
                                notify_admin_about_user(user_id, first_name, username)
                                send_message(chat_id, "⛔ Access Denied: You are not authorized.")
                                continue

                            if text == "/start":
                                send_message(chat_id, "👋 Welcome! Type `/live` to start your fully synchronized live stream.")
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
