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
TELEGRAM_BOT_TOKEN = "9237583887:AAGfUABC5pb4X8sI40If2BMm0surTrCtnRA"
FREE_ACCESS_USER_IDS = ["9063263288", "7891601316", "8842031370"]

USER_SESSIONS = {} 

@app.route("/")
def index():
    return "FB999 10-Table Live Session Bot is Active & Running!"

def telegram_bot_polling():
    offset = 0
    print(">>> TELEGRAM LONG-POLLING WORKER INITIALIZED <<<")
    
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
                        
                        if "callback_query" in update:
                            cq = update["callback_query"]
                            cq_id = cq["id"]
                            chat_id = str(cq["message"]["chat"]["id"])
                            data_val = cq["data"]
                            
                            handle_button_response(chat_id, cq_id, data_val)
                            continue

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

def send_or_edit_telegram_message(chat_id, text, reply_markup=None):
    try:
        session = USER_SESSIONS.get(chat_id)
        msg_id = session.get("msg_id") if session else None

        if msg_id:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
            payload = {
                "chat_id": chat_id,
                "message_id": msg_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup
            
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            try:
                with urllib.request.urlopen(req) as resp:
                    res_data = json.loads(resp.read().decode())
                    if res_data.get("ok"):
                        return msg_id
            except Exception:
                pass 

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        if reply_markup:
            payload["reply_markup"] = reply_markup
            
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as resp:
            res_data = json.loads(resp.read().decode())
            if res_data.get("ok"):
                new_id = res_data["result"].get("message_id")
                if chat_id in USER_SESSIONS:
                    USER_SESSIONS[chat_id]["msg_id"] = new_id
                return new_id
    except Exception as e:
        print(f"Error sending/editing message to {chat_id}: {e}")
    return None

def answer_callback_query(callback_query_id, text="Updated!"):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
        payload = json.dumps({"callback_query_id": callback_query_id, "text": text, "show_alert": True}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"Error answering callback: {e}")

def get_current_fb999_period():
    now = datetime.now(timezone.utc)
    total_minutes = (now.hour * 60) + now.minute
    date_part = now.strftime("%Y%m%d")
    return f"{date_part}000{10000 + total_minutes}"

def build_dashboard_text(chat_id):
    session = USER_SESSIONS.get(chat_id, {})
    history = session.get("history", [])
    stage = session.get("stage", 1)

    text = "🔥 *WINGO_SMART_AI_PRO* — *LIVE 10-TABLE FEED*\n"
    text += f"📈 *Stage Level*: Stage {stage} / 6\n\n"
    text += "📋 *Recent Rounds History (Latest on Top):*\n"
    text += "`----------------------------------------------`\n"
    text += "` Period         | Prediction | Result `\n"
    text += "`----------------------------------------------`\n"

    if not history:
        text += "` Waiting for first round...                  `\n"
    else:
        # Display latest period at the top
        sorted_history = list(reversed(history))
        for item in sorted_history:
            per = item["period"]
            pred = item["size"]
            stat = item["status"] 
            text += f"` {per} | {pred:<10} | {stat} `\n"

    text += "`----------------------------------------------`\n"
    text += "👇 *Locked until current period concludes on fb999:*"
    return text

def get_inline_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "✅ WIN", "callback_data": "win"},
                {"text": "❌ LOSS", "callback_data": "loss"}
            ]
        ]
    }

def handle_button_response(chat_id, cq_id, result):
    if chat_id not in USER_SESSIONS or not USER_SESSIONS[chat_id]["active"]:
        answer_callback_query(cq_id, "ℹ️ Session inactive. Send /live to start.")
        return

    session = USER_SESSIONS[chat_id]
    history = session["history"]
    
    if not history:
        return

    active_period = history[0]["period"]
    current_live_period = get_current_fb999_period()

    # STRICT CHECK: Do not allow clicking until the live period on fb999 has advanced past the active prediction period
    if int(current_live_period) <= int(active_period):
        answer_callback_query(cq_id, f"⏳ Period {active_period} still active on fb999! Wait for results.")
        return

    # Period has passed, process win/loss on active item
    if result == "win":
        history[0]["status"] = "✅"
        session["stage"] = 1
        answer_callback_query(cq_id, "✅ Result Recorded: WIN!")
    else:
        history[0]["status"] = "❌"
        if session["stage"] < 6:
            session["stage"] += 1
        else:
            session["stage"] = 6 
        answer_callback_query(cq_id, "❌ Result Recorded: LOSS.")

    # Generate next live period automatically
    next_period = current_live_period
    next_size = random.choice(["BIG (5-9)", "SMALL (0-4)"])

    # Insert new active round at the beginning (top)
    history.insert(0, {
        "period": next_period,
        "size": next_size,
        "status": "⏳"
    })

    # Keep max 10 tables
    if len(history) > 10:
        history.pop()

    dash_text = build_dashboard_text(chat_id)
    send_or_edit_telegram_message(chat_id, dash_text, reply_markup=get_inline_keyboard())

def start_live_stream(chat_id):
    if chat_id in USER_SESSIONS and USER_SESSIONS[chat_id]["active"]:
        dash_text = build_dashboard_text(chat_id)
        send_or_edit_telegram_message(chat_id, dash_text, reply_markup=get_inline_keyboard())
        return

    initial_period = get_current_fb999_period()
    initial_size = random.choice(["BIG (5-9)", "SMALL (0-4)"])

    USER_SESSIONS[chat_id] = {
        "active": True,
        "stage": 1,
        "msg_id": None,
        "history": [
            {
                "period": initial_period,
                "size": initial_size,
                "status": "⏳"
            }
        ]
    }

    dash_text = build_dashboard_text(chat_id)
    send_or_edit_telegram_message(chat_id, dash_text, reply_markup=get_inline_keyboard())

def stop_live_stream(chat_id):
    if chat_id in USER_SESSIONS:
        USER_SESSIONS[chat_id]["active"] = False
        USER_SESSIONS.pop(chat_id, None)
        send_or_edit_telegram_message(chat_id, "🛑 *Live Stream Session Stopped Successfully.*")
    else:
        send_or_edit_telegram_message(chat_id, "ℹ️ No active live stream found.")

# --- MODULE-LEVEL STARTUP GUARD (FOR GUNICORN/RENDER) ---
_polling_started = False
if not _polling_started:
    _polling_started = True
    bot_thread = threading.Thread(target=telegram_bot_polling, daemon=True)
    bot_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
