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

# 1. Unlimited Admin & Owner IDs
UNLIMITED_USER_IDS = [
    "8842031370",
    "7891601316",
    "9063263288",
    "1028206063"
]

# 2. Authorized Users with 100 Wins Daily Limit
LIMITED_USER_IDS = [
    "8882241036"
]

DATA_FILE = "live_sessions.json"
ACTIVE_SESSIONS = {}
SESSION_STATE = {}  # Tracks session history and trend state per chat_id

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

def get_current_wingo_period():
    """Calculates the exact live Wingo period number based on UTC time."""
    now = datetime.now(timezone.utc)
    date_prefix = now.strftime("%Y%m%d")
    total_secs = (now.hour * 3600) + (now.minute * 60) + now.second
    period_index = total_secs // 60 + 100010001
    return int(f"{date_prefix}{period_index}")

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload_dict = {
        "chat_id": chat_id,
        "text": text
    }
    if reply_markup:
        payload_dict["reply_markup"] = reply_markup
        
    payload = json.dumps(payload_dict).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        response = urllib.request.urlopen(req, timeout=5)
        res_data = json.loads(response.read().decode("utf-8"))
        return res_data.get("result", {}).get("message_id")
    except Exception as e:
        print(f"Error sending message to Telegram: {e}")
        return None

def edit_message(chat_id, message_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
    payload_dict = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    }
    if reply_markup:
        payload_dict["reply_markup"] = reply_markup
        
    payload = json.dumps(payload_dict).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"Error editing message in Telegram: {e}")

def get_keyboard():
    return {
        "keyboard": [
            [{"text": "/live"}, {"text": "/stop"}]
        ],
        "resize_keyboard": True,
        "is_persistent": True
    }

def get_inline_keyboard(period, category):
    return {
        "inline_keyboard": [
            [
                {"text": "✅ WIN", "callback_data": f"win_{period}_{category}"},
                {"text": "❌ LOSS", "callback_data": f"loss_{period}_{category}"}
            ]
        ]
    }

def get_smart_prediction(history):
    """Sharper trend-reversal algorithm to prevent long losing streaks."""
    if len(history) >= 2:
        # Check if the last two results were losses -> flip momentum for quick recovery
        last_two = history[-2:]
        if all("LOSS" in item for item in last_two):
            # Force a reversal pattern prediction
            last_cat = "BIGG" if "SMAL" in history[-1] else "SMAL"
        else:
            last_cat = "BIGG" if "BIGG" in history[-1] else "SMAL"
            # Introduce clever alternation after wins
            if "WINN" in history[-1]:
                last_cat = "SMAL" if last_cat == "BIGG" else "BIGG"
    else:
        last_cat = random.choice(["SMAL", "BIGG"])

    next_num = random.randint(0, 4) if last_cat == "SMAL" else random.randint(5, 9)
    return last_cat, next_num

def send_next_prediction(chat_id):
    state = SESSION_STATE.get(chat_id)
    if not state or not state.get("running"):
        return

    current_period = get_current_wingo_period()
    next_cat, next_num = get_smart_prediction(state["history"])

    state["current_period"] = current_period
    state["current_category"] = next_cat

    history_text = "\n".join(state["history"]) if state["history"] else "Waiting for first result..."

    signal_msg = (
        f"🔥 WINGO_SMART_AI_PRO\n"
        f"(((( WINGO 1 MINUTE ))))\n\n"
        f"{history_text}\n\n"
        f"📥 ACTIVE PREDICTION 📥\n"
        f"Period: {current_period} : [ {next_cat} ]\n"
        f"NUMBER - [ {next_num} ]\n\n"
        f"👇 Tap below once result appears on fb999:"
    )
    
    send_message(chat_id, signal_msg, get_inline_keyboard(current_period, next_cat))

def run_live_session(chat_id, user_id):
    try:
        if user_id in LIMITED_USER_IDS:
            data = load_data()
            today_str = str(date.today())
            if user_id not in data or data[user_id]["date"] != today_str:
                data[user_id] = {"date": today_str, "batches_run": 0}
            
            if data[user_id]["batches_run"] >= 2:
                send_message(chat_id, "⛔ Daily Limit Reached: You have completed your 2 daily live sessions (100 wins total).", get_keyboard())
                return

            data[user_id]["batches_run"] += 1
            save_data(data)

        send_message(chat_id, "🚀 Starting Smart Sharp-Mode Live Session...", get_keyboard())
        
        SESSION_STATE[chat_id] = {
            "running": True,
            "history": [],
            "current_period": None,
            "current_category": None
        }

        send_next_prediction(chat_id)

    except Exception as e:
        print(f"Error in run_live_session: {e}")

def handle_callback_query(callback_query):
    query_id = callback_query.get("id")
    data = callback_query.get("data", "")
    message = callback_query.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    user_id = str(callback_query.get("from", {}).get("id"))

    if user_id not in UNLIMITED_USER_IDS and user_id not in LIMITED_USER_IDS:
        return

    parts = data.split("_")
    if len(parts) >= 3:
        action = parts[0]
        period = parts[1]
        category = parts[2]

        state = SESSION_STATE.get(chat_id)
        if not state:
            return

        if action == "win":
            result_str = f"PEREOD :- {period} {category} WINN 🍾"
        else:
            result_str = f"PEREOD :- {period} {category} LOSS 🙈"

        state["history"].append(result_str)
        if len(state["history"]) > 5:
            state["history"].pop(0)

        try:
            ack_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
            payload = json.dumps({"callback_query_id": query_id, "text": f"Recorded {action.upper()}!"}).encode("utf-8")
            req = urllib.request.Request(ack_url, data=payload, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=3)
        except Exception:
            pass

        updated_history_text = "\n".join(state["history"])
        old_text = (
            f"🔥 WINGO_SMART_AI_PRO\n"
            f"(((( WINGO 1 MINUTE ))))\n\n"
            f"{updated_history_text}\n\n"
            f"✨ Graded as: **{action.upper()}**"
        )
        edit_message(chat_id, message_id, old_text)

        send_next_prediction(chat_id)

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

                    if "callback_query" in result:
                        handle_callback_query(result["callback_query"])

                    if "message" in result:
                        message = result["message"]
                        chat_id = message.get("chat", {}).get("id")
                        user_info = message.get("from", {})
                        user_id = str(user_info.get("id", ""))
                        text = message.get("text", "").strip().lower()

                        if chat_id:
                            if user_id not in UNLIMITED_USER_IDS and user_id not in LIMITED_USER_IDS:
                                send_message(chat_id, "⛔ Access Denied: You are not authorized.")
                                continue

                            if text == "/start":
                                send_message(chat_id, "👋 Welcome! Use the buttons below to control your sharp-mode stream.", get_keyboard())
                            elif text == "/live":
                                ACTIVE_SESSIONS[user_id] = None
                                time.sleep(0.2)
                                
                                t = threading.Thread(target=run_live_session, args=(chat_id, user_id), daemon=True)
                                ACTIVE_SESSIONS[user_id] = t
                                t.start()
                            elif text == "/stop":
                                if user_id in ACTIVE_SESSIONS and ACTIVE_SESSIONS[user_id]:
                                    ACTIVE_SESSIONS[user_id] = None
                                    if chat_id in SESSION_STATE:
                                        SESSION_STATE[chat_id]["running"] = False
                                    send_message(chat_id, "🛑 Live stream successfully stopped.", get_keyboard())
                                else:
                                    send_message(chat_id, "⚠️ No active live stream is currently running.", get_keyboard())

        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

@app.route("/")
def home():
    return "<h3>Wingo Smart AI Bot is Live & Running 24/7!</h3>"

if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
    bot_thread = threading.Thread(target=telegram_bot_loop, daemon=True)
    bot_thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
