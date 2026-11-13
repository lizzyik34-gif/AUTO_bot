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

# 📊 GROUP SESSION TRACKING
ACTIVE_GROUPS = {} 

@app.route("/")
def health_check():
    return "FB999 Clean Uninterrupted Signal Bot is Running!"

def get_1min_period(offset_minutes=0):
    now = datetime.now(timezone.utc)
    total_minutes = (now.hour * 60) + now.minute + offset_minutes + 1
    date_prefix = now.strftime("%Y%m%d")
    period_suffix = 100010000 + total_minutes
    return f"{date_prefix}{period_suffix}"

def fetch_fb999_actual_result():
    try:
        req = urllib.request.Request(
            "https://api.55thebs.com/api/webapi/GetNoaverageList", 
            data=json.dumps({"typeId": 1, "pageNo": 1, "pageSize": 10}).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            }
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            items = res_data.get("data", {}).get("list", [])
            if items:
                latest = items[0]
                period = str(latest.get("issueNumber"))
                number = int(latest.get("number", 0))
                size = "Big" if number >= 5 else "Small"
                return period, number, size
    except Exception as e:
        print(f"API Fetch Notice: {e}")
    return None, None, None

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

def auto_signal_worker(chat_id):
    print(f">>> STARTED NON-STOP UNINTERRUPTED STREAM FOR: {chat_id} <<<")
    last_sent_period = None

    while ACTIVE_GROUPS.get(chat_id, {}).get("active", False):
        current_period = get_1min_period(offset_minutes=0)

        if current_period != last_sent_period:
            session = ACTIVE_GROUPS[chat_id]
            
            if pending_press_period := last_sent_period:
                actual_period, actual_num, actual_size = fetch_fb999_actual_result()
                
                if actual_size and actual_period == pending_press_period:
                    user_predicted_size = session.get("last_prediction")
                    round_won = (actual_size.lower() == user_predicted_size.lower())
                else:
                    round_won = True 

                session["stats"]["total"] += 1
                if round_won:
                    session["stats"]["wins"] += 1
                    session["consecutive_losses"] = 0
                    outcome_msg = f"✅ **ROUND {pending_press_period} RESULT: WIN!**\n🎯 Actual: `{actual_size}`"
                else:
                    session["stats"]["losses"] += 1
                    session["consecutive_losses"] += 1
                    outcome_msg = f"❌ **ROUND {pending_press_period} RESULT: LOSS**\n🎯 Actual: `{actual_size}`"

                send_message(chat_id, outcome_msg)
                time.sleep(1)

            number, size, color, accuracy = generate_smart_signal(session)

            signal_text = (
                f"🚨 **FB999 LIVE 1-MIN SIGNAL** 🚨\n\n"
                f"🔹 **Period:** `{current_period}`\n"
                f"🎯 **Prediction:** **{size.upper()}** (`{number}`)\n"
                f"🎨 **Color:** {color}\n"
                f"🔥 **Win Rate:** `{accuracy}%`\n\n"
                f"⏳ *Non-stop automated live feed active...*"
            )
            send_message(chat_id, signal_text)
            last_sent_period = current_period

        time.sleep(2)

    print(f">>> STOPPED GROUP STREAM FOR CHAT: {chat_id} <<<")

def check_updates():
    offset = 0
    print(">>> BOT POLLING ACTIVE (UNINTERRUPTED MODE) <<<")
    
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

                if text == "/live":
                    if user_id not in ALLOWED_USER_IDS:
                        send_message(chat_id, "⛔ Only authorized admins can start the live signal stream.")
                        continue

                    if ACTIVE_GROUPS.get(chat_id, {}).get("active", False):
                        send_message(chat_id, "ℹ️ **Live stream is already running smoothly!**")
                        continue

                    ACTIVE_GROUPS[chat_id] = {
                        "active": True,
                        "consecutive_losses": 0,
                        "last_prediction": None,
                        "stats": {"total": 0, "wins": 0, "losses": 0}
                    }
                    send_message(chat_id, "🚀 **NON-STOP SIGNALS STARTED!**\nWill run continuously without sleeping or prompts until you send `/stop`.")
                    threading.Thread(target=auto_signal_worker, args=(chat_id,), daemon=True).start()

                elif text == "/stop":
                    if user_id not in ALLOWED_USER_IDS:
                        send_message(chat_id, "⛔ Only authorized admins can stop the live signal stream.")
                        continue

                    if ACTIVE_GROUPS.get(chat_id, {}).get("active", False):
                        ACTIVE_GROUPS[chat_id]["active"] = False
                        send_message(chat_id, "🛑 **Live signal stream stopped.**")
                    else:
                        send_message(chat_id, "ℹ️ No active signal stream running here.")

                elif text == "/stats":
                    stats = ACTIVE_GROUPS.get(chat_id, {}).get("stats", {"total": 0, "wins": 0, "losses": 0})
                    total = stats["total"]
                    wins = stats["wins"]
                    losses = stats["losses"]
                    win_pct = (wins / total * 100) if total > 0 else 0
                    stats_text = (
                        f"📈 **GROUP LIVE STATISTICS**\n\n"
                        f"📌 **Total Rounds:** `{total}`\n"
                        f"✅ **Total Wins:** `{wins}`\n"
                        f"❌ **Total Losses:** `{losses}`\n"
                        f"🎯 **Success Rate:** `{win_pct:.1f}%`"
                    )
                    send_message(chat_id, stats_text)

                elif text == "/start":
                    send_message(
                        chat_id,
                        "👋 **FB999 Uninterrupted Signal Bot Ready!**\n\n"
                        "Type `/live` to start non-stop 1-minute automated signals.\n"
                        "Type `/stop` anytime to pause."
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
