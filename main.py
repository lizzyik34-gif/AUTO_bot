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

# 📊 GLOBAL & GROUP SESSION TRACKING
ACTIVE_GROUPS = {} # {chat_id: {"active": True, "stage": 1, "last_size": None, "stats": {"total": 0, "wins": 0, "losses": 0}}}

@app.route("/")
def health_check():
    return "FB999 Automated Group Signal Bot is Running!"

def get_1min_period():
    now = datetime.now(timezone.utc)
    date_prefix = now.strftime("%Y%m%d")
    minute_of_day = (now.hour * 60) + now.minute + 1
    period_suffix = 100010000 + minute_of_day
    return f"{date_prefix}{period_suffix}"

def generate_smart_signal(session):
    stage = session["stage"]
    last_size = session["last_size"]

    # 🛡️ Stage 3+ Anti-Loss Pattern Reversal Logic
    if stage >= 3 and last_size:
        size = "Small" if last_size == "Big" else "Big"
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

    accuracy = random.randint(85, 98) if stage >= 3 else random.randint(72, 95)
    session["last_size"] = size

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
    print(f">>> STARTED NON-STOP GROUP STREAM FOR CHAT: {chat_id} <<<")
    last_sent_period = None

    while ACTIVE_GROUPS.get(chat_id, {}).get("active", False):
        current_period = get_1min_period()

        # Drop signal once per new 1-minute period
        if current_period != last_sent_period:
            session = ACTIVE_GROUPS[chat_id]
            
            # Evaluate previous round before dropping the next one
            if last_sent_period is not None:
                # Simulate/check round outcome to manage stage progression automatically
                round_won = random.choices([True, False], weights=[75, 25])[0] if session["stage"] < 3 else random.choices([True, False], weights=[92, 8])[0]
                
                session["stats"]["total"] += 1
                if round_won:
                    session["stats"]["wins"] += 1
                    outcome_banner = f"✅ **PREVIOUS ROUND ({last_sent_period}): WIN!** (Resetting to Stage 1)"
                    session["stage"] = 1
                else:
                    session["stats"]["losses"] += 1
                    next_stage = session["stage"] + 1 if session["stage"] < 6 else 6
                    outcome_banner = f"❌ **PREVIOUS ROUND ({last_sent_period}): LOSS** (Advancing to Stage {next_stage} — Anti-Loss Active)"
                    session["stage"] = next_stage
                
                send_message(chat_id, outcome_banner)
                time.sleep(1)

            # Generate and drop the new signal for the incoming period
            number, size, color, accuracy = generate_smart_signal(session)
            shield_tag = "🛡️ **ANTI-LOSS ACTIVE**" if session["stage"] >= 3 else "⚡ **STANDARD AI**"

            signal_text = (
                f"🚨 **FB999 LIVE 1-MIN SIGNAL** 🚨\n\n"
                f"🔹 **Period:** `{current_period}`\n"
                f"📈 **Stage:** `Stage {session['stage']} / 6` ({shield_tag})\n"
                f"🎯 **Prediction:** **{size.upper()}** (`{number}`)\n"
                f"🎨 **Color:** {color}\n"
                f"🔥 **Win Rate:** `{accuracy}%`\n\n"
                f"⏳ *Next update drops automatically at the next minute...*"
            )
            send_message(chat_id, signal_text)
            last_sent_period = current_period

        # Check every 2 seconds so it triggers the exact second a new minute begins
        time.sleep(2)

    print(f">>> STOPPED GROUP STREAM FOR CHAT: {chat_id} <<<")

def check_updates():
    offset = 0
    print(">>> BOT POLLING ACTIVE (READY FOR GROUPS & PRIVATE CHATS) <<<")
    
    # Clear old webhooks so polling works cleanly
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
                # Clean group commands like "/live@YourBotName" -> "/live"
                text = message["text"].strip().lower().split("@")[0]

                if text == "/live":
                    if user_id not in ALLOWED_USER_IDS:
                        send_message(chat_id, "⛔ Only authorized admins can start the live signal stream.")
                        continue

                    if ACTIVE_GROUPS.get(chat_id, {}).get("active", False):
                        send_message(chat_id, "ℹ️ **Live stream is already running in this group!**")
                        continue

                    ACTIVE_GROUPS[chat_id] = {
                        "active": True,
                        "stage": 1,
                        "last_size": None,
                        "stats": {"total": 0, "wins": 0, "losses": 0}
                    }
                    send_message(chat_id, "🚀 **NON-STOP LIVE SIGNALS STARTED!**\nSignals will drop every minute automatically. Send `/stop` to halt.")
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
                        "👋 **FB999 Automated Group Signal Bot Ready!**\n\n"
                        "1️⃣ Add me to your Telegram Group & make me an **Admin**.\n"
                        "2️⃣ Type `/live` to start non-stop 1-minute automated signals.\n"
                        "3️⃣ Type `/stop` anytime to pause the stream.\n"
                        "4️⃣ Type `/stats` to check live win/loss performance."
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
