
import telebot
import requests
import json
import os
import random
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
SMS_API_KEY = os.environ.get("SMS_API_KEY")
SMS_LINE = ''

USERS_DB = 'users.json'
PENDING_DB = 'pending.json'
CARD_DB = 'card_db.json'
BALANCE_DB = 'balances.json'

ADMIN_ID = 123456789  # 🛑 جایگزین کن با آیدی عددی تلگرامت

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

def load_json(file, default):
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump(default, f)
    with open(file, 'r') as f:
        return json.load(f)

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=2)

def is_user_registered(user_id):
    return user_id in load_json(USERS_DB, [])

def is_user_pending(user_id):
    return user_id in load_json(PENDING_DB, [])

def request_registration(user_id):
    pending = load_json(PENDING_DB, [])
    if user_id not in pending:
        pending.append(user_id)
        save_json(PENDING_DB, pending)

def approve_user(user_id):
    users = load_json(USERS_DB, [])
    pending = load_json(PENDING_DB, [])
    if user_id not in users:
        users.append(user_id)
        save_json(USERS_DB, users)
    if user_id in pending:
        pending.remove(user_id)
        save_json(PENDING_DB, pending)

def send_sms(to, text):
    url = f"https://api.kavenegar.com/v1/{SMS_API_KEY}/sms/send.json"
    payload = {
        'receptor': to,
        'sender': SMS_LINE,
        'message': text
    }
    try:
        r = requests.post(url, data=payload)
        print("SMS Response:", r.json())
    except Exception as e:
        print("SMS Error:", e)

def get_balance(card):
    balances = load_json(BALANCE_DB, {})
    return balances.get(card, random.randint(10_000_000, 50_000_000))

def update_balance(card, amount):
    balances = load_json(BALANCE_DB, {})
    current = balances.get(card, random.randint(10_000_000, 50_000_000))
    new_balance = max(0, current - amount)
    balances[card] = new_balance
    save_json(BALANCE_DB, balances)
    return new_balance

def fake_sms(amount, card, balance=None, bank=None):
    banks = ['ملی', 'ملت', 'صادرات', 'پاسارگاد', 'تجارت', 'رفاه', 'کشاورزی', 'مهر ایران', 'مسکن', 'بلو']
    if bank is None:
        bank = random.choice(banks)
    if balance is None:
        balance = get_balance(card)
    now = datetime.now().strftime("%Y/%m/%d - %H:%M")
    templates = {
        'ملی': f"مشتری گرامی،\nواریز به حساب شما مبلغ {amount:,} ریال\nتاریخ: {now}\nمانده: {balance:,} ریال",
        'ملت': f"مبلغ {amount:,} ریال به حساب شما واریز شد.\nتاریخ: {now}\nمانده: {balance:,} ریال\nبانک ملت",
        'صادرات': f"واریزی به مبلغ: {amount:,} ریال\nحساب شما در بانک صادرات شارژ شد.\nمانده: {balance:,} ریال",
        'پاسارگاد': f"برداشت: 0\nواریز: {amount:,} ریال\nتاریخ: {now}\nمانده: {balance:,} ریال",
        'تجارت': f"واریز جدید به حساب شما: {amount:,} ریال\nتاریخ: {now}\nمانده: {balance:,} ریال",
        'رفاه': f"مبلغ {amount:,} ریال به کارت شما واریز شد.\nمانده: {balance:,} ریال\nبانک رفاه",
        'کشاورزی': f"📥 واریز: {amount:,} ریال\nتاریخ: {now}\nمانده: {balance:,} ریال",
        'مهر ایران': f"واریز انجام شد: {amount:,} ریال\nکارت مقصد: {card}\nمانده حساب: {balance:,} ریال",
        'مسکن': f"مبلغ {amount:,} ریال به حساب واریز شد.\nبانک مسکن\nتاریخ: {now}\nمانده: {balance:,} ریال",
        'بلو': f"✅ واریز موفق: {amount:,} ریال\nحساب شما شارژ شد.\nبانک دیجیتال Blu"
    }
    return templates.get(bank, f"واریز: {amount:,} ریال\nتاریخ: {now}\nمانده: {balance:,} ریال")

@bot.message_handler(commands=['start'])
def start(message):
    if not is_user_registered(message.chat.id):
        bot.send_message(message.chat.id, "❌ شما ثبت‌نام نشده‌اید. /register را بزنید.")
        return
    bot.send_message(message.chat.id, "سلام! مبلغ واریزی را وارد کنید:")

@bot.message_handler(commands=['register'])
def register(message):
    user_id = message.chat.id
    if is_user_registered(user_id):
        bot.send_message(user_id, "✅ قبلاً ثبت‌نام کرده‌اید.")
    elif is_user_pending(user_id):
        bot.send_message(user_id, "⏳ درخواست شما در حال بررسی است.")
    else:
        request_registration(user_id)
        bot.send_message(user_id, "📥 درخواست ثبت‌نام ارسال شد. منتظر تایید ادمین باشید.")
        bot.send_message(ADMIN_ID, f"🔐 درخواست جدید:
{user_id}")

@bot.message_handler(commands=['approve'])
def approve(message):
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "⛔ فقط ادمین می‌تواند تایید کند.")
        return
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            bot.reply_to(message, "فرمت درست: /approve USER_ID")
            return
        user_id = int(parts[1])
        if not is_user_pending(user_id):
            bot.reply_to(message, "این کاربر در انتظار نیست.")
            return
        approve_user(user_id)
        bot.send_message(user_id, "🎉 ثبت‌نام شما تایید شد.")
        bot.reply_to(message, f"✅ تایید شد: {user_id}")
    except:
        bot.reply_to(message, "خطا در تایید.")

@bot.message_handler(func=lambda m: True)
def handle_input(message):
    user_id = message.chat.id
    if not is_user_registered(user_id):
        bot.reply_to(message, "❌ شما ثبت‌نام نشده‌اید.")
        return
    if user_id not in user_data:
        try:
            amount = int(message.text.replace(',', '').strip())
            user_data[user_id] = {'amount': amount}
            bot.send_message(user_id, "شماره کارت مقصد را وارد کنید:")
        except ValueError:
            bot.send_message(user_id, "لطفاً عدد معتبر وارد کنید.")
        return
    if 'card' not in user_data[user_id]:
        card = message.text.strip()
        user_data[user_id]['card'] = card
        db = load_json(CARD_DB, {})
        if card in db:
            user_data[user_id]['mobile'] = db[card]
            bot.send_message(user_id, f"📲 شماره موبایل ذخیره‌شده: {db[card]}\nدر حال ارسال پیامک...")
            send_and_clear(user_id)
        else:
            bot.send_message(user_id, "شماره موبایل مربوط به کارت را وارد کنید:")
        return
    if 'mobile' not in user_data[user_id]:
        mobile = message.text.strip()
        user_data[user_id]['mobile'] = mobile
        db = load_json(CARD_DB, {})
        db[user_data[user_id]['card']] = mobile
        save_json(CARD_DB, db)
        bot.send_message(user_id, "✅ شماره موبایل ذخیره شد. در حال ارسال پیامک...")
        send_and_clear(user_id)
        return

def send_and_clear(user_id):
    d = user_data[user_id]
    balance = update_balance(d['card'], d['amount'])
    msg = fake_sms(d['amount'], d['card'], balance=balance)
    send_sms(d['mobile'], msg)
    bot.send_message(user_id, "📤 پیامک ارسال شد.")
    del user_data[user_id]

bot.polling()
