import telebot
import os
import subprocess
import threading
import signal
import time
import shutil

API_TOKEN = '7574721300:AAFu27bMIt-4TYo11tCh3MeNWlTFUgIFI3k'
ADMIN_ID = 6353114118  # Replace with your Telegram user ID

bot = telebot.TeleBot(API_TOKEN)

USER_BOTS = {}  # user_id: process
ALLOWED_USERS = {ADMIN_ID}

BASE_DIR = 'user_bots'
os.makedirs(BASE_DIR, exist_ok=True)

# ----------- Helpers -----------
def get_user_dir(user_id):
    user_dir = os.path.join(BASE_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def get_bot_path(user_id):
    return os.path.join(get_user_dir(user_id), 'main.py')

def get_process(user_id):
    return USER_BOTS.get(user_id)

def start_user_bot(user_id, chat_id):
    bot_path = get_bot_path(user_id)
    if not os.path.exists(bot_path):
        bot.send_message(chat_id, "❌ No bot file uploaded.")
        return
    if user_id in USER_BOTS:
        bot.send_message(chat_id, "⚠️ Bot already running.")
        return
    def run_bot():
        proc = subprocess.Popen(['python3', bot_path], cwd=get_user_dir(user_id))
        USER_BOTS[user_id] = proc
        proc.wait()
        if user_id in USER_BOTS:
            del USER_BOTS[user_id]
    thread = threading.Thread(target=run_bot)
    thread.start()
    bot.send_message(chat_id, "✅ Bot started.")

def stop_user_bot(user_id, chat_id):
    proc = get_process(user_id)
    if proc:
        proc.terminate()
        bot.send_message(chat_id, "🛑 Bot stopped.")
    else:
        bot.send_message(chat_id, "❌ No bot running.")

def delete_user_bot(user_id, chat_id):
    stop_user_bot(user_id, chat_id)
    user_dir = get_user_dir(user_id)
    try:
        shutil.rmtree(user_dir)
        bot.send_message(chat_id, "🗑 Bot deleted.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Delete failed: {e}")

# ----------- Bot Commands -----------

@bot.message_handler(commands=['start'])
def welcome(msg):
    bot.send_message(msg.chat.id, "👋 Welcome to the Python Bot Hosting Service!\n\nCommands:\n📤 Upload your `.py` file\n/startbot - Start your bot\n/stopbot - Stop your bot\n/deletebot - Delete bot file\n/status - Bot running status\n/install <package> - Install dependency\n/add - add other users (admin only)\n/remove - remove user (admin only)\n/stopall - stop all bots (admin only)\n/ping - check ping\n/status - check bot status\n/log - send all `.py` to admin")

@bot.message_handler(content_types=['document'])
def handle_file(msg):
    user_id = msg.from_user.id
    if user_id not in ALLOWED_USERS:
        return bot.reply_to(msg, "❌ Unauthorized.")
    if not msg.document.file_name.endswith('.py'):
        return bot.reply_to(msg, "⚠️ Only `.py` files allowed.")
    file_info = bot.get_file(msg.document.file_id)
    file = bot.download_file(file_info.file_path)
    with open(get_bot_path(user_id), 'wb') as f:
        f.write(file)
    bot.reply_to(msg, "📥 File uploaded.")

@bot.message_handler(commands=['startbot'])
def cmd_startbot(msg):
    if msg.from_user.id not in ALLOWED_USERS: return
    start_user_bot(msg.from_user.id, msg.chat.id)

@bot.message_handler(commands=['stopbot'])
def cmd_stopbot(msg):
    if msg.from_user.id not in ALLOWED_USERS: return
    stop_user_bot(msg.from_user.id, msg.chat.id)

@bot.message_handler(commands=['deletebot'])
def cmd_deletebot(msg):
    if msg.from_user.id not in ALLOWED_USERS: return
    delete_user_bot(msg.from_user.id, msg.chat.id)

@bot.message_handler(commands=['status'])
def cmd_status(msg):
    if msg.from_user.id not in ALLOWED_USERS: return
    if msg.from_user.id in USER_BOTS:
        bot.send_message(msg.chat.id, "🟢 Your bot is running.")
    else:
        bot.send_message(msg.chat.id, "🔴 Your bot is stopped.")

@bot.message_handler(commands=['install'])
def cmd_install(msg):
    if msg.from_user.id not in ALLOWED_USERS: return
    parts = msg.text.split(' ', 1)
    if len(parts) != 2:
        return bot.reply_to(msg, "Usage: /install <package>")
    package = parts[1]
    proc = subprocess.Popen(['pip3', 'install', package], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    result = out + err
    bot.reply_to(msg, f"📦 Install result:\n<pre>{result.decode()}</pre>", parse_mode='HTML')

@bot.message_handler(commands=['add'])
def cmd_add(msg):
    if msg.from_user.id != ADMIN_ID:
        return bot.reply_to(msg, "❌ Admin only.")
    parts = msg.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return bot.reply_to(msg, "Usage: /add <user_id>")
    uid = int(parts[1])
    ALLOWED_USERS.add(uid)
    bot.reply_to(msg, f"✅ Added user {uid}")

@bot.message_handler(commands=['remove'])
def cmd_remove(msg):
    if msg.from_user.id != ADMIN_ID:
        return bot.reply_to(msg, "❌ Admin only.")
    parts = msg.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return bot.reply_to(msg, "Usage: /remove <user_id>")
    uid = int(parts[1])
    if uid in ALLOWED_USERS:
        ALLOWED_USERS.remove(uid)
        bot.reply_to(msg, f"✅ Removed user {uid}")
    else:
        bot.reply_to(msg, "⚠️ User not found.")

@bot.message_handler(commands=['stopall'])
def cmd_stopall(msg):
    if msg.from_user.id != ADMIN_ID:
        return bot.reply_to(msg, "❌ Admin only.")
    for uid, proc in list(USER_BOTS.items()):
        try:
            proc.terminate()
            del USER_BOTS[uid]
        except Exception:
            pass
    bot.reply_to(msg, "🛑 All bots stopped.")

BOT_START_TIME = time.time()

@bot.message_handler(commands=['ping'])
def cmd_ping(msg):
    start = time.time()

    # Measure latency
    sent_msg = bot.reply_to(msg, "⏱ Measuring ping...")
    ping_ms = int((time.time() - start) * 1000)

    # Uptime
    uptime_sec = time.time() - BOT_START_TIME
    uptime_str = str(timedelta(seconds=int(uptime_sec)))

    # CPU & RAM
    cpu_usage = psutil.cpu_percent(interval=0.5)
    ram_usage = psutil.virtual_memory().percent

    # System Info
    system = platform.system()
    arch = platform.machine()

    # Total users
    total_users = len(ALLOWED_USERS)

    # Response message
    result = (
        "✦ <b>Isagi bot host service</b> ✦ is running...\n\n"
        f"✧ <b>Ping:</b> {ping_ms} ms\n"
        f"✧ <b>Up Time:</b>  {uptime_str}\n"
        f"✧ <b>CPU Usage:</b> {cpu_usage}%\n"
        f"✧ <b>RAM Usage:</b> {ram_usage}%\n"
        f"✧ <b>System:</b> {system} ({arch})\n"
        f"✧ <b>Total Users:</b> {total_users}\n\n"
        f"✧ <i>Bot By:</i> <a href='https://t.me/SLAYER_OP7'>@SLAYER_OP7</a>"
    )

    bot.edit_message_text(result, chat_id=msg.chat.id, message_id=sent_msg.message_id, parse_mode="HTML", disable_web_page_preview=True)

@bot.message_handler(commands=['log'])
def cmd_log(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    for user in os.listdir(BASE_DIR):
        user_dir = os.path.join(BASE_DIR, user)
        for file in os.listdir(user_dir):
            if file.endswith('.py'):
                with open(os.path.join(user_dir, file), 'rb') as f:
                    bot.send_document(msg.chat.id, f, caption=f"📄 From {user}")

# ----------- Run Bot -----------
print("🤖 Bot is running...")
bot.infinity_polling()
