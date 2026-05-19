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
