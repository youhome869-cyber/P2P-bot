import logging
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")

settings = {
    "bot_name": "Lucky Money",
    "fiat": "MMK",
    "coin": "USDT",
    "max_amount": 15000000,
    "min_amount": 180000,
    "target_value": 3100,
    "max_orders": 1,
    "take_full_bank": False,
    "pay_methods": ["AYA Pay", "Bank Transfer", "CB Pay", "Cash Deposit to Bank", "KBZPay", "WavePay", "Airtime Mobile Top-Up", "Spring Development Bank", "Transfers with specific bank", "Wave Mobile Money", "Wave Money", "Yoma Bank", "uabpay"],
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
        "payTypes": settings["pay_methods"],
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
            [InlineKeyboardButton(f"Bot name [{settings['bot_name']}]", callback_data="set_botname")],
            [InlineKeyboardButton(f"Fiat [{settings['fiat']}]", callback_data="set_fiat")],
            [InlineKeyboardButton(f"Pay Methods [{len(settings['pay_methods'])}]", callback_data="no")],
            [InlineKeyboardButton(f"Coin [{settings['coin']}]", callback_data="set_coin")],
            [InlineKeyboardButton(f"Max amount [{settings['max_amount']}]", callback_data="set_max")],
            [InlineKeyboardButton(f"Min amount [{settings['min_amount']}]", callback_data="set_min")],
            [InlineKeyboardButton(f"Target: [price]", callback_data="no")],
            [InlineKeyboardButton(f"Target price/percent [Less {settings['target_value']}]", callback_data="no")],
            [InlineKeyboardButton(f"Max num orders [{settings['max_orders']}]", callback_data="no")],
            [InlineKeyboardButton(f"Take Full bank orders [{'On' if settings['take_full_bank'] else 'Off'}]", callback_data="toggle_bank")],
            [InlineKeyboardButton("🔑 API Key", callback_data="api_key_menu")],
            [InlineKeyboardButton("◀️ Back", callback_data="back")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "set_botname":
        user_states[chat_id] = "waiting_botname"
        keyboard = [[InlineKeyboardButton("◀️ Cancel", callback_data="settings")]]
        await query.edit_message_text("🤖 Enter new Bot Name:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "set_fiat":
        text = "💱 Select Fiat Currency:"
        keyboard = [
            [InlineKeyboardButton("MMK 🇲🇲", callback_data="fiat_MMK")],
            [InlineKeyboardButton("THB 🇹🇭", callback_data="fiat_THB")],
            [InlineKeyboardButton("USD 🇺🇸", callback_data="fiat_USD")],
            [InlineKeyboardButton("SGD 🇸🇬", callback_data="fiat_SGD")],
            [InlineKeyboardButton("MYR 🇲🇾", callback_data="fiat_MYR")],
            [InlineKeyboardButton("✏️ Custom", callback_data="fiat_custom")],
            [InlineKeyboardButton("◀️ Back", callback_data="settings")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("fiat_"):
        fiat = query.data.replace("fiat_", "")
        if fiat == "custom":
            user_states[chat_id] = "waiting_fiat"
            keyboard = [[InlineKeyboardButton("◀️ Cancel", callback_data="set_fiat")]]
            await query.edit_message_text("💱 Enter Fiat currency code:\n\nExample: MMK, THB, USD", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            settings["fiat"] = fiat
            keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="settings")]]
            await query.edit_message_text(f"✅ Fiat changed to: {fiat}", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "set_coin":
        text = "🪙 Select Coin:"
        keyboard = [
            [InlineKeyboardButton("USDT", callback_data="coin_USDT")],
            [InlineKeyboardButton("BTC", callback_data="coin_BTC")],
            [InlineKeyboardButton("ETH", callback_data="coin_ETH")],
            [InlineKeyboardButton("BNB", callback_data="coin_BNB")],
            [InlineKeyboardButton("✏️ Custom", callback_data="coin_custom")],
            [InlineKeyboardButton("◀️ Back", callback_data="settings")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("coin_"):
        coin = query.data.replace("coin_", "")
        if coin == "custom":
            user_states[chat_id] = "waiting_coin"
            keyboard = [[InlineKeyboardButton("◀️ Cancel", callback_data="set_coin")]]
            await query.edit_message_text("🪙 Enter Coin name:\n\nExample: USDT, BTC, ETH", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            settings["coin"] = coin
            keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="settings")]]
            await query.edit_message_text(f"✅ Coin changed to: {coin}", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "set_max":
        user_states[chat_id] = "waiting_max"
        keyboard = [[InlineKeyboardButton("◀️ Cancel", callback_data="settings")]]
        await query.edit_message_text(
            f"💰 Enter Max Amount:\n\nCurrent: {settings['max_amount']}\n\nType the new amount (numbers only)",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "set_min":
        user_states[chat_id] = "waiting_min"
        keyboard = [[InlineKeyboardButton("◀️ Cancel", callback_data="settings")]]
        await query.edit_message_text(
            f"💵 Enter Min Amount:\n\nCurrent: {settings['min_amount']}\n\nType the new amount (numbers only)",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

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
        await query.edit_message_text("🔑 Enter your Binance API Key:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "add_secret":
        user_states[chat_id] = "waiting_secret_key"
        keyboard = [[InlineKeyboardButton("◀️ Cancel", callback_data="api_key_menu")]]
        await query.edit_message_text("🔐 Enter your Binance Secret Key:", reply_markup=InlineKeyboardMarkup(keyboard))

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

    elif query.data == "no":
        await query.answer("Coming soon!", show_alert=True)

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

        if state == "waiting_botname":
            settings["bot_name"] = text
            user_states.pop(chat_id)
            keyboard = [[InlineKeyboardButton("◀️ Back to Settings", callback_data="settings")]]
            await update.message.reply_text(f"✅ Bot name changed to: {text}", reply_markup=InlineKeyboardMarkup(keyboard))

        elif state == "waiting_fiat":
            settings["fiat"] = text.upper()
            user_states.pop(chat_id)
            keyboard = [[InlineKeyboardButton("◀️ Back to Settings", callback_data="settings")]]
            await update.message.reply_text(f"✅ Fiat changed to: {text.upper()}", reply_markup=InlineKeyboardMarkup(keyboard))

        elif state == "waiting_coin":
            settings["coin"] = text.upper()
            user_states.pop(chat_id)
            keyboard = [[InlineKeyboardButton("◀️ Back to Settings", callback_data="settings")]]
            await update.message.reply_text(f"✅ Coin changed to: {text.upper()}", reply_markup=InlineKeyboardMarkup(keyboard))

        elif state == "waiting_max":
            try:
                settings["max_amount"] = int(text)
                user_states.pop(chat_id)
                keyboard = [[InlineKeyboardButton("◀️ Back to Settings", callback_data="settings")]]
                await update.message.reply_text(f"✅ Max amount changed to: {text}", reply_markup=InlineKeyboardMarkup(keyboard))
            except ValueError:
                await update.message.reply_text("❌ Numbers only! Example: 15000000")

        elif state == "waiting_min":
            try:
                settings["min_amount"] = int(text)
                user_states.pop(chat_id)
                keyboard = [[InlineKeyboardButton("◀️ Back to Settings", callback_data="settings")]]
                await update.message.reply_text(f"✅ Min amount changed to: {text}", reply_markup=InlineKeyboardMarkup(keyboard))
            except ValueError:
                await update.message.reply_text("❌ Numbers only! Example: 180000")

        elif state == "waiting_api_key":
            settings["api_key"] = text
            user_states.pop(chat_id)
            keyboard = [[InlineKeyboardButton("◀️ Back to API Menu", callback_data="api_key_menu")]]
            await update.message.reply_text("✅ API Key saved!", reply_markup=InlineKeyboardMarkup(keyboard))

        elif state == "waiting_secret_key":
            settings["secret_key"] = text
            user_states.pop(chat_id)
            keyboard = [[InlineKeyboardButton("◀️ Back to API Menu", callback_data="api_key_menu")]]
            await update.message.reply_text("✅ Secret Key saved!", reply_markup=InlineKeyboardMarkup(keyboard))

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
