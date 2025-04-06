from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import requests
from flask import Flask
from threading import Thread
import os

# Web server Flask untuk mencegah Render tidur
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Telegram aktif!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# Ambil token dari environment variable
TOKEN = os.getenv("BOT_TOKEN")

# API Endpoint & seller code
REQ_OTP_URL = "https://nomorxlku.my.id/api/req_otp.php"
VER_OTP_URL = "https://nomorxlku.my.id/api/ver_otp.php"
CHECK_QUOTA_URL = "https://nomorxlku.my.id/api/check_quota.php"
CHECK_VERIF_URL = "https://nomorxlku.my.id/api/check_ver_otp.php"
SELLER_CODE = "6cdeb687424a7d7a641d0494dfb2ec23"

MSISDN, OTP, CHECK_MSISDN = range(3)
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("📲 Login Nomor XL")],
        [KeyboardButton("📊 Cek Kuota"), KeyboardButton("ℹ️ Cek Status Verifikasi")],
        [KeyboardButton("🚪 Logout"), KeyboardButton("🆘 Bantuan Admin")]
    ]
    await update.message.reply_text("🔹 *Selamat Datang!* 🔹\nSilakan pilih menu di bawah:",
                                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
                                    parse_mode="Markdown")

async def login_xl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📌 Masukkan nomor XL kamu (08xxx / 628xxx):")
    return MSISDN

async def request_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msisdn = update.message.text.strip()
    if not msisdn.startswith("08") and not msisdn.startswith("628"):
        await update.message.reply_text("❌ Nomor tidak valid!")
        return ConversationHandler.END

    user_data[update.message.chat_id] = {"msisdn": msisdn}
    try:
        res = requests.post(REQ_OTP_URL, data={"msisdn": msisdn, "seller_code": SELLER_CODE}, timeout=10).json()
        if res.get("status"):
            user_data[update.message.chat_id]["auth_id"] = res["data"]["auth_id"]
            await update.message.reply_text(f"📨 OTP dikirim ke {msisdn}.", reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("✅ Masukkan OTP", callback_data="masukkan_otp")]]))
            return OTP
        else:
            await update.message.reply_text(f"❌ Gagal: {res.get('message')}")
            return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")
        return ConversationHandler.END

async def input_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.delete()
    await update.callback_query.message.reply_text("🔑 Masukkan kode OTP:")
    return OTP

async def verify_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    otp_code = update.message.text.strip()
    info = user_data.get(chat_id, {})

    try:
        res = requests.post(VER_OTP_URL, data={
            "msisdn": info["msisdn"], "auth_id": info["auth_id"], "otp": otp_code
        }, timeout=10).json()

        if res.get("status"):
            user_data[chat_id]["access_token"] = res["data"]["access_token"]
            await update.message.reply_text("✅ Login berhasil!")
        else:
            await update.message.reply_text(f"❌ Gagal verifikasi: {res.get('message')}")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")
        return ConversationHandler.END

async def check_quota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    access_token = user_data.get(chat_id, {}).get("access_token")
    if not access_token:
        await update.message.reply_text("⚠️ Belum login.")
        return

    try:
        res = requests.post(CHECK_QUOTA_URL, data={"access_token": access_token}, timeout=10).json()
        if res.get("status"):
            text = "📊 *Informasi Kuota:*\n\n"
            for q in res["data"]["quotas"]:
                text += f"📌 *{q['name']}*\n🕒 Exp: {q['expired_at']}\n"
                for b in q["benefits"]:
                    text += f"🔹 {b['name']}: {b['quota']} (Sisa: {b['remaining_quota']})\n"
                text += "\n"
            await update.message.reply_text(text, parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ {res.get('message')}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data.pop(update.message.chat_id, None)
    await update.message.reply_text("🚪 Logout berhasil.")

async def bantuan_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📞 Hubungi: [Admin](https://t.me/admin_bot)", parse_mode="Markdown")

async def request_verifikasi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📌 Masukkan nomor XL:")
    return CHECK_MSISDN

async def check_verifikasi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msisdn = update.message.text.strip()
    if not msisdn.startswith("08") and not msisdn.startswith("628"):
        await update.message.reply_text("❌ Nomor tidak valid!")
        return CHECK_MSISDN

    try:
        res = requests.post(CHECK_VERIF_URL, data={"username": SELLER_CODE, "msisdn": msisdn}, timeout=10).json()
        message = res.get("message", "Tidak diketahui.")
        await update.message.reply_text(f"ℹ️ *Status Verifikasi:* {message}", parse_mode="Markdown")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")
        return ConversationHandler.END

def main():
    keep_alive()
    bot = Application.builder().token(TOKEN).build()

    login_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📲 Login Nomor XL$"), login_xl)],
        states={MSISDN: [MessageHandler(filters.TEXT, request_otp)],
                OTP: [MessageHandler(filters.TEXT, verify_otp)]},
        fallbacks=[]
    )

    verif_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^ℹ️ Cek Status Verifikasi$"), request_verifikasi)],
        states={CHECK_MSISDN: [MessageHandler(filters.TEXT, check_verifikasi)]},
        fallbacks=[]
    )

    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(login_conv)
    bot.add_handler(verif_conv)
    bot.add_handler(MessageHandler(filters.Regex("^📊 Cek Kuota$"), check_quota))
    bot.add_handler(MessageHandler(filters.Regex("^🚪 Logout$"), logout))
    bot.add_handler(MessageHandler(filters.Regex("^🆘 Bantuan Admin$"), bantuan_admin))
    bot.add_handler(CallbackQueryHandler(input_otp, pattern="masukkan_otp"))
    print("Bot aktif.")
    bot.run_polling()

if __name__ == "__main__":
    main()
