import logging
import os
import requests
import hmac
import hashlib
import time
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

ALL_PAY_METHODS = [
    "AYA Pay",
    "Bank Transfer",
    "CB Pay",
    "Cash Deposit to Bank",
    "KBZPay",
    "WavePay",
    "Wave Money",
    "Wave Mobile Money",
    "uabpay",
    "Yoma Bank",
    "Spring Development Bank",
    "Transfers with specific bank",
    "Airtime Mobile Top-Up",
]

subscriptions = {}
order_history = []

settings = {
    "bot_name": "Lucky Money",
    "fiat": "MMK",
    "coin": "USDT",
    "max_amount": 15000000,
    "min_amount": 180000,
    "target_value": 3100,
    "max_orders": 1,
    "take_full_bank": False,
    "pay_methods": list(ALL_PAY_METHODS),
    "running": False,
    "api_key": "",
    "secret_key": ""
}

logging.basicConfig(level=logging.INFO)
user_states = {}

PAY_METHOD_SHORT = {
    "AYA Pay": "AYAPay",
    "Bank Transfer": "BANK",
    "CB Pay": "CBPay",
    "Cash Deposit to Bank": "CashDeposit",
    "KBZPay": "KBZPay1",
    "WavePay": "WavePay1",
    "Wave Money": "WaveMoney",
    "Wave Mobile Money": "WaveMobile",
    "uabpay": "uabpay",
    "Yoma Bank": "YomaBank",
    "Spring Development Bank": "SpringBank",
    "Transfers with specific bank": "SpecificBank",
    "Airtime Mobile Top-Up": "Airtime",
}

def is_subscribed(user_id):
    if user_id == ADMIN_ID:
        return True
    if user_id in subscriptions:
        if subscriptions[user_id]["expiry"] > datetime.now():
            return True
    return False

def get_expiry(user_id):
    if user_id == ADMIN_ID:
        return "Admin (Unlimited)"
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
            return data
    except Exception as e:
        logging.error(f"Error: {e}")
    return []

def binance_request(method, endpoint, params={}, api_key="", secret=""):
    params["timestamp"] = int(time.time() * 1000)
    query = "&".join([f"{k}={v}" for k, v in params.items()])
    sig = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    url = f"https://api.binance.com{endpoint}?{query}&signature={sig}"
    headers = {"X-MBX-APIKEY": api_key}
    if method == "GET":
        return requests.get(url, headers=headers).json()
    elif method == "POST":
        return requests.post(url, headers=headers).json()

async def place_buy_order(context, chat_id):
    if not settings["running"]:
        return
    if not settings["api_key"] or not settings["secret_key"]:
        await context.bot.send_message(chat_id=chat_id, text="API Key not set!")
        return

    orders = get_best_price("BUY")
    if not orders:
        await context.bot.send_message(chat_id=chat_id, text="No P2P orders found!")
        return

    placed = 0
    for best in orders[:settings["max_orders"]]:
        price = float(best["adv"]["price"])
        adv_id = best["adv"]["advNo"]
        min_amt = float(best["adv"]["minSingleTransAmount"])
        max_amt = float(best["adv"]["maxSingleTransAmount"])

        if price > settings["target_value"]:
            msg = (
                "UNSUCCESS\n\n"
                f"Rate: {price} {settings['fiat']}\n"
                f"Target: {settings['target_value']}\n"
                f"Diff: {price - settings['target_value']}\n"
                f"Time: {datetime.now().strftime('%H:%M:%S')}"
            )
            order_history.append({"status": "UNSUCCESS", "price": price, "time": datetime.now()})
            await context.bot.send_message(chat_id=chat_id, text=msg)
            continue

        trade_amount = min(settings["max_amount"], max_amt)
        trade_amount = max(settings["min_amount"], min_amt)

        try:
            result = binance_request(
                "POST",
                "/sapi/v1/c2c/orderMatch/placeOrder",
                {
                    "advNo": adv_id,
                    "tradeType": "BUY",
                    "fiatAmount": trade_amount,
                },
                settings["api_key"],
                settings["secret_key"]
            )

            if result.get("code") == "000000":
                msg = (
                    "SUCCESS!\n\n"
                    f"Rate: {price} {settings['fiat']}\n"
                    f"Amount: {trade_amount} {settings['fiat']}\n"
                    f"Order ID: {result.get('data', {}).get('orderNumber', 'N/A')}\n"
                    f"Time: {datetime.now().strftime('%H:%M:%S')}"
                )
                order_history.append({"status": "SUCCESS", "price": price, "amount": trade_amount, "time": datetime.now()})
                placed += 1
            else:
                msg = (
                    "UNSUCCESS\n\n"
                    f"Rate: {price} {settings['fiat']}\n"
                    f"Error: {result.get('message', 'Unknown error')}\n"
                    f"Time: {datetime.now().strftime('%H:%M:%S')}"
                )
                order_history.append({"status": "UNSUCCESS", "price": price, "time": datetime.now()})

            await context.bot.send_message(chat_id=chat_id, text=msg)

        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"Error: {e}")

    if placed >= settings["max_orders"]:
        settings["running"] = False


def pay_methods_keyboard(page=0):
    per_page = 5
    start = page * per_page
    end = start + per_page
    page_methods = ALL_PAY_METHODS[start:end]

    keyboard = []
    for m in page_methods:
        short = PAY_METHOD_SHORT.get(m, m)
        tick = "✅ " if m in settings["pay_methods"] else ""
        keyboard.append([InlineKeyboardButton(f"{tick}{short}", callback_data=f"pm_{m}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Back", callback_data=f"pm_page_{page-1}"))
    if end < len(ALL_PAY_METHODS):
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"pm_page_{page+1}"))
    if nav:
        keyboard.append(nav)

    keyboard.append([
        InlineKeyboardButton("✅ All", callback_data="pm_all"),
        InlineKeyboardButton("❌ Clear", callback_data="pm_clear"),
    ])
    keyboard.append([InlineKeyboardButton("✔️ Done", callback_data="settings")])
    return keyboard


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_subscribed(user_id):
        text = "Choose Your Plan!\n\nSelect the plan that fits your needs:"
        keyboard = [
            [InlineKeyboardButton("1 month - 150$", callback_data="buy_1month")],
            [InlineKeyboardButton("3 months - 400$", callback_data="buy_3months")],
        ]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    status = "Running" if settings["running"] else "Stopped"
    text = (
        f"Welcome to the {settings['bot_name']} Menu!\n\n"
        f"Status: {status}\n\n"
        f"Select an option to continue!"
    )
    keyboard = [
        [InlineKeyboardButton("Start Bot" if not settings["running"] else "Stop Bot", callback_data="toggle")],
        [InlineKeyboardButton("Settings", callback_data="settings")],
        [InlineKeyboardButton("Statistics", callback_data="stats")],
        [InlineKeyboardButton("Order History", callback_data="history")]
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
            f"Payment Instructions\n\n"
            f"Plan: {plan['name']}\n"
            f"Price: ${plan['price']} USDT\n\n"
            f"Send ${plan['price']} USDT to:\n"
            f"{USDT_ADDRESS}\n\n"
            f"Network: {USDT_NETWORK}\n\n"
            f"After payment send screenshot or TXID."
        )
        user_states[chat_id] = f"waiting_payment_{plan_key}"
        keyboard = [[InlineKeyboardButton("Back", callback_data="back_to_plans")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "back_to_plans":
        text = "Choose Your Plan!\n\nSelect the plan that fits your needs:"
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
            await query.edit_message_text(f"Approved! User {target_user} - {plan['name']} until {expiry.strftime('%Y-%m-%d')}")
            try:
                await context.bot.send_message(
                    chat_id=target_user,
                    text=f"Subscription Approved!\n\nPlan: {plan['name']}\nExpiry: {expiry.strftime('%Y-%m-%d')}\n\nSend /start to begin!"
                )
            except:
                pass

    elif query.data.startswith("reject_"):
        if user_id == ADMIN_ID:
            parts = query.data.split("_")
            target_user = int(parts[1])
            await query.edit_message_text(f"Rejected user {target_user}")
            try:
                await context.bot.send_message(
                    chat_id=target_user,
                    text="Payment not confirmed. Please contact admin or try again."
                )
            except:
                pass

    elif query.data == "toggle":
        if not is_subscribed(user_id):
            await query.answer("Please subscribe first!", show_alert=True)
            return
        settings["running"] = not settings["running"]
        if settings["running"]:
            await query.edit_message_text("Bot Started! Scanning P2P orders...")
            await place_buy_order(context, chat_id)
        else:
            keyboard = [[InlineKeyboardButton("Back", callback_data="back")]]
            await query.edit_message_text("Bot Stopped!", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "settings":
        if not is_subscribed(user_id):
            await query.answer("Please subscribe first!", show_alert=True)
            return
        text = "Settings Menu:"
        keyboard = [
            [InlineKeyboardButton(f"Bot name [{settings['bot_name']}]", callback_data="set_botname")],
            [InlineKeyboardButton(f"Fiat [{settings['fiat']}]", callback_data="set_fiat")],
            [InlineKeyboardButton(f"Pay Methods [{len(settings['pay_methods'])}]", callback_data="set_pay_methods")],
            [InlineKeyboardButton(f"Coin [{settings['coin']}]", callback_data="set_coin")],
            [InlineKeyboardButton(f"Max amount [{settings['max_amount']}]", callback_data="set_max")],
            [InlineKeyboardButton(f"Min amount [{settings['min_amount']}]", callback_data="set_min")],
            [InlineKeyboardButton(f"Target price [Less {settings['target_value']}]", callback_data="set_target")],
            [InlineKeyboardButton(f"Max orders [{settings['max_orders']}]", callback_data="set_max_orders")],
            [InlineKeyboardButton(f"Full bank [{'On' if settings['take_full_bank'] else 'Off'}]", callback_data="toggle_bank")],
            [InlineKeyboardButton("API Key", callback_data="api_key_menu")],
            [InlineKeyboardButton("Back", callback_data="back")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "set_pay_methods":
        text = f"Pay Methods ({len(settings['pay_methods'])}/{len(ALL_PAY_METHODS)} selected)\nTap to toggle:"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(pay_methods_keyboard(0)))

    elif query.data.startswith("pm_page_"):
        page = int(query.data.replace("pm_page_", ""))
        text = f"Pay Methods ({len(settings['pay_methods'])}/{len(ALL_PAY_METHODS)} selected)\nTap to toggle:"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(pay_methods_keyboard(page)))

    elif query.data == "pm_all":
        settings["pay_methods"] = list(ALL_PAY_METHODS)
        text = f"Pay Methods ({len(settings['pay_methods'])}/{len(ALL_PAY_METHODS)} selected)\nTap to toggle:"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(pay_methods_keyboard(0)))

    elif query.data == "pm_clear":
        settings["pay_methods"] = []
        text = f"Pay Methods (0/{len(ALL_PAY_METHODS)} selected)\nTap to toggle:"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(pay_methods_keyboard(0)))

    elif query.data.startswith("pm_"):
        method = query.data[3:]
        if method in settings["pay_methods"]:
            settings["pay_methods"].remove(method)
        else:
            settings["pay_methods"].append(method)
        text = f"Pay Methods ({len(settings['pay_methods'])}/{len(ALL_PAY_METHODS)} selected)\nTap to toggle:"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(pay_methods_keyboard(0)))

    elif query.data == "history":
        if not order_history:
            text = "Order History\n\nNo orders yet."
        else:
            text = "Order History (Last 10)\n\n"
            for order in order_history[-10:]:
                emoji = "SUCCESS" if order["status"] == "SUCCESS" else "UNSUCCESS"
                text += f"{emoji}\n"
                text += f"Rate: {order['price']} {settings['fiat']}\n"
                text += f"Time: {order['time'].strftime('%H:%M:%S')}\n\n"
        keyboard = [[InlineKeyboardButton("Back", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "set_botname":
        user_states[chat_id] = "waiting_botname"
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="settings")]]
        await query.edit_message_text("Enter new Bot Name:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "set_fiat":
        text = "Select Fiat Currency:"
        keyboard = [
            [InlineKeyboardButton("MMK", callback_data="fiat_MMK")],
            [InlineKeyboardButton("THB", callback_data="fiat_THB")],
            [InlineKeyboardButton("USD", callback_data="fiat_USD")],
            [InlineKeyboardButton("SGD", callback_data="fiat_SGD")],
            [InlineKeyboardButton("MYR", callback_data="fiat_MYR")],
            [InlineKeyboardButton("Custom", callback_data="fiat_custom")],
            [InlineKeyboardButton("Back", callback_data="settings")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("fiat_"):
        fiat = query.data.replace("fiat_", "")
        if fiat == "custom":
            user_states[chat_id] = "waiting_fiat"
            keyboard = [[InlineKeyboardButton("Cancel", callback_data="set_fiat")]]
            await query.edit_message_text("Enter Fiat code: (MMK, THB, USD)", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            settings["fiat"] = fiat
            keyboard = [[InlineKeyboardButton("Back", callback_data="settings")]]
            await query.edit_message_text(f"Fiat changed to: {fiat}", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "set_coin":
        text = "Select Coin:"
        keyboard = [
            [InlineKeyboardButton("USDT", callback_data="coin_USDT")],
            [InlineKeyboardButton("BTC", callback_data="coin_BTC")],
            [InlineKeyboardButton("ETH", callback_data="coin_ETH")],
            [InlineKeyboardButton("BNB", callback_data="coin_BNB")],
            [InlineKeyboardButton("Custom", callback_data="coin_custom")],
            [InlineKeyboardButton("Back", callback_data="settings")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("coin_"):
        coin = query.data.replace("coin_", "")
        if coin == "custom":
            user_states[chat_id] = "waiting_coin"
            keyboard = [[InlineKeyboardButton("Cancel", callback_data="set_coin")]]
            await query.edit_message_text("Enter Coin name: (USDT, BTC, ETH)", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            settings["coin"] = coin
            keyboard = [[InlineKeyboardButton("Back", callback_data="settings")]]
            await query.edit_message_text(f"Coin changed to: {coin}", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "set_max":
        user_states[chat_id] = "waiting_max"
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="settings")]]
        await query.edit_message_text(f"Enter Max Amount:\nCurrent: {settings['max_amount']}", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "set_min":
        user_states[chat_id] = "waiting_min"
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="settings")]]
        await query.edit_message_text(f"Enter Min Amount:\nCurrent: {settings['min_amount']}", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "set_target":
        user_states[chat_id] = "waiting_target"
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="settings")]]
        await query.edit_message_text(
            f"Enter Target Price:\nCurrent: {settings['target_value']}\n\nBot will only buy if rate is LESS than this value.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "set_max_orders":
        user_states[chat_id] = "waiting_max_orders"
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="settings")]]
        await query.edit_message_text(
            f"Enter Max Orders:\nCurrent: {settings['max_orders']}\n\nBot will place this many orders per run.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "api_key_menu":
        api_status = "Set" if settings["api_key"] else "Not Set"
        secret_status = "Set" if settings["secret_key"] else "Not Set"
        text = f"API Key Menu\n\nAPI Key: {api_status}\nSecret Key: {secret_status}"
        keyboard = [
            [InlineKeyboardButton("Add API Key", callback_data="add_api")],
            [InlineKeyboardButton("Add Secret Key", callback_data="add_secret")],
            [InlineKeyboardButton("Back", callback_data="settings")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "add_api":
        user_states[chat_id] = "waiting_api_key"
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="api_key_menu")]]
        await query.edit_message_text("Enter Binance API Key:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "add_secret":
        user_states[chat_id] = "waiting_secret_key"
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="api_key_menu")]]
        await query.edit_message_text("Enter Binance Secret Key:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "stats":
        orders = get_best_price("BUY")
        best_buy = orders[0]["adv"]["price"] if orders else "N/A"
        total = len(order_history)
        success = len([o for o in order_history if o["status"] == "SUCCESS"])
        text = (
            f"Statistics\n\n"
            f"Best Buy: {best_buy} {settings['fiat']}\n"
            f"Target: {settings['target_value']}\n"
            f"Status: {'Running' if settings['running'] else 'Stopped'}\n"
            f"API Key: {'Set' if settings['api_key'] else 'Not Set'}\n"
            f"Total Orders: {total}\n"
            f"Success: {success}\n"
            f"Unsuccess: {total - success}\n"
            f"Subscription: {get_expiry(user_id)}"
        )
        keyboard = [[InlineKeyboardButton("Back", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "toggle_bank":
        settings["take_full_bank"] = not settings["take_full_bank"]

    elif query.data == "back":
        if not is_subscribed(user_id):
            text = "Choose Your Plan!"
            keyboard = [
                [InlineKeyboardButton("1 month - 150$", callback_data="buy_1month")],
                [InlineKeyboardButton("3 months - 400$", callback_data="buy_3months")],
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            return
        status = "Running" if settings["running"] else "Stopped"
        text = f"{settings['bot_name']} Menu\n\nStatus: {status}"
        keyboard = [
            [InlineKeyboardButton("Start Bot" if not settings["running"] else "Stop Bot", callback_data="toggle")],
            [InlineKeyboardButton("Settings", callback_data="settings")],
            [InlineKeyboardButton("Statistics", callback_data="stats")],
            [InlineKeyboardButton("Order History", callback_data="history")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if update.message.photo:
        if chat_id in user_states and user_states[chat_id].startswith("waiting_payment_"):
            plan_key = user_states[chat_id].replace("waiting_payment_", "")
            plan = SUBSCRIPTION_PLANS[plan_key]
            await update.message.reply_text(f"Payment screenshot received!\nWaiting for admin approval...\nPlan: {plan['name']} - ${plan['price']}")
            keyboard = [
                [InlineKeyboardButton(f"Approve {plan['name']}", callback_data=f"approve_{user_id}_{plan_key}")],
                [InlineKeyboardButton("Reject", callback_data=f"reject_{user_id}_{plan_key}")]
            ]
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"New Payment!\n\nUser: {user_id}\n@{update.message.from_user.username or 'N/A'}\nPlan: {plan['name']} - ${plan['price']} USDT",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            user_states.pop(chat_id)
        return

    if chat_id not in user_states:
        return

    text = update.message.text
    state = user_states[chat_id]

    if state.startswith("waiting_payment_"):
        plan_key = state.replace("waiting_payment_", "")
        plan = SUBSCRIPTION_PLANS[plan_key]
        await update.message.reply_text(f"Payment proof received!\nWaiting for admin approval...")
        keyboard = [
            [InlineKeyboardButton(f"Approve {plan['name']}", callback_data=f"approve_{user_id}_{plan_key}")],
            [InlineKeyboardButton("Reject", callback_data=f"reject_{user_id}_{plan_key}")]
        ]
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"New Payment!\n\nUser: {user_id}\n@{update.message.from_user.username or 'N/A'}\nPlan: {plan['name']} - ${plan['price']} USDT",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        user_states.pop(chat_id)

    elif state == "waiting_botname":
        settings["bot_name"] = text
        user_states.pop(chat_id)
        keyboard = [[InlineKeyboardButton("Back", callback_data="settings")]]
        await update.message.reply_text(f"Bot name changed to: {text}", reply_markup=InlineKeyboardMarkup(keyboard))

    elif state == "waiting_fiat":
        settings["fiat"] = text.upper()
        user_states.pop(chat_id)
        keyboard = [[InlineKeyboardButton("Back", callback_data="settings")]]
        await update.message.reply_text(f"Fiat changed to: {text.upper()}", reply_markup=InlineKeyboardMarkup(keyboard))

    elif state == "waiting_coin":
        settings["coin"] = text.upper()
        user_states.pop(chat_id)
        keyboard = [[InlineKeyboardButton("Back", callback_data="settings")]]
        await update.message.reply_text(f"Coin changed to: {text.upper()}", reply_markup=InlineKeyboardMarkup(keyboard))

    elif state == "waiting_max":
        try:
            settings["max_amount"] = int(text)
            user_states.pop(chat_id)
            keyboard = [[InlineKeyboardButton("Back", callback_data="settings")]]
            await update.message.reply_text(f"Max amount: {text}", reply_markup=InlineKeyboardMarkup(keyboard))
        except ValueError:
            await update.message.reply_text("Numbers only!")

    elif state == "waiting_min":
        try:
            settings["min_amount"] = int(text)
            user_states.pop(chat_id)
            keyboard = [[InlineKeyboardButton("Back", callback_data="settings")]]
            await update.message.reply_text(f"Min amount: {text}", reply_markup=InlineKeyboardMarkup(keyboard))
        except ValueError:
            await update.message.reply_text("Numbers only!")

    elif state == "waiting_target":
        try:
            settings["target_value"] = int(text)
            user_states.pop(chat_id)
            keyboard = [[InlineKeyboardButton("Back", callback_data="settings")]]
            await update.message.reply_text(
                f"Target price set to: {text}\nBot will buy if rate < {text}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except ValueError:
            await update.message.reply_text("Numbers only!")

    elif state == "waiting_max_orders":
        try:
            val = int(text)
            if val < 1:
                await update.message.reply_text("Minimum is 1!")
                return
            settings["max_orders"] = val
            user_states.pop(chat_id)
            keyboard = [[InlineKeyboardButton("Back", callback_data="settings")]]
            await update.message.reply_text(
                f"Max orders set to: {val}\nBot will place up to {val} order(s) per run.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except ValueError:
            await update.message.reply_text("Numbers only!")

    elif state == "waiting_api_key":
        settings["api_key"] = text
        user_states.pop(chat_id)
        keyboard = [[InlineKeyboardButton("Back", callback_data="api_key_menu")]]
        await update.message.reply_text("API Key saved!", reply_markup=InlineKeyboardMarkup(keyboard))

    elif state == "waiting_secret_key":
        settings["secret_key"] = text
        user_states.pop(chat_id)
        keyboard = [[InlineKeyboardButton("Back", callback_data="api_key_menu")]]
        await update.message.reply_text("Secret Key saved!", reply_markup=InlineKeyboardMarkup(keyboard))


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
