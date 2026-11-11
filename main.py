import time
import json
import random
import urllib.request
import threading
import os
from datetime import datetime, timezone
from flask import Flask

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "render-secure-key-2026")

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "9036832422:AAHMZibYneXOFOwkETsFm6wRXujXClQH8Zk"
FREE_ACCESS_USER_IDS = ["9063263288", "7891601316", "8842031370"]

ACTIVE_LIVE_SESSIONS = {}
USER_STAGE_TRACKER = {}
USER_SEMAPHORE = {}

@app.route("/")
def index():
    return "FB999 Telegram Bot Long-Polling Service is Active & Running!"

def telegram_bot_polling():
    offset = 0
    print(">>> TELEGRAM LONG-POLLING WORKER INITIALIZED <<<")
    
    # Clear any old webhook automatically so polling works cleanly
    try:
        clear_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook?drop_pending_updates=true"
        urllib.request.urlopen(clear_url)
        print(">>> OLD WEBHOOK CLEARED FOR POLLING MODE <<<")
    except Exception as e:
        print(f"Webhook clear notice: {e}")

    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={offset}&timeout=30"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=35) as response:
                data = json.loads(response.read().decode())
                if data.get("ok"):
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        
                        # Handle button clicks (Callback Queries)
                        if "callback_query" in update:
                            cq = update["callback_query"]
                            cq_id = cq["id"]
                            chat_id = str(cq["message"]["chat"]["id"])
                            data_val = cq["data"]
                            
                            answer_callback_query(cq_id)
                            if data_val in ["win", "loss"]:
                                handle_button_response(chat_id, data_val)
                            continue

                        # Handle text messages
                        message = update.get("message")
                        if message and "text" in message:
                            chat_id = str(message["chat"]["id"])
                            user_id = str(message["from"]["id"])
                            text = message["text"].strip().lower()
                            print(f"--> MESSAGE RECEIVED: '{text}' from USER ID: {user_id}")

                            if "stop" in text:
                                stop_live_stream(chat_id)
                            else:
                                start_live_stream(chat_id)
        except Exception as e:
            print(f"Polling loop exception: {e}")
            time.sleep(3)

def send_telegram_message(chat_id, text, reply_markup=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        if reply_markup:
            payload["reply_markup"] = reply_markup
            
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as resp:
            res_data = json.loads(resp.read().decode())
            if res_data.get("ok"):
                return res_data["result"].get("message_id")
    except Exception as e:
        print(f"Error sending message to {chat_id}: {e}")
    return None

def answer_callback_query(callback_query_id, text="Recorded!"):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
        payload = json.dumps({"callback_query_id": callback_query_id, "text": text}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"Error answering callback: {e}")

def get_live_fb999_period():
    now = datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d")
    total_minutes = (now.hour * 60) + now.minute
    return f"{date_part}000{10000 + total_minutes}"

def generate_signal_text(stage=1):
    period_str = get_live_fb999_period()
    size = random.choice(["BIG (5-9)", "SMALL (0-4)"])
    target_num = f"{random.randint(7, 9)} / 9"
    win_rate = random.randint(84, 97)
    
    return (
        f"🔥 *WINGO_SMART_AI_PRO*\n"
        f"(((( WINGO 1 MINUTE ))))\n\n"
        f"⏳ Period: `{period_str}`\n"
        f"📈 Stage Level: Stage {stage} / 6\n"
        f"🎯 Prediction Range: 🔴 {size}\n"
        f"🔢 Target Numbers: {target_num}\n"
        f"⚡ Win Rate: {win_rate}%\n\n"
        f"👇 *Tap below once result appears on fb999:*"
    )

def get_inline_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "✅ WIN", "callback_data": "win"},
                {"text": "❌ LOSS", "callback_data": "loss"}
            ]
        ]
    }

def handle_button_response(chat_id, result):
    if chat_id not in USER_STAGE_TRACKER:
        USER_STAGE_TRACKER[chat_id] = 1

    if result == "win":
        USER_STAGE_TRACKER[chat_id] = 1 
        send_telegram_message(chat_id, "🎉 *Result Recorded: WIN!* Resetting to Stage 1.")
    else:
        if USER_STAGE_TRACKER[chat_id] < 6:
            USER_STAGE_TRACKER[chat_id] += 1
            send_telegram_message(chat_id, f"⚠️ *Result Recorded: LOSS.* Moving to Stage {USER_STAGE_TRACKER[chat_id]} / 6.")
        else:
            send_telegram_message(chat_id, "🛡️ *Max Stage 6 Reached.* Capped securely at Stage 6.")

    if chat_id in USER_SEMAPHORE:
        USER_SEMAPHORE[chat_id].set()

def start_live_stream(chat_id):
    if ACTIVE_LIVE_SESSIONS.get(chat_id, False):
        if chat_id in USER_SEMAPHORE:
            USER_SEMAPHORE[chat_id].set()
        return

    ACTIVE_LIVE_SESSIONS[chat_id] = True
    USER_STAGE_TRACKER[chat_id] = 1
    USER_SEMAPHORE[chat_id] = threading.Event()
    
    send_telegram_message(chat_id, "🚀 *Live Stream Started!* Waiting for your Win/Loss clicks.")

    def run_stream():
        while ACTIVE_LIVE_SESSIONS.get(chat_id, False):
            stage = USER_STAGE_TRACKER.get(chat_id, 1)
            signal_msg = generate_signal_text(stage)
            send_telegram_message(chat_id, signal_msg, reply_markup=get_inline_keyboard())

            USER_SEMAPHORE[chat_id].clear()
            USER_SEMAPHORE[chat_id].wait(timeout=None)

            if not ACTIVE_LIVE_SESSIONS.get(chat_id, False):
                break

        ACTIVE_LIVE_SESSIONS[chat_id] = False
        send_telegram_message(chat_id, "🛑 *Live Stream Stopped.*")

    threading.Thread(target=run_stream, daemon=True).start()

def stop_live_stream(chat_id):
    if ACTIVE_LIVE_SESSIONS.get(chat_id, False):
        ACTIVE_LIVE_SESSIONS[chat_id] = False
        if chat_id in USER_SEMAPHORE:
            USER_SEMAPHORE[chat_id].set()
        send_telegram_message(chat_id, "🛑 *Live Stream Stopped Successfully.*")
    else:
        send_telegram_message(chat_id, "ℹ️ No active live stream found.")

if __name__ == "__main__":
    # Start the telegram polling thread
    bot_thread = threading.Thread(target=telegram_bot_polling, daemon=True)
    bot_thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
