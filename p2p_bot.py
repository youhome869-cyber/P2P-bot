import logging
import asyncio
import hmac
import hashlib
import time
import json
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ==================== SETTINGS ====================
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
ADMIN_IDS = []  # သင့် Telegram ID ထည့်ပါ ဥပမာ [123456789]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# States
(MAIN_MENU, SET_API_KEY, SET_SECRET_KEY, SET_COIN,
 SET_MIN_PRICE, SET_MAX_PRICE, SET_AMOUNT, RUNNING) = range(8)

# User data store
user_data_store = {}

def default_user():
    return {
        "api_key": "",
        "secret_key": "",
        "coin": "USDT",
        "min_price": 0,
        "max_price": 9999999,
        "amount": 100,
        "running": False,
        "trade_count": 0,
        "profit": 0.0,
    }

# ==================== BINANCE P2P API ====================

def get_p2p_orders(coin="USDT", fiat="MMK", side="BUY", rows=10):
    """Binance P2P orders fetch (public API)"""
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    payload = {
        "asset": coin,
        "fiat": fiat,
        "merchantCheck": False,
        "page": 1,
        "payTypes": [],
        "publisherType": None,
        "rows": rows,
        "tradeType": side,
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        data = response.json()
        return data.get("data", [])
    except Exception as e:
        logger.error(f"P2P fetch error: {e}")
        return []

def binance_signed_request(api_key, secret_key, method, endpoint, params=None):
    """Binance signed API request"""
    base_url = "https://api.binance.com"
    if params is None:
        params = {}
    params["timestamp"] = int(time.time() * 1000)
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(
        secret_key.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    query_string += f"&signature={signature}"
    headers = {"X-MBX-APIKEY": api_key}
    url = f"{base_url}{endpoint}?{query_string}"
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=10)
        else:
            r = requests.post(url, headers=headers, timeout=10)
        return r.json()
    except Exception as e:
        logger.error(f"Binance API error: {e}")
        return None

def get_market_price(coin="USDT", fiat="MMK"):
    """Get current market price from P2P"""
    orders = get_p2p_orders(coin, fiat, "BUY", 5)
    if orders:
        prices = [float(o["adv"]["price"]) for o in orders]
        return sum(prices) / len(prices)
    return 0

# ==================== KEYBOARDS ====================

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
         InlineKeyboardButton("📊 Status", callback_data="status")],
        [InlineKeyboardButton("▶️ Start Bot", callback_data="start_bot"),
         InlineKeyboardButton("⏹ Stop Bot", callback_data="stop_bot")],
        [InlineKeyboardButton("📈 Market Price", callback_data="market_price")],
    ])

def settings_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Set API Key", callback_data="set_api")],
        [InlineKeyboardButton("🪙 Set Coin", callback_data="set_coin")],
        [InlineKeyboardButton("💵 Set Min Price", callback_data="set_min")],
        [InlineKeyboardButton("💵 Set Max Price", callback_data="set_max")],
        [InlineKeyboardButton("💰 Set Amount", callback_data="set_amount")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")],
    ])

# ==================== HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data_store:
        user_data_store[user_id] = default_user()
    await update.message.reply_text(
        "🤖 *Binance P2P Bot*\n\n"
        "Auto detect & buy P2P orders below market price.\n\n"
        "⚠️ API Key ထည့်ပြီးမှ Bot စတင်ပါ။",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )
    return MAIN_MENU

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in user_data_store:
        user_data_store[user_id] = default_user()
    ud = user_data_store[user_id]
    data = query.data

    if data == "main_menu":
        await query.edit_message_text(
            "🤖 *Binance P2P Bot*\n\nMenu ရွေးပါ:",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )
        return MAIN_MENU

    elif data == "settings":
        text = (
            f"⚙️ *Current Settings*\n\n"
            f"🔑 API Key: `{'✅ Set' if ud['api_key'] else '❌ Not set'}`\n"
            f"🪙 Coin: `{ud['coin']}`\n"
            f"💵 Min Price: `{ud['min_price']} MMK`\n"
            f"💵 Max Price: `{ud['max_price']} MMK`\n"
            f"💰 Amount: `{ud['amount']} USDT`\n"
        )
        await query.edit_message_text(text, parse_mode="Markdown",
                                       reply_markup=settings_keyboard())
        return MAIN_MENU

    elif data == "status":
        status = "🟢 Running" if ud["running"] else "🔴 Stopped"
        text = (
            f"📊 *Bot Status*\n\n"
            f"Status: {status}\n"
            f"Trade Count: `{ud['trade_count']}`\n"
            f"Total Profit: `{ud['profit']:.2f} USDT`\n"
        )
        await query.edit_message_text(text, parse_mode="Markdown",
                                       reply_markup=main_keyboard())

    elif data == "market_price":
        price = get_market_price(ud["coin"])
        await query.edit_message_text(
            f"📈 *{ud['coin']}/MMK Market Price*\n\n"
            f"Average: `{price:,.0f} MMK`",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )

    elif data == "start_bot":
        if not ud["api_key"]:
            await query.edit_message_text(
                "❌ API Key မထည့်ရသေးပါ!\n\nSettings → Set API Key",
                reply_markup=main_keyboard()
            )
            return MAIN_MENU
        ud["running"] = True
        await query.edit_message_text(
            "✅ *Bot Started!*\n\nP2P orders ကို monitor လုပ်နေပြီ...",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )
        asyncio.create_task(monitor_orders(context, user_id))

    elif data == "stop_bot":
        ud["running"] = False
        await query.edit_message_text(
            "⏹ *Bot Stopped.*",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )

    elif data == "set_api":
        await query.edit_message_text(
            "🔑 Binance API Key ထည့်ပါ:\n\n"
            "(Binance → Settings → API Management)",
        )
        return SET_API_KEY

    elif data == "set_coin":
        await query.edit_message_text("🪙 Coin ထည့်ပါ (ဥပမာ: USDT, BTC, ETH):")
        return SET_COIN

    elif data == "set_min":
        await query.edit_message_text("💵 Minimum Price (MMK) ထည့်ပါ:")
        return SET_MIN_PRICE

    elif data == "set_max":
        await query.edit_message_text("💵 Maximum Price (MMK) ထည့်ပါ:")
        return SET_MAX_PRICE

    elif data == "set_amount":
        await query.edit_message_text("💰 Buy Amount (USDT) ထည့်ပါ:")
        return SET_AMOUNT

    return MAIN_MENU

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in user_data_store:
        user_data_store[user_id] = default_user()
    ud = user_data_store[user_id]

    state = context.user_data.get("state", MAIN_MENU)

    if state == SET_API_KEY:
        ud["api_key"] = text
        context.user_data["state"] = SET_SECRET_KEY
        await update.message.reply_text("✅ API Key သိမ်းပြီ!\n\n🔐 Secret Key ထည့်ပါ:")
        return SET_SECRET_KEY

    elif state == SET_SECRET_KEY:
        ud["secret_key"] = text
        context.user_data["state"] = MAIN_MENU
        await update.message.reply_text("✅ API Keys သိမ်းပြီ!", reply_markup=main_keyboard())
        return MAIN_MENU

    elif state == SET_COIN:
        ud["coin"] = text.upper()
        context.user_data["state"] = MAIN_MENU
        await update.message.reply_text(f"✅ Coin: {ud['coin']}", reply_markup=main_keyboard())
        return MAIN_MENU

    elif state == SET_MIN_PRICE:
        try:
            ud["min_price"] = float(text)
            context.user_data["state"] = MAIN_MENU
            await update.message.reply_text(f"✅ Min Price: {ud['min_price']:,.0f} MMK",
                                             reply_markup=main_keyboard())
        except:
            await update.message.reply_text("❌ ဂဏန်းသာ ထည့်ပါ!")
        return MAIN_MENU

    elif state == SET_MAX_PRICE:
        try:
            ud["max_price"] = float(text)
            context.user_data["state"] = MAIN_MENU
            await update.message.reply_text(f"✅ Max Price: {ud['max_price']:,.0f} MMK",
                                             reply_markup=main_keyboard())
        except:
            await update.message.reply_text("❌ ဂဏန်းသာ ထည့်ပါ!")
        return MAIN_MENU

    elif state == SET_AMOUNT:
        try:
            ud["amount"] = float(text)
            context.user_data["state"] = MAIN_MENU
            await update.message.reply_text(f"✅ Amount: {ud['amount']} USDT",
                                             reply_markup=main_keyboard())
        except:
            await update.message.reply_text("❌ ဂဏန်းသာ ထည့်ပါ!")
        return MAIN_MENU

    await update.message.reply_text("Menu ကနေ ရွေးပါ:", reply_markup=main_keyboard())
    return MAIN_MENU

# ==================== AUTO MONITOR ====================

async def monitor_orders(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Auto monitor P2P orders and alert when below market price"""
    ud = user_data_store.get(user_id)
    if not ud:
        return

    logger.info(f"Starting monitor for user {user_id}")

    while ud.get("running"):
        try:
            market_price = get_market_price(ud["coin"])
            orders = get_p2p_orders(ud["coin"], "MMK", "BUY", 20)

            for order in orders:
                adv = order.get("adv", {})
                price = float(adv.get("price", 0))
                min_amt = float(adv.get("minSingleTransAmount", 0))
                max_amt = float(adv.get("maxSingleTransAmount", 0))
                advertiser = order.get("advertiser", {})
                nick = advertiser.get("nickName", "Unknown")

                # Check if price is below market and within range
                if (price < market_price * 0.998 and
                        ud["min_price"] <= price <= ud["max_price"] and
                        min_amt <= ud["amount"] <= max_amt):

                    diff_pct = ((market_price - price) / market_price) * 100
                    msg = (
                        f"🚨 *Low Price Order Found!*\n\n"
                        f"👤 Seller: `{nick}`\n"
                        f"💵 Price: `{price:,.0f} MMK`\n"
                        f"📈 Market: `{market_price:,.0f} MMK`\n"
                        f"📉 Diff: `{diff_pct:.2f}%` below market\n"
                        f"💰 Amount: `{min_amt} - {max_amt} USDT`\n"
                        f"⏰ Time: `{datetime.now().strftime('%H:%M:%S')}`"
                    )
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=msg,
                        parse_mode="Markdown"
                    )
                    ud["trade_count"] += 1
                    await asyncio.sleep(5)  # Avoid duplicate alerts

        except Exception as e:
            logger.error(f"Monitor error: {e}")

        await asyncio.sleep(30)  # Check every 30 seconds

    logger.info(f"Monitor stopped for user {user_id}")

# ==================== MAIN ====================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot started...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
