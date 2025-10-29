import telebot
from telebot import types
import json
import os
import uuid

BOT_TOKEN = '7817896484:AAHRW16WmzrEbR2nBwMy4vGyrRDgZNRKxQ4'
bot = telebot.TeleBot(BOT_TOKEN)

# مسیر دیتابیس برای ذخیره فولدرها و فایل‌ها
DATA_FILE = "folders.json"

# اگر فایل دیتابیس وجود نداشت، ایجادش کن
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

# 📦 لود فولدرها از فایل
def load_folders():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

# 💾 ذخیره فولدرها در فایل
def save_folders(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# 🧰 دیکشنری موقت برای حالت ساخت فولدر
user_states = {}

@bot.message_handler(commands=['start'])
def start(message):
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("folder_"):
        folder_id = args[1].replace("folder_", "")
        send_folder_files(message.chat.id, folder_id)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ ساخت فولدر جدید", "📂 دیدن فولدرها")
    bot.send_message(message.chat.id, "به ربات مدیریت فایل خوش آمدی 👋", reply_markup=markup)

# ➕ ساخت فولدر جدید
@bot.message_handler(func=lambda m: m.text == "➕ ساخت فولدر جدید")
def create_folder(message):
    bot.send_message(message.chat.id, "اسم فولدر رو بفرست:")
    user_states[message.chat.id] = {"state": "creating_folder"}

@bot.message_handler(func=lambda m: user_states.get(m.chat.id, {}).get("state") == "creating_folder")
def save_folder_name(message):
    folders = load_folders()
    folder_id = str(uuid.uuid4())[:8]
    folders[folder_id] = {
        "owner": message.chat.id,
        "name": message.text,
        "files": []
    }
    save_folders(folders)
    user_states[message.chat.id] = {"state": None, "folder_id": folder_id}
    bot.send_message(message.chat.id, f"فولدر '{message.text}' ساخته شد ✅\nحالا فایل‌هاتو بفرست تا داخل فولدر ذخیره بشن.\nوقتی تموم شد بزن /done")

@bot.message_handler(content_types=['document', 'photo', 'video', 'audio'])
def save_files(message):
    state = user_states.get(message.chat.id)
    if not state or not state.get("folder_id"):
        return

    folder_id = state["folder_id"]
    folders = load_folders()
    folder = folders.get(folder_id)
    if folder:
        file_info = {
            "type": message.content_type,
            "file_id": getattr(message, message.content_type)[-1].file_id if message.content_type == "photo" else getattr(message, message.content_type).file_id
        }
        folder["files"].append(file_info)
        save_folders(folders)
        bot.send_message(message.chat.id, "📁 فایل ذخیره شد.")

@bot.message_handler(commands=['done'])
def finish_folder(message):
    bot.send_message(message.chat.id, "✅ فولدر ذخیره شد. می‌تونی از منو «📂 دیدن فولدرها» رو انتخاب کنی.")

# 📂 دیدن فولدرها
@bot.message_handler(func=lambda m: m.text == "📂 دیدن فولدرها")
def view_folders(message):
    folders = load_folders()
    user_folders = {fid: f for fid, f in folders.items() if f["owner"] == message.chat.id}

    if not user_folders:
        bot.send_message(message.chat.id, "📭 هیچ فولدری نداری.")
        return

    markup = types.InlineKeyboardMarkup()
    for fid, folder in user_folders.items():
        markup.add(types.InlineKeyboardButton(folder["name"], callback_data=f"view_{fid}"))
    bot.send_message(message.chat.id, "📂 فولدرهای شما:", reply_markup=markup)

# 📊 نمایش اطلاعات فولدر
@bot.callback_query_handler(func=lambda call: call.data.startswith("view_"))
def show_folder_info(call):
    folder_id = call.data.replace("view_", "")
    folders = load_folders()
    folder = folders.get(folder_id)
    if not folder:
        bot.answer_callback_query(call.id, "فولدر پیدا نشد ❌")
        return

    total = len(folder["files"])
    vids = sum(1 for f in folder["files"] if f["type"] == "video")
    imgs = sum(1 for f in folder["files"] if f["type"] == "photo")
    docs = sum(1 for f in folder["files"] if f["type"] == "document")
    auds = sum(1 for f in folder["files"] if f["type"] == "audio")

    stats = f"""
📁 {folder['name']}
📊 فایل‌ها: {total}
🎞 ویدیو: {vids}/{total}
🖼 عکس: {imgs}/{total}
📄 سند: {docs}/{total}
🎧 صدا: {auds}/{total}
🔗 لینک اشتراک: t.me/{bot.get_me().username}?start=folder_{folder_id}
"""
    bot.send_message(call.message.chat.id, stats)

# 📨 فوروارد فایل‌های فولدر
def send_folder_files(chat_id, folder_id):
    folders = load_folders()
    folder = folders.get(folder_id)
    if not folder or not folder["files"]:
        bot.send_message(chat_id, "❌ این فولدر وجود ندارد یا خالی است.")
        return

    bot.send_message(chat_id, f"📦 در حال ارسال فولدر: {folder['name']}")
    for f in folder["files"]:
        try:
            if f["type"] == "photo":
                bot.send_photo(chat_id, f["file_id"])
            elif f["type"] == "video":
                bot.send_video(chat_id, f["file_id"])
            elif f["type"] == "document":
                bot.send_document(chat_id, f["file_id"])
            elif f["type"] == "audio":
                bot.send_audio(chat_id, f["file_id"])
        except Exception as e:
            print(f"خطا در ارسال فایل: {e}")

    bot.send_message(chat_id, "✅ همه فایل‌ها ارسال شدند.")

bot.infinity_polling()