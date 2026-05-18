import logging
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8782322070:AAHzQmC2OkjdKmQlVdxR-KXUJDCCNFtQATk")

settings = {
    "bot_name": "Lucky Money",
    "fiat": "MMK",
    "coin": "USDT",
    "max_amount": 15000000,
    "min_amount": 180000,
    "target_value": 3100,
    "max_orders": 1,
    "take_full_bank": False,
    "pay_methods": [],
    "running": False
}

logging.basicConfig(level=logging.INFO)

def get_best_price(trade_type="BUY"):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    payload = {
        "asset": settings["coin"],
        "fiat": settings["fiat"],
        "merchantCheck": False,
        "page": 1,
        "payTypes": [],
        "publisherType": None,
        "rows": 20,
        "tradeType": trade_type
    }
    try:
        r = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        data = r.json().get("data", [])
        if data:
            return float(data[0]["adv"]["price"])
    except Exception as e:
        logging.error(f"Error: {e}")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = "🟢 Running" if settings["running"] else "🔴 Stopped"
    text = (
        f"🎰 Welcome to the {settings['bot_name']} Menu!\n\n"
        f"Status of your bot: {status}\n\n"
        f"🚀 Start Operation — Launch the bot\n"
        f"⚙️ Configure — Modify settings\n\n"
        f"Select an option to continue!"
    )
    keyboard = [
        [InlineKeyboardButton("🚀 Start Bot" if not settings["running"] else "⏹ Stop Bot", callback_data="toggle")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("📊 Statistics", callback_data="stats")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "toggle":
        settings["running"] = not settings["running"]
        status = "🟢 Bot Started!" if settings["running"] else "🔴 Bot Stopped!"
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="back")]]
        await query.edit_message_text(status, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "settings":
        text = "⚙️ Settings Menu\n\nBot settings:"
        keyboard = [
            [InlineKeyboardButton(f"Bot name [{settings['bot_name']}]", callback_data="no")],
            [InlineKeyboardButton(f"Fiat [{settings['fiat']}]", callback_data="no")],
            [InlineKeyboardButton(f"Coin [{settings['coin']}]", callback_data="no")],
            [InlineKeyboardButton(f"Max amount [{settings['max_amount']}]", callback_data="no")],
            [InlineKeyboardButton(f"Min amount [{settings['min_amount']}]", callback_data="no")],
            [InlineKeyboardButton(f"Target price [Less {settings['target_value']}]", callback_data="no")],
            [InlineKeyboardButton(f"Max orders [{settings['max_orders']}]", callback_data="no")],
            [InlineKeyboardButton(f"Full bank [{'On' if settings['take_full_bank'] else 'Off'}]", callback_data="toggle_bank")],
            [InlineKeyboardButton("◀️ Back", callback_data="back")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "stats":
        buy = get_best_price("BUY")
        sell = get_best_price("SELL")
        text = (
            f"📊 Statistics\n\n"
            f"💰 Best Buy: {buy} {settings['fiat']}\n"
            f"💸 Best Sell: {sell} {settings['fiat']}\n"
            f"🤖 Status: {'Running' if settings['running'] else 'Stopped'}\n"
        )
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "toggle_bank":
        settings["take_full_bank"] = not settings["take_full_bank"]

    elif query.data == "back":
        status = "🟢 Running" if settings["running"] else "🔴 Stopped"
        text = f"🎰 {settings['bot_name']} Menu\n\nStatus: {status}"
        keyboard = [
            [InlineKeyboardButton("🚀 Start Bot" if not settings["running"] else "⏹ Stop Bot", callback_data="toggle")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
            [InlineKeyboardButton("📊 Statistics", callback_data="stats")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    print("Bot running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
