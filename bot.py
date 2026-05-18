import logging
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "")
BINANCE_SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY", "")

settings = {
    "bot_name": "Lucky Money",
    "fiat": "MMK",
    "coin": "USDT",
    "max_amount": 15000000,
    "min_amount": 180000,
    "target_value": 3100,
    "max_orders": 1,
    "take_full_bank": False,
    "pay_methods":"pay_methods": ["AYA Pay", "Bank Transfer", "CB Pay", "Cash Deposit to Bank", "KBZPay", "WavePay", "Airtime Mobile Top-Up", "Spring Development Bank", "Transfers with specific bank", "Wave Mobile Money", "Wave Money", "Yoma Bank", "uabpay"],
    "running": False,
    "api_key": "",
    "secret_key": ""
}

logging.basicConfig(level=logging.INFO)
user_states = {}

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
    chat_id = query.message.chat_id

    if query.data == "toggle":
        settings["running"] = not settings["running"]
        status = "🟢 Bot Started!" if settings["running"] else "🔴 Bot Stopped!"
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="back")]]
        await query.edit_message_text(status, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "settings":
        text = "⚙️ Settings Menu\nFor optimal bot operation, please ensure all settings are configured:"
        keyboard = [
            [InlineKeyboardButton(f"Bot name [{settings['bot_name']}]", callback_data="no")],
            [InlineKeyboardButton(f"Fiat [{settings['fiat']}]", callback_data="no")],
            [InlineKeyboardButton(f"Pay Methods [{len(settings['pay_methods'])}]", callback_data="no")],
            [InlineKeyboardButton(f"Coin [{settings['coin']}]", callback_data="no")],
            [InlineKeyboardButton(f"Max amount [{settings['max_amount']}]", callback_data="no")],
            [InlineKeyboardButton(f"Min amount [{settings['min_amount']}]", callback_data="no")],
            [InlineKeyboardButton(f"Target: [price]", callback_data="no")],
            [InlineKeyboardButton(f"Target price/percent [Less {settings['target_value']}]", callback_data="no")],
            [InlineKeyboardButton(f"Max num orders [{settings['max_orders']}]", callback_data="no")],
            [InlineKeyboardButton(f"Take Full bank orders [{'On' if settings['take_full_bank'] else 'Off'}]", callback_data="toggle_bank")],
            [InlineKeyboardButton("🔑 API Key", callback_data="api_key_menu")],
            [InlineKeyboardButton("◀️ Back", callback_data="back")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "api_key_menu":
        api_status = "✅ Set" if settings["api_key"] else "❌ Not Set"
        secret_status = "✅ Set" if settings["secret_key"] else "❌ Not Set"
        text = (
            f"🔑 API Key Menu\n\n"
            f"API Key: {api_status}\n"
            f"Secret Key: {secret_status}\n\n"
            f"Select option:"
        )
        keyboard = [
            [InlineKeyboardButton("➕ Add API Key", callback_data="add_api")],
            [InlineKeyboardButton("➕ Add Secret Key", callback_data="add_secret")],
            [InlineKeyboardButton("◀️ Back", callback_data="settings")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "add_api":
        user_states[chat_id] = "waiting_api_key"
        keyboard = [[InlineKeyboardButton("◀️ Cancel", callback_data="api_key_menu")]]
        await query.edit_message_text(
            "🔑 Enter your Binance API Key:\n\nType and send your API Key",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "add_secret":
        user_states[chat_id] = "waiting_secret_key"
        keyboard = [[InlineKeyboardButton("◀️ Cancel", callback_data="api_key_menu")]]
        await query.edit_message_text(
            "🔐 Enter your Binance Secret Key:\n\nType and send your Secret Key",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "stats":
        buy = get_best_price("BUY")
        sell = get_best_price("SELL")
        text = (
            f"📊 Statistics\n\n"
            f"💰 Best Buy: {buy} {settings['fiat']}\n"
            f"💸 Best Sell: {sell} {settings['fiat']}\n"
            f"🤖 Status: {'Running' if settings['running'] else 'Stopped'}\n"
            f"🔑 API Key: {'✅ Set' if settings['api_key'] else '❌ Not Set'}\n"
        )
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "toggle_bank":
        settings["take_full_bank"] = not settings["take_full_bank"]
        await button(update, context)

    elif query.data == "back":
        status = "🟢 Running" if settings["running"] else "🔴 Stopped"
        text = f"🎰 {settings['bot_name']} Menu\n\nStatus: {status}"
        keyboard = [
            [InlineKeyboardButton("🚀 Start Bot" if not settings["running"] else "⏹ Stop Bot", callback_data="toggle")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
            [InlineKeyboardButton("📊 Statistics", callback_data="stats")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text

    if chat_id in user_states:
        state = user_states[chat_id]

        if state == "waiting_api_key":
            settings["api_key"] = text
            user_states.pop(chat_id)
            keyboard = [[InlineKeyboardButton("◀️ Back to API Menu", callback_data="api_key_menu")]]
            await update.message.reply_text("✅ API Key saved successfully!", reply_markup=InlineKeyboardMarkup(keyboard))

        elif state == "waiting_secret_key":
            settings["secret_key"] = text
            user_states.pop(chat_id)
            keyboard = [[InlineKeyboardButton("◀️ Back to API Menu", callback_data="api_key_menu")]]
            await update.message.reply_text("✅ Secret Key saved successfully!", reply_markup=InlineKeyboardMarkup(keyboard))

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
