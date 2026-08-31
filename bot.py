import os
import sqlite3
import secrets
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from dotenv import load_dotenv

# =========================================================
# CONFIG
# =========================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing in environment variables")

# =========================================================
# DATABASE
# =========================================================

DB = "bank.db"


def db():
    return sqlite3.connect(DB)


def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            account_no TEXT UNIQUE,
            balance REAL DEFAULT 0,
            pin TEXT,
            frozen INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount REAL,
            description TEXT,
            txid TEXT UNIQUE,
            created_at TEXT
        )
    """)

    con.commit()
    con.close()


# =========================================================
# HELPERS
# =========================================================

def generate_account():
    while True:
        number = "10" + "".join(
            secrets.choice("0123456789") for _ in range(8)
        )

        con = db()
        cur = con.cursor()

        cur.execute(
            "SELECT account_no FROM users WHERE account_no=?",
            (number,)
        )

        exists = cur.fetchone()
        con.close()

        if not exists:
            return number


def generate_txid():
    return "TX" + secrets.token_hex(6).upper()


def get_user(user_id):
    con = db()
    cur = con.cursor()

    cur.execute(
        "SELECT * FROM users WHERE user_id=?",
        (user_id,)
    )

    user = cur.fetchone()
    con.close()

    return user


def create_user(message):
    user_id = message.from_user.id

    if get_user(user_id):
        return

    account_no = generate_account()

    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO users
        (user_id, username, first_name, account_no, balance, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        message.from_user.username or "",
        message.from_user.first_name or "",
        account_no,
        0,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    con.commit()
    con.close()


def add_transaction(user_id, tx_type, amount, description):
    txid = generate_txid()

    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO transactions
        (user_id, type, amount, description, txid, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        tx_type,
        amount,
        description,
        txid,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    con.commit()
    con.close()

    return txid


# =========================================================
# KEYBOARD
# =========================================================

def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Balance",
                    callback_data="balance"
                ),
                InlineKeyboardButton(
                    text="👤 Profile",
                    callback_data="profile"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧾 Transactions",
                    callback_data="transactions"
                )
            ]
        ]
    )


# =========================================================
# BOT
# =========================================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start(message: Message):

    create_user(message)

    user = get_user(message.from_user.id)

    if user[6] == 1:
        await message.answer(
            "🚫 Your account is frozen."
        )
        return

    await message.answer(
        f"🏦 <b>Welcome to MyBank</b>\n\n"
        f"Hello {message.from_user.first_name} 👋\n\n"
        f"🔢 Account: <code>{user[3]}</code>\n"
        f"💰 Balance: ₹{user[4]:.2f}\n\n"
        f"Choose an option:",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


# =========================================================
# BALANCE
# =========================================================

@dp.callback_query(F.data == "balance")
async def balance(callback: CallbackQuery):

    user = get_user(callback.from_user.id)

    if not user:
        await callback.answer("Please use /start first.")
        return

    await callback.message.edit_text(
        f"💰 <b>Your Balance</b>\n\n"
        f"₹{user[4]:.2f}",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# PROFILE
# =========================================================

@dp.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):

    user = get_user(callback.from_user.id)

    if not user:
        await callback.answer("Please use /start first.")
        return

    status = "🔴 Frozen" if user[6] else "🟢 Active"

    await callback.message.edit_text(
        f"👤 <b>My Profile</b>\n\n"
        f"Name: {user[2]}\n"
        f"Username: @{user[1] if user[1] else 'None'}\n"
        f"User ID: <code>{user[0]}</code>\n"
        f"Account: <code>{user[3]}</code>\n"
        f"Balance: ₹{user[4]:.2f}\n"
        f"Status: {status}\n"
        f"Created: {user[7]}",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# TRANSACTIONS
# =========================================================

@dp.callback_query(F.data == "transactions")
async def transactions(callback: CallbackQuery):

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT type, amount, description, txid, created_at
        FROM transactions
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 10
    """, (callback.from_user.id,))

    rows = cur.fetchall()
    con.close()

    if not rows:
        text = "🧾 <b>Transactions</b>\n\nNo transactions yet."
    else:
        text = "🧾 <b>Last Transactions</b>\n\n"

        for row in rows:
            text += (
                f"• {row[0]}\n"
                f"  Amount: ₹{row[1]:.2f}\n"
                f"  {row[2]}\n"
                f"  ID: <code>{row[3]}</code>\n"
                f"  {row[4]}\n\n"
            )

    await callback.message.edit_text(
        text,
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# ADMIN
# =========================================================

@dp.message(Command("admin"))
async def admin(message: Message):

    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Access denied.")
        return

    con = db()
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    cur.execute("SELECT SUM(balance) FROM users")
    total_balance = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM transactions")
    transactions_count = cur.fetchone()[0]

    con.close()

    await message.answer(
        f"👑 <b>Admin Panel</b>\n\n"
        f"👥 Users: {users}\n"
        f"💰 Total Balance: ₹{total_balance:.2f}\n"
        f"🧾 Transactions: {transactions_count}",
        parse_mode="HTML"
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    init_db()

    print("🏦 MyBank Bot Started")

    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
