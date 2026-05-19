import logging
import os
import requests
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ADMIN_ID = 8301711838
USDT_ADDRESS = "0xcDc6120ABdb68041C7c64C21167601b89f74fd0e"
USDT_NETWORK = "BEP20"

SUBSCRIPTION_PLANS = {
    "1month": {"name": "1 Month", "price": 150, "days": 30},
    "3months": {"name": "3 Months", "price": 400, "days": 90}
}

subscriptions = {}

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

def is_subscribed(user_id):
    if user_id == ADMIN_ID:
        return True
    if user_id in subscriptions:
        if subscriptions[user_id]["expiry"] > datetime.now():
            return True
    return False

def get_expiry(user_id):
    if user_id in subscriptions:
        return subscriptions[user_id]["expiry"].strftime("%Y-%m-%d")
    return "Not subscribed"

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
    user_id = update.message.from_user.id
    if not is_subscribed(user_id):
        text = (
            "⭐ Choose Your Plan!\n\n"
            "Ready to buy your subscription? Select the plan that fits your needs:"
        )
        keyboard = [
            [InlineKeyboardButton("1 month - 150$", callback_data="buy_1month")],
            [InlineKeyboardButton("3 months - 400$", callback_data="buy_3months")],
        ]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

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
    user_id = query.from_user.id

    if query.data.startswith("buy_"):
        plan_key = query.data.replace("buy_", "")
        plan = SUBSCRIPTION_PLANS[plan_key]
        text = (
            f"💳 Payment Instructions\n\n"
            f"Plan: {plan['name']}\n"
            f"Price: ${plan['price']} USDT\n\n"
            f"Send exactly ${plan['price']} USDT to:\n\n"
            f"`{USDT_ADDRESS}`\n\n"
            f"Network: {USDT_NETWORK}\n\n"
            f"After payment, send the transaction screenshot or TXID to confirm your payment.\n\n"
            f"⚠️ Make sure to send the exact amount!"
        )
        user_states[chat_id] = f"waiting_payment_{plan_key}"
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="back_to_plans")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "back_to_plans":
        text = (
            "⭐ Choose Your Plan!\n\n"
            "Ready to buy your subscription? Select the plan that fits your needs:"
        )
        keyboard = [
            [InlineKeyboardButton("1 month - 150$", callback_data="buy_1month")],
            [InlineKeyboardButton("3 months - 400$", callback_data="buy_3months")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("approve_"):
        if user_id == ADMIN_ID:
            parts = query.data.split("_")
            target_user = int(parts[1])
            plan_key = parts[2]
            plan = SUBSCRIPTION_PLANS[plan_key]
            expiry = datetime.now() + timedelta(days=plan["days"])
            subscriptions[target_user] = {"plan": plan_key, "expiry": expiry}
            await query.edit_message_text(f"✅ Approved! User {target_user} - {plan['name']} until {expiry.strftime('%Y-%m-%d')}")
            try:
                await context.bot.send_message(
                    chat_id=target_user,
                    text=f"✅ Your subscription has been approved!\n\nPlan: {plan['name']}\nExpiry: {expiry.strftime('%Y-%m-%d')}\n\nSend /start to begin!"
                )
            except:
                pass

    elif query.data.startswith("reject_"):
        if user_id == ADMIN_ID:
            parts = query.data.split("_")
            target_user = int(parts[1])
            await query.edit_message_text(f"❌ Rejected user {target_user}")
            try:
                await context.bot.send_message(
                    chat_id=target_user,
                    text="❌ Your payment was not confirmed. Please contact admin or try again."
                )
            except:
                pass

    elif query.data == "toggle":
        if not is_subscribed(user_id):
            await query.answer("⚠️ Please subscribe first!", show_alert=True)
            return
        settings["running"] = not settings["running"]
        status = "🟢 Bot Started!" if settings["running"] else "🔴 Bot Stopped!"
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="back")]]
        await query.edit_message_text(status, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "settings":
        if not is_subscribed(user_id):
            await query.answer("⚠️ Please subscribe first!", show_alert=True)
            return
        text = "⚙️ Settings Menu\nFor optimal bot operation, please ensure all settings are configured:"
        keyboard = [
            [InlineKeyboardButton(f"Bot name [{settings['bot_name']}]", callback_data="set_botname")],
            [InlineKeyboardButton(f"Fiat [{settings['fiat']}]", callback_data="set_fiat")],
            [InlineKeyboardButton(f"Pay Methods [{len(settings['pay_methods'])}]", callback_data="no")],
            [InlineKeyboardButton(f"Coin [{settings['coin']}]", callback_data="set_coin")],
            [InlineKeyboardButton(f"Max amount [{settings['max_amount']}]", callback_data="set_max")],
            [InlineKeyboardButton(f"Min amount [{settings['min_amount']}]", callback_data="set_min")],
            [InlineKeyboardButton(f"Target: [price]", callback_data="no")],
            [InlineKeyboardButton(f"Target price [Less {settings['target_value']}]", callback_data="set_target")],
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
        text = (
            "🌍 Select Your National Currency!\n\n"
            "To ensure orders at the best prices in your market, "
            "please choose the currency of your country.\n\n"
            "For example: if you're in Myanmar, enter MMK; "
            "if in Thailand, enter THB; if in USA, enter USD.\n\n"
            "What is the currency code for your country?\n\n"
            "Simply enter the currency code of your country "
            "to get started and personalize your trading journey. "
            "Happy trading! 🚀"
        )
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
        text = "🪙 Select Your Coin!\n\nPlease choose the cryptocurrency you want to trade."
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

    elif query.data == "set_target":
        user_states[chat_id] = "waiting_target"
        keyboard = [[InlineKeyboardButton("◀️ Cancel", callback_data="settings")]]
        await query.edit_message_text(
            f"🎯 Enter Target Price:\n\nCurrent: {settings['target_value']}\n\nType the new target price (numbers only)",
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
            f"🎯 Target Price: {settings['target_value']}\n"
            f"🤖 Status: {'Running' if settings['running'] else 'Stopped'}\n"
            f"🔑 API Key: {'✅ Set' if settings['api_key'] else '❌ Not Set'}\n"
            f"📅 Subscription: {get_expiry(user_id)}\n"
        )
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "toggle_bank":
        settings["take_full_bank"] = not settings["take_full_bank"]

    elif query.data == "no":
        await query.answer("Coming soon!", show_alert=True)

    elif query.data == "back":
        if not is_subscribed(user_id):
            text = (
                "⭐ Choose Your Plan!\n\n"
                "Ready to buy your subscription? Select the plan that fits your needs:"
            )
            keyboard = [
                [InlineKeyboardButton("1 month - 150$", callback_data="buy_1month")],
                [InlineKeyboardButton("3 months - 400$", callback_data="buy_3months")],
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            return
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
    user_id = update.message.from_user.id
    text = update.message.text

    if chat_id in user_states:
        state = user_states[chat_id]

        if state.startswith("waiting_payment_"):
            plan_key = state.replace("waiting_payment_", "")
            plan = SUBSCRIPTION_PLANS[plan_key]
            await update.message.reply_text(
                f"✅ Payment screenshot received!\n\nWaiting for admin approval...\n\nPlan: {plan['name']} - ${plan['price']}"
            )
            keyboard = [
                [InlineKeyboardButton(f"✅ Approve {plan['name']}", callback_data=f"approve_{user_id}_{plan_key}")],
                [InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}_{plan_key}")]
            ]
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"💳 New Payment Request!\n\n"
                    f"User ID: {user_id}\n"
                    f"Username: @{update.message.from_user.username or 'N/A'}\n"
                    f"Plan: {plan['name']} - ${plan['price']} USDT\n\n"
                    f"Payment proof received. Please verify and approve/reject."
                ),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            user_states.pop(chat_id)

        elif state == "waiting_botname":
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

        elif state == "waiting_target":
            try:
                settings["target_value"] = int(text)
                user_states.pop(chat_id)
                keyboard = [[InlineKeyboardButton("◀️ Back to Settings", callback_data="settings")]]
                await update.message.reply_text(f"✅ Target price changed to: {text}", reply_markup=InlineKeyboardMarkup(keyboard))
            except ValueError:
                await update.message.reply_text("❌ Numbers only! Example: 3100")

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
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    print("Bot running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
