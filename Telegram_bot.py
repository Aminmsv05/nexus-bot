import os
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# وارد کردن مغز نکسوس از app.py
from app import chat_with_nexus

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN در فایل .env پیدا نشد.")

# حافظه جدا برای هر کاربر تلگرام
user_histories = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "سلام 👋\n"
        "من *نکسوس* هستم؛ دستیار شخصی هوشمند شما.\n\n"
        "می‌توانم کمکتان کنم در:\n"
        "• پاسخ به سوالات روزمره\n"
        "• انجام محاسبات\n"
        "• یادداشت‌برداری و مدیریت کارها\n"
        "• تولید رمز عبور امن\n"
        "• تبدیل واحدها\n"
        "• خواندن و خلاصه‌سازی متن\n\n"
        "فقط پیام خود را بنویسید.\n"
        "برای راهنما: /help"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *راهنمای نکسوس*\n\n"
        "مثال‌ها:\n"
        "• ساعت چند است؟\n"
        "• ۲۵۰ تقسیم بر ۵\n"
        "• این را یادداشت کن: فردا جلسه دارم\n"
        "• لیست کارها را نشان بده\n"
        "• یک رمز ۱۶ کاراکتری بساز\n"
        "• ۲۵ درجه سانتی‌گراد چند فارنهایت است؟\n\n"
        "دستورها:\n"
        "/start - شروع مجدد\n"
        "/help - نمایش همین راهنما"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if not text:
        await update.message.reply_text("لطفاً یک پیام متنی بفرست.")
        return

    # تاریخچه این کاربر
    history = user_histories.get(user_id, [])

    try:
        # استفاده از همان مغز نکسوس
        reply = chat_with_nexus(text, history)

        # آپدیت حافظه
        history = history + [
            {"role": "user", "content": text},
            {"role": "assistant", "content": reply}
        ]

        # فقط پیام‌های اخیر را نگه می‌داریم
        user_histories[user_id] = history[-20:]

        await update.message.reply_text(reply)

    except Exception as e:
        print("TELEGRAM ERROR:", e)
        await update.message.reply_text(
            "متأسفم، یک خطا رخ داد. لطفاً دوباره امتحان کن."
        )


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("ربات نکسوس روشن شد...")
    app.run_polling()


if __name__ == "__main__":
    main()