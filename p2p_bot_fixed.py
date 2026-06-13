import os
import asyncioimportt asyncio
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "7576496100:AAFezDOM1HRbiXkQx5_GA501kbOGJeLgJds"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# User storage
users = {}

def get_user(uid):
    if uid not in users:
        users[uid] = {
            "api_key": "",
            "secret_key": "",
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

# ==================== P2P API ====================

def fetch_p2p(coin="USDT", fiat="MMK", side="BUY", rows=20):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    data = {
        "asset": coin, "fiat": fiat,
        "merchantCheck": False, "page": 1,
        "payTypes": [], "rows": rows, "tradeType": side,
    }
    try:
        r = requests.post(url, json=data, headers={"Content-Type": "application/json"}, timeout=10)
        return r.json().get("data", [])
    except Exception as e:
        logger.error(f"P2P error: {e}")
        return []

def get_market_price(coin="USDT", fiat="MMK"):
    orders = fetch_p2p(coin, fiat, "BUY", 5)
    if orders:
        prices = [float(o["adv"]["price"]) for o in orders]
        return round(sum(prices) / len(prices), 2)
    return 0

# ==================== KEYBOARDS ====================

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
        [InlineKeyboardButton("🔑 API Key", callback_data="set_api")],
        [InlineKeyboardButton("🔐 Secret Key", callback_data="set_secret")],
        [InlineKeyboardButton("🪙 Coin", callback_data="set_coin")],
        [InlineKeyboardButton("💵 Min Price", callback_data="set_min")],
        [InlineKeyboardButton("💵 Max Price", callback_data="set_max")],
        [InlineKeyboardButton("💰 Amount (USDT)", callback_data="set_amount")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")],
    ])

# ==================== COMMANDS ====================

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    get_user(uid)
    await update.message.reply_text(
        "🤖 *Binance P2P Bot*\n\n"
        "P2P orders ကို auto monitor လုပ်ပြီး\n"
        "market ထက် နှိမ့်တဲ့ order တွေ alert ပေးတယ်။\n\n"
        "⚠️ Settings မှာ API Key ထည့်ပါ။",
        parse_mode="Markdown",
        reply_markup=main_kb()
    )

# ==================== CALLBACKS ====================

async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    u = get_user(uid)
    d = q.data

    if d == "back":
        u["waiting"] = None
        await q.edit_message_text(
            "🤖 *Binance P2P Bot*\nMenu ရွေးပါ:",
            parse_mode="Markdown", reply_markup=main_kb()
        )

    elif d == "settings":
        api_status = "✅ Set" if u["api_key"] else "❌ Not set"
        txt = (
            f"⚙️ *Settings*\n\n"
            f"🔑 API Key: {api_status}\n"
            f"🪙 Coin: `{u['coin']}`\n"
            f"💰 Amount: `{u['amount']} USDT`\n"
            f"💵 Price Range: `{u['min_price']:,} - {u['max_price']:,} MMK`\n"
        )
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=settings_kb())

    elif d == "status":
        status = "🟢 Running" if u["running"] else "🔴 Stopped"
        txt = (
            f"📊 *Bot Status*\n\n"
            f"Status: {status}\n"
            f"Alerts sent: `{u['trades']}`\n"
            f"Coin: `{u['coin']}/MMK`\n"
        )
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=main_kb())

    elif d == "price":
        price = get_market_price(u["coin"])
        await q.edit_message_text(
            f"📈 *{u['coin']}/MMK Market Price*\n\n`{price:,.0f} MMK`",
            parse_mode="Markdown", reply_markup=main_kb()
        )

    elif d == "start_bot":
        if not u["api_key"]:
            await q.edit_message_text(
                "❌ API Key မထည့်ရသေးပါ!\nSettings → API Key",
                reply_markup=main_kb()
            )
            return
        u["running"] = True
        await q.edit_message_text(
            "✅ *Bot Started!*\n\nP2P orders monitor လုပ်နေပြီ...\n"
            "Market ထက် ၀.၂% နှိမ့်တဲ့ order တွေ alert ပေးမယ်။",
            parse_mode="Markdown", reply_markup=main_kb()
        )
        asyncio.create_task(monitor(ctx, uid))

    elif d == "stop_bot":
        u["running"] = False
        await q.edit_message_text("⏹ *Bot Stopped.*", parse_mode="Markdown", reply_markup=main_kb())

    elif d == "set_api":
        u["waiting"] = "api"
        await q.edit_message_text("🔑 Binance API Key ထည့်ပါ:")

    elif d == "set_secret":
        u["waiting"] = "secret"
        await q.edit_message_text("🔐 Binance Secret Key ထည့်ပါ:")

    elif d == "set_coin":
        u["waiting"] = "coin"
        await q.edit_message_text("🪙 Coin ထည့်ပါ (USDT / BTC / ETH / BNB):")

    elif d == "set_min":
        u["waiting"] = "min"
        await q.edit_message_text("💵 Minimum Price (MMK) ထည့်ပါ:")

    elif d == "set_max":
        u["waiting"] = "max"
        await q.edit_message_text("💵 Maximum Price (MMK) ထည့်ပါ:")

    elif d == "set_amount":
        u["waiting"] = "amount"
        await q.edit_message_text("💰 Buy Amount (USDT) ထည့်ပါ:")

# ==================== TEXT HANDLER ====================

async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u = get_user(uid)
    txt = update.message.text.strip()
    w = u.get("waiting")

    if w == "api":
        u["api_key"] = txt
        u["waiting"] = None
        await update.message.reply_text("✅ API Key သိမ်းပြီ!", reply_markup=main_kb())

    elif w == "secret":
        u["secret_key"] = txt
        u["waiting"] = None
        await update.message.reply_text("✅ Secret Key သိမ်းပြီ!", reply_markup=main_kb())

    elif w == "coin":
        u["coin"] = txt.upper()
        u["waiting"] = None
        await update.message.reply_text(f"✅ Coin: {u['coin']}", reply_markup=main_kb())

    elif w == "min":
        try:
            u["min_price"] = float(txt)
            u["waiting"] = None
            await update.message.reply_text(f"✅ Min Price: {u['min_price']:,.0f} MMK", reply_markup=main_kb())
        except:
            await update.message.reply_text("❌ ဂဏန်းသာ ထည့်ပါ!")

    elif w == "max":
        try:
            u["max_price"] = float(txt)
            u["waiting"] = None
            await update.message.reply_text(f"✅ Max Price: {u['max_price']:,.0f} MMK", reply_markup=main_kb())
        except:
            await update.message.reply_text("❌ ဂဏန်းသာ ထည့်ပါ!")

    elif w == "amount":
        try:
            u["amount"] = float(txt)
            u["waiting"] = None
            await update.message.reply_text(f"✅ Amount: {u['amount']} USDT", reply_markup=main_kb())
        except:
            await update.message.reply_text("❌ ဂဏန်းသာ ထည့်ပါ!")

    else:
        await update.message.reply_text("Menu ကနေ ရွေးပါ:", reply_markup=main_kb())

# ==================== MONITOR ====================

async def monitor(ctx: ContextTypes.DEFAULT_TYPE, uid: int):
    u = get_user(uid)
    logger.info(f"Monitor started for {uid}")
    alerted = set()

    while u.get("running"):
        try:
            market = get_market_price(u["coin"])
            if market == 0:
                await asyncio.sleep(60)
                continue

            orders = fetch_p2p(u["coin"], u["fiat"], "BUY", 20)
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
                        f"🚨 *Low Price P2P Order!*\n\n"
                        f"👤 Seller: `{nick}`\n"
                        f"💵 Price: `{price:,.0f} MMK`\n"
                        f"📈 Market: `{market:,.0f} MMK`\n"
                        f"📉 Below market: `{diff:.2f}%`\n"
                        f"💰 Range: `{min_amt:.0f} - {max_amt:.0f} USDT`\n"
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

    logger.info(f"Monitor stopped for {uid}")

# ==================== MAIN ====================

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    logger.info("Bot running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
