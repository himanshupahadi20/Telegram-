# Telegram Wallet Bot with Signup Bonus, UPI QR Payment, Withdraw System, Admin Panel
# Safe version: No real-money gambling, only QR-based deposit, with full admin control

import json
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# === CONFIG ===
BOT_TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 123456789  # Replace with your Telegram numeric user ID
QR_IMAGE_PATH = "qr.png"  # QR image file path
BONUS_AMOUNT = 51
DATA_FILE = "users.json"

# === Data Handling ===
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {"users": {}, "withdraw_requests": {}, "banned_users": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# === Commands ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id in data["banned_users"]:
        await update.message.reply_text("🚫 Aapka access restricted hai. Contact admin.")
        return

    if user_id not in data["users"]:
        button = KeyboardButton("📱 Share Phone Number", request_contact=True)
        markup = ReplyKeyboardMarkup([[button]], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Please verify your phone number to continue:", reply_markup=markup)
    else:
        await update.message.reply_text("✅ You're already registered! Use /balance or /withdraw.")

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    contact = update.message.contact.phone_number
    data = load_data()

    if user_id in data["users"]:
        await update.message.reply_text("You are already registered.")
        return

    data["users"][user_id] = {
        "name": user.full_name,
        "phone": contact,
        "balance": BONUS_AMOUNT
    }
    save_data(data)

    await update.message.reply_text(f"🎁 ₹{BONUS_AMOUNT} signup bonus added to your wallet.")

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🆕 New user registered!\n👤 {user.full_name}\n📱 {contact}\n🆔 ID: {user_id}"
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id in data["banned_users"]:
        await update.message.reply_text("🚫 Aapka access restricted hai.")
        return

    bal = data["users"].get(user_id, {}).get("balance", 0)
    await update.message.reply_text(f"💰 Your wallet balance is ₹{bal}")

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id in data["banned_users"]:
        await update.message.reply_text("🚫 Aapka access restricted hai.")
        return

    await update.message.reply_photo(photo=InputFile(QR_IMAGE_PATH), caption="📲 Scan this QR to deposit. Send screenshot after payment.")

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id in data["banned_users"]:
        await update.message.reply_text("🚫 Aapka access restricted hai.")
        return

    try:
        amount = int(context.args[0])
    except:
        await update.message.reply_text("❌ Usage: /withdraw <amount>")
        return

    if user_id not in data["users"]:
        await update.message.reply_text("❌ Please register first using /start")
        return

    if data["users"][user_id]["balance"] < amount:
        await update.message.reply_text("❌ Not enough balance.")
        return

    data["withdraw_requests"][user_id] = amount
    save_data(data)

    await update.message.reply_text(f"✅ Withdrawal request for ₹{amount} submitted. Admin will review.")
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"💸 Withdraw request:\n👤 {data['users'][user_id]['name']}\nAmount: ₹{amount}\nUser ID: {user_id}"
    )

# === Admin Commands ===
async def requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    data = load_data()
    if not data["withdraw_requests"]:
        await update.message.reply_text("📭 No pending withdrawal requests.")
        return

    msg = "📤 Pending Withdrawals:\n"
    for uid, amt in data["withdraw_requests"].items():
        name = data["users"].get(uid, {}).get("name", "Unknown")
        msg += f"👤 {name} (ID: {uid}) → ₹{amt}\n"
    await update.message.reply_text(msg)

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        uid, amt = context.args[0], int(context.args[1])
    except:
        await update.message.reply_text("Usage: /approve <user_id> <amount>")
        return

    data = load_data()
    if uid in data["users"] and uid in data["withdraw_requests"]:
        if data["users"][uid]["balance"] >= amt:
            data["users"][uid]["balance"] -= amt
            del data["withdraw_requests"][uid]
            save_data(data)
            await update.message.reply_text("✅ Approved.")
            await context.bot.send_message(chat_id=uid, text=f"🎉 Your ₹{amt} withdrawal has been approved.")
        else:
            await update.message.reply_text("❌ Insufficient balance.")

async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        uid = context.args[0]
    except:
        await update.message.reply_text("Usage: /reject <user_id>")
        return

    data = load_data()
    if uid in data["withdraw_requests"]:
        del data["withdraw_requests"][uid]
        save_data(data)
        await update.message.reply_text("❌ Rejected.")
        await context.bot.send_message(chat_id=uid, text="🚫 Your withdrawal request was rejected by admin.")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        uid = context.args[0]
    except:
        await update.message.reply_text("Usage: /ban <user_id>")
        return

    data = load_data()
    if uid not in data["banned_users"]:
        data["banned_users"].append(uid)
        save_data(data)
        await update.message.reply_text("🚫 User banned.")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        uid = context.args[0]
    except:
        await update.message.reply_text("Usage: /unban <user_id>")
        return

    data = load_data()
    if uid in data["banned_users"]:
        data["banned_users"].remove(uid)
        save_data(data)
        await update.message.reply_text("✅ User unbanned.")

# === App Init ===
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("balance", balance))
app.add_handler(CommandHandler("pay", pay))
app.add_handler(CommandHandler("withdraw", withdraw))
app.add_handler(CommandHandler("requests", requests))
app.add_handler(CommandHandler("approve", approve))
app.add_handler(CommandHandler("reject", reject))
app.add_handler(CommandHandler("ban", ban))
app.add_handler(CommandHandler("unban", unban))
app.add_handler(MessageHandler(filters.CONTACT, contact_handler))

app.run_polling()
