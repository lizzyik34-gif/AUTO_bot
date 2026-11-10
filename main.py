import time
import json
import random
import urllib.request
import threading
import os
from datetime import datetime, timezone
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
SESSION_HISTORY = {}  # Stores history log per user chat_id

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
        response = urllib.request.urlopen(req, timeout=10)
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
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Error editing message in Telegram: {e}")

def get_keyboard():
    """Persistent keyboard menu at the bottom."""
    return {
        "keyboard": [
            [{"text": "/live"}, {"text": "/stop"}]
        ],
        "resize_keyboard": True,
        "is_persistent": True
    }

def get_inline_keyboard(period):
    """Inline buttons attached right under the message for manual WIN/LOSS grading."""
    return {
        "inline_keyboard": [
            [
                {"text": "✅ WIN", "callback_data": f"win_{period}"},
                {"text": "❌ LOSS", "callback_data": f"loss_{period}"}
            ]
        ]
    }

def run_live_session(chat_id, user_id):
    try:
        send_message(chat_id, "🚀 Starting Interactive Wingo Live Session...\nTap WIN or LOSS on each signal card based on fb999 results!", get_keyboard())
        
        history_log = []
        SESSION_HISTORY[chat_id] = history_log

        while ACTIVE_SESSIONS.get(user_id) == threading.current_thread():
            current_period = get_current_wingo_period()
            next_period = current_period + 1

            next_cat = random.choice(["SMAL", "BIGG"])
            next_num = random.randint(0, 4) if next_cat == "SMAL" else random.randint(5, 9)

            history_text = "\n".join(history_log) if history_log else "Waiting for first result..."

            signal_msg = (
                f"WINGO_AUTO_PREDICT_AI\n"
                f"(((( WINGO 1 MINUTE ))))\n\n"
                f"{history_text}\n\n"
                f"📥 ACTIVE PREDICTION 📥\n"
                f"Period: {current_period} : [ {next_cat} ]\n"
                f"NUMBER - [ {next_num} ]\n\n"
                f"👇 Tap below once result appears on fb999:"
            )
            
            msg_id = send_message(chat_id, signal_msg, get_inline_keyboard(current_period))
            
            # Store active message mapping if needed for callbacks
            # Wait for the 1-minute period cycle
            time.sleep(60)
            
    except Exception as e:
        print(f"Error in run_live_session: {e}")

def handle_callback_query(callback_query):
    query_id = callback_query.get("id")
    data = callback_query.get("data", "")
    message = callback_query.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    user_id = str(callback_query.get("from", {}).get("id"))

    if user_id not in UNLIMITED_USER_IDS:
        return

    if "_" in data:
        action, period = data.split("_", 1)
        history_log = SESSION_HISTORY.get(chat_id, [])

        # Format result line based on user selection
        if action == "win":
            result_str = f"PEREOD :- {period} WINN 🍾"
        else:
            result_str = f"PEREOD :- {period} LOSS 🙈"

        history_log.append(result_str)
        if len(history_log) > 5:
            history_log.pop(0)

        # Acknowledge callback to remove loading animation on button
        try:
            ack_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
            payload = json.dumps({"callback_query_id": query_id, "text": f"Recorded as {action.upper()}!"}).encode("utf-8")
            req = urllib.request.Request(ack_url, data=payload, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass

        # Update message to remove buttons and show updated history
        updated_history_text = "\n".join(history_log)
        new_text = (
            f"WINGO_AUTO_PREDICT_AI\n"
            f"(((( WINGO 1 MINUTE ))))\n\n"
            f"{updated_history_text}\n\n"
            f"✨ Graded as: **{action.upper()}**"
        )
        edit_message(chat_id, message_id, new_text)

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
                            if user_id not in UNLIMITED_USER_IDS:
                                send_message(chat_id, "⛔ Access Denied: You are not authorized.")
                                continue

                            if text == "/start":
                                send_message(chat_id, "👋 Welcome! Use the buttons below to control your interactive stream.", get_keyboard())
                            elif text == "/live":
                                ACTIVE_SESSIONS[user_id] = None
                                time.sleep(0.5)
                                
                                t = threading.Thread(target=run_live_session, args=(chat_id, user_id), daemon=True)
                                ACTIVE_SESSIONS[user_id] = t
                                t.start()
                            elif text == "/stop":
                                if user_id in ACTIVE_SESSIONS and ACTIVE_SESSIONS[user_id]:
                                    ACTIVE_SESSIONS[user_id] = None
                                    send_message(chat_id, "🛑 Live stream successfully stopped.", get_keyboard())
                                else:
                                    send_message(chat_id, "⚠️ No active live stream is currently running.", get_keyboard())

        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

@app.route("/")
def home():
    return "<h3>Wingo Interactive Bot is Live & Running 24/7!</h3>"

if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
    bot_thread = threading.Thread(target=telegram_bot_loop, daemon=True)
    bot_thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
