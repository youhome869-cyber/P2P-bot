import os
import logging
import asyncio
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN", "7576496100:AAFezDOM1HRbiXkQx5_GA501kbOGJeLgJds")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

users = {}

def get_user(uid):
    if uid not in users:
        users[uid] = {
            "coin": "USDT",
            "fiat": "MMK",
            "min_price": 0,
            "max_price": 9999999,
            "amount": 100,
            "running": False,
            "trades": 0,
            "waiting": None,
        }
    return users[uid]

def fetch_p2p(coin="USDT", fiat="MMK", rows=20):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    payload = {
        "asset": coin, "fiat": fiat,
        "merchantCheck": False, "page": 1,
        "payTypes": [], "rows": rows, "tradeType": "BUY",
    }
    try:
        r = requests.post(url, json=payload,
                         headers={"Content-Type": "application/json"}, timeout=10)
        return r.json().get("data", [])
    except Exception as e:
        logger.error(f"P2P error: {e}")
        return []

def get_market_price(coin, fiat):
    orders = fetch_p2p(coin, fiat, 5)
    if orders:
        prices = [float(o["adv"]["price"]) for o in orders]
        return round(sum(prices) / len(prices), 2)
    return 0

def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
         InlineKeyboardButton("📊 Status", callback_data="status")],
        [InlineKeyboardButton("▶️ Start", callback_data="start_bot"),
         InlineKeyboardButton("⏹ Stop", callback_data="stop_bot")],
        [InlineKeyboardButton("📈 Market Price", callback_data="price")],
    ])

def settings_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙 Coin", callback_data="set_coin")],
        [InlineKeyboardButton("💵 Min Price", callback_data="set_min")],
        [InlineKeyboardButton("💵 Max Price", callback_data="set_max")],
        [InlineKeyboardButton("💰 Amount (USDT)", callback_data="set_amount")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")],
    ])

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    get_user(uid)
    await update.message.reply_text(
        "🤖 *Binance P2P Bot*\n\n"
        "P2P orders monitor လုပ်ပြီး\n"
        "market ထက် နှိမ့်တဲ့ order တွေ alert ပေးတယ်။",
        parse_mode="Markdown",
        reply_markup=main_kb()
    )

async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    u = get_user(uid)
    d = q.data

    if d == "back":
        u["waiting"] = None
        await q.edit_message_text(
            "🤖 *P2P Bot*\nMenu ရွေးပါ:",
            parse_mode="Markdown", reply_markup=main_kb()
        )

    elif d == "settings":
        txt = (
            f"⚙️ *Settings*\n\n"
            f"🪙 Coin: `{u['coin']}`\n"
            f"💰 Amount: `{u['amount']} USDT`\n"
            f"💵 Range: `{u['min_price']:,} - {u['max_price']:,} MMK`\n"
        )
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=settings_kb())

    elif d == "status":
        status = "🟢 Running" if u["running"] else "🔴 Stopped"
        await q.edit_message_text(
            f"📊 *Status*\n\nStatus: {status}\nAlerts: `{u['trades']}`",
            parse_mode="Markdown", reply_markup=main_kb()
        )

    elif d == "price":
        price = get_market_price(u["coin"], u["fiat"])
        await q.edit_message_text(
            f"📈 *{u['coin']}/MMK*\n\n`{price:,.0f} MMK`",
            parse_mode="Markdown", reply_markup=main_kb()
        )

    elif d == "start_bot":
        u["running"] = True
        await q.edit_message_text(
            "✅ *Bot Started!*\nMonitor လုပ်နေပြီ...",
            parse_mode="Markdown", reply_markup=main_kb()
        )
        asyncio.create_task(monitor(ctx, uid))

    elif d == "stop_bot":
        u["running"] = False
        await q.edit_message_text(
            "⏹ *Bot Stopped.*",
            parse_mode="Markdown", reply_markup=main_kb()
        )

    elif d == "set_coin":
        u["waiting"] = "coin"
        await q.edit_message_text("🪙 Coin ထည့်ပါ (USDT / BTC / ETH):")

    elif d == "set_min":
        u["waiting"] = "min"
        await q.edit_message_text("💵 Min Price (MMK) ထည့်ပါ:")

    elif d == "set_max":
        u["waiting"] = "max"
        await q.edit_message_text("💵 Max Price (MMK) ထည့်ပါ:")

    elif d == "set_amount":
        u["waiting"] = "amount"
        await q.edit_message_text("💰 Amount (USDT) ထည့်ပါ:")

async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u = get_user(uid)
    txt = update.message.text.strip()
    w = u.get("waiting")

    if w == "coin":
        u["coin"] = txt.upper()
        u["waiting"] = None
        await update.message.reply_text(f"✅ Coin: {u['coin']}", reply_markup=main_kb())

    elif w == "min":
        try:
            u["min_price"] = float(txt)
            u["waiting"] = None
            await update.message.reply_text(
                f"✅ Min: {u['min_price']:,.0f} MMK", reply_markup=main_kb())
        except:
            await update.message.reply_text("❌ ဂဏန်းသာ ထည့်ပါ!")

    elif w == "max":
        try:
            u["max_price"] = float(txt)
            u["waiting"] = None
            await update.message.reply_text(
                f"✅ Max: {u['max_price']:,.0f} MMK", reply_markup=main_kb())
        except:
            await update.message.reply_text("❌ ဂဏန်းသာ ထည့်ပါ!")

    elif w == "amount":
        try:
            u["amount"] = float(txt)
            u["waiting"] = None
            await update.message.reply_text(
                f"✅ Amount: {u['amount']} USDT", reply_markup=main_kb())
        except:
            await update.message.reply_text("❌ ဂဏန်းသာ ထည့်ပါ!")

    else:
        await update.message.reply_text("Menu ကနေ ရွေးပါ:", reply_markup=main_kb())

async def monitor(ctx: ContextTypes.DEFAULT_TYPE, uid: int):
    u = get_user(uid)
    alerted = set()
    while u.get("running"):
        try:
            market = get_market_price(u["coin"], u["fiat"])
            if market == 0:
                await asyncio.sleep(60)
                continue
            orders = fetch_p2p(u["coin"], u["fiat"], 20)
            for order in orders:
                adv = order.get("adv", {})
                price = float(adv.get("price", 0))
                min_amt = float(adv.get("minSingleTransAmount", 0))
                max_amt = float(adv.get("maxSingleTransAmount", 0))
                adv_no = adv.get("advNo", "")
                nick = order.get("advertiser", {}).get("nickName", "?")
                if adv_no in alerted:
                    continue
                if (price < market * 0.998 and
                        u["min_price"] <= price <= u["max_price"] and
                        min_amt <= u["amount"] <= max_amt):
                    diff = ((market - price) / market) * 100
                    msg = (
                        f"🚨 *Low Price Order!*\n\n"
                        f"👤 `{nick}`\n"
                        f"💵 Price: `{price:,.0f} MMK`\n"
                        f"📈 Market: `{market:,.0f} MMK`\n"
                        f"📉 Below: `{diff:.2f}%`\n"
                        f"💰 `{min_amt:.0f} - {max_amt:.0f} USDT`\n"
                        f"⏰ `{datetime.now().strftime('%H:%M:%S')}`"
                    )
                    await ctx.bot.send_message(uid, msg, parse_mode="Markdown")
                    alerted.add(adv_no)
                    u["trades"] += 1
                    if len(alerted) > 100:
                        alerted.clear()
        except Exception as e:
            logger.error(f"Monitor error: {e}")
        await asyncio.sleep(30)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    logger.info("Bot running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
