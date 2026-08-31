import os
import sqlite3
import secrets
from datetime import datetime, date

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage


# =========================================================
# ENVIRONMENT
# =========================================================

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])


# =========================================================
# SETTINGS
# =========================================================

CURRENCY = "₹"

MAX_SEND = 5000
MAX_WITHDRAW = 5000

SEND_DAILY_LIMIT = 10000
WITHDRAW_DAILY_LIMIT = 10000

SEND_FEE_PERCENT = 0
WITHDRAW_FEE_PERCENT = 0

DB_NAME = "bank.db"


# =========================================================
# DATABASE
# =========================================================

def connect():
    return sqlite3.connect(DB_NAME)


def init_db():

    con = connect()
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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount REAL,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)

    con.commit()
    con.close()


# =========================================================
# HELPERS
# =========================================================

def get_user(user_id):

    con = connect()
    cur = con.cursor()

    cur.execute(
        "SELECT * FROM users WHERE user_id=?",
        (user_id,)
    )

    user = cur.fetchone()

    con.close()

    return user


def account_exists(account_no):

    con = connect()
    cur = con.cursor()

    cur.execute(
        "SELECT * FROM users WHERE account_no=?",
        (account_no,)
    )

    user = cur.fetchone()

    con.close()

    return user


def generate_account():

    while True:

        number = "10" + "".join(
            secrets.choice("0123456789")
            for _ in range(8)
        )

        if not account_exists(number):
            return number


def generate_txid():

    return "TX" + secrets.token_hex(6).upper()


def create_user(message):

    if get_user(message.from_user.id):
        return

    account_no = generate_account()

    con = connect()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO users
        (
            user_id,
            username,
            first_name,
            account_no,
            balance,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.first_name or "",
        account_no,
        0,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    con.commit()
    con.close()


def add_transaction(
    user_id,
    tx_type,
    amount,
    description
):

    txid = generate_txid()

    con = connect()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO transactions
        (
            user_id,
            type,
            amount,
            description,
            txid,
            created_at
        )
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


def today_amount(user_id, tx_type):

    today = date.today().strftime("%Y-%m-%d")

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id=?
        AND type=?
        AND created_at LIKE ?
    """, (
        user_id,
        tx_type,
        today + "%"
    ))

    amount = cur.fetchone()[0]

    con.close()

    return amount


# =========================================================
# KEYBOARDS
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
                    text="💸 Send Money",
                    callback_data="send"
                ),

                InlineKeyboardButton(
                    text="➕ Add Money",
                    callback_data="add_money"
                )
            ],

            [
                InlineKeyboardButton(
                    text="➖ Withdraw",
                    callback_data="withdraw"
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
# STATES
# =========================================================

class SendState(StatesGroup):

    account = State()
    amount = State()


class WithdrawState(StatesGroup):

    amount = State()


class AddMoneyState(StatesGroup):

    amount = State()


# =========================================================
# BOT
# =========================================================

bot = Bot(BOT_TOKEN)

dp = Dispatcher(
    storage=MemoryStorage()
)


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

        f"🏦 <b>MyBank</b>\n\n"
        f"Hello {message.from_user.first_name} 👋\n\n"
        f"🔢 Account: <code>{user[3]}</code>\n"
        f"💰 Balance: {CURRENCY}{user[4]:.2f}\n\n"
        f"Select an option:",

        reply_markup=main_menu(),

        parse_mode="HTML"
    )


# =========================================================
# BALANCE
# =========================================================

@dp.callback_query(F.data == "balance")
async def balance(callback: CallbackQuery):

    user = get_user(callback.from_user.id)

    await callback.message.edit_text(

        f"💰 <b>Balance</b>\n\n"
        f"{CURRENCY}{user[4]:.2f}",

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

    status = "🔴 Frozen" if user[6] else "🟢 Active"

    await callback.message.edit_text(

        f"👤 <b>Profile</b>\n\n"
        f"Name: {user[2]}\n"
        f"Username: @{user[1] or 'None'}\n"
        f"Account: <code>{user[3]}</code>\n"
        f"Balance: {CURRENCY}{user[4]:.2f}\n"
        f"Status: {status}\n"
        f"Created: {user[7]}",

        reply_markup=main_menu(),

        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# SEND MONEY
# =========================================================

@dp.callback_query(F.data == "send")
async def send_start(
    callback: CallbackQuery,
    state: FSMContext
):

    user = get_user(callback.from_user.id)

    if user[6] == 1:

        await callback.answer(
            "Account frozen.",
            show_alert=True
        )

        return

    await state.set_state(
        SendState.account
    )

    await callback.message.answer(
        "💸 <b>Send Money</b>\n\n"
        "Enter receiver's account number:",
        parse_mode="HTML"
    )

    await callback.answer()


@dp.message(SendState.account)
async def send_account(
    message: Message,
    state: FSMContext
):

    account = message.text.strip()

    receiver = account_exists(account)

    if not receiver:

        await message.answer(
            "❌ Account not found.\n\n"
            "Enter a valid account number."
        )

        return

    if receiver[0] == message.from_user.id:

        await message.answer(
            "❌ You cannot send money to yourself."
        )

        return

    if receiver[6] == 1:

        await message.answer(
            "❌ Receiver account is frozen."
        )

        return

    await state.update_data(
        receiver_id=receiver[0],
        receiver_account=receiver[3]
    )

    await state.set_state(
        SendState.amount
    )

    await message.answer(
        f"👤 Receiver: {receiver[2]}\n"
        f"🔢 Account: <code>{receiver[3]}</code>\n\n"
        f"Enter amount:\n"
        f"Maximum: {CURRENCY}{MAX_SEND}",
        parse_mode="HTML"
    )


@dp.message(SendState.amount)
async def send_amount(
    message: Message,
    state: FSMContext
):

    try:

        amount = float(message.text)

    except ValueError:

        await message.answer(
            "❌ Enter a valid amount."
        )

        return

    if amount <= 0:

        await message.answer(
            "❌ Amount must be greater than 0."
        )

        return

    if amount > MAX_SEND:

        await message.answer(
            f"❌ Maximum send amount is "
            f"{CURRENCY}{MAX_SEND}."
        )

        return

    user = get_user(message.from_user.id)

    if amount > user[4]:

        await message.answer(
            "❌ Insufficient balance."
        )

        return

    sent_today = today_amount(
        message.from_user.id,
        "SEND"
    )

    if sent_today + amount > SEND_DAILY_LIMIT:

        await message.answer(
            f"❌ Daily send limit exceeded.\n\n"
            f"Daily limit: {CURRENCY}{SEND_DAILY_LIMIT}"
        )

        await state.clear()

        return

    data = await state.get_data()

    receiver_id = data["receiver_id"]

    fee = amount * SEND_FEE_PERCENT / 100

    total = amount + fee

    if total > user[4]:

        await message.answer(
            "❌ Insufficient balance after fee."
        )

        await state.clear()

        return

    con = connect()
    cur = con.cursor()

    try:

        cur.execute(
            "UPDATE users SET balance=balance-? WHERE user_id=?",
            (total, message.from_user.id)
        )

        cur.execute(
            "UPDATE users SET balance=balance+? WHERE user_id=?",
            (amount, receiver_id)
        )

        con.commit()

    except Exception:

        con.rollback()

        await message.answer(
            "❌ Transaction failed."
        )

        con.close()

        await state.clear()

        return

    con.close()

    txid = add_transaction(
        message.from_user.id,
        "SEND",
        amount,
        f"Transfer to {data['receiver_account']}"
    )

    add_transaction(
        receiver_id,
        "RECEIVE",
        amount,
        f"Received from {user[3]}"
    )

    await message.answer(

        f"✅ <b>Money Sent</b>\n\n"
        f"Amount: {CURRENCY}{amount:.2f}\n"
        f"Fee: {CURRENCY}{fee:.2f}\n"
        f"Total: {CURRENCY}{total:.2f}\n\n"
        f"Transaction ID:\n"
        f"<code>{txid}</code>",

        parse_mode="HTML"
    )

    await state.clear()


# =========================================================
# ADD MONEY
# =========================================================

@dp.callback_query(F.data == "add_money")
async def add_money_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(
        AddMoneyState.amount
    )

    await callback.message.answer(
        "➕ <b>Add Money</b>\n\n"
        "Enter amount you want to add:",
        parse_mode="HTML"
    )

    await callback.answer()


@dp.message(AddMoneyState.amount)
async def add_money_amount(
    message: Message,
    state: FSMContext
):

    try:

        amount = float(message.text)

    except ValueError:

        await message.answer(
            "❌ Enter a valid amount."
        )

        return

    if amount <= 0:

        await message.answer(
            "❌ Invalid amount."
        )

        return

    con = connect()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO requests
        (user_id, type, amount, status, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        message.from_user.id,
        "DEPOSIT",
        amount,
        "pending",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    ))

    request_id = cur.lastrowid

    con.commit()
    con.close()

    await message.answer(

        f"✅ <b>Deposit Request Created</b>\n\n"
        f"Amount: {CURRENCY}{amount:.2f}\n"
        f"Request ID: <code>#{request_id}</code>\n\n"
        f"⏳ Waiting for admin approval.",

        parse_mode="HTML"
    )

    await bot.send_message(

        ADMIN_ID,

        f"💰 <b>New Deposit Request</b>\n\n"
        f"User: <code>{message.from_user.id}</code>\n"
        f"Amount: {CURRENCY}{amount:.2f}\n"
        f"Request: #{request_id}",

        parse_mode="HTML"
    )

    await state.clear()


# =========================================================
# WITHDRAW
# =========================================================

@dp.callback_query(F.data == "withdraw")
async def withdraw_start(
    callback: CallbackQuery,
    state: FSMContext
):

    user = get_user(callback.from_user.id)

    if user[4] <= 0:

        await callback.answer(
            "Insufficient balance.",
            show_alert=True
        )

        return

    await state.set_state(
        WithdrawState.amount
    )

    await callback.message.answer(
        "➖ <b>Withdraw</b>\n\n"
        f"Available: {CURRENCY}{user[4]:.2f}\n"
        f"Maximum: {CURRENCY}{MAX_WITHDRAW}\n\n"
        "Enter amount:",
        parse_mode="HTML"
    )

    await callback.answer()


@dp.message(WithdrawState.amount)
async def withdraw_amount(
    message: Message,
    state: FSMContext
):

    try:

        amount = float(message.text)

    except ValueError:

        await message.answer(
            "❌ Enter a valid amount."
        )

        return

    if amount <= 0:

        await message.answer(
            "❌ Invalid amount."
        )

        return

    if amount > MAX_WITHDRAW:

        await message.answer(
            f"❌ Maximum withdrawal is "
            f"{CURRENCY}{MAX_WITHDRAW}."
        )

        return

    user = get_user(message.from_user.id)

    if amount > user[4]:

        await message.answer(
            "❌ Insufficient balance."
        )

        await state.clear()

        return

    withdrawn_today = today_amount(
        message.from_user.id,
        "WITHDRAW"
    )

    if withdrawn_today + amount > WITHDRAW_DAILY_LIMIT:

        await message.answer(
            f"❌ Daily withdrawal limit exceeded.\n\n"
            f"Limit: {CURRENCY}{WITHDRAW_DAILY_LIMIT}"
        )

        await state.clear()

        return

    fee = amount * WITHDRAW_FEE_PERCENT / 100

    total = amount + fee

    if total > user[4]:

        await message.answer(
            "❌ Insufficient balance after fee."
        )

        await state.clear()

        return

    con = connect()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO requests
        (user_id, type, amount, status, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        message.from_user.id,
        "WITHDRAW",
        amount,
        "pending",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    ))

    request_id = cur.lastrowid

    con.commit()
    con.close()

    await message.answer(

        f"✅ <b>Withdrawal Request</b>\n\n"
        f"Amount: {CURRENCY}{amount:.2f}\n"
        f"Fee: {CURRENCY}{fee:.2f}\n"
        f"Request ID: <code>#{request_id}</code>\n\n"
        f"⏳ Waiting for admin approval.",

        parse_mode="HTML"
    )

    await bot.send_message(

        ADMIN_ID,

        f"➖ <b>New Withdrawal Request</b>\n\n"
        f"User: <code>{message.from_user.id}</code>\n"
        f"Amount: {CURRENCY}{amount:.2f}\n"
        f"Request: #{request_id}",

        parse_mode="HTML"
    )

    await state.clear()


# =========================================================
# TRANSACTIONS
# =========================================================

@dp.callback_query(F.data == "transactions")
async def transactions(callback: CallbackQuery):

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT type, amount, description, txid, created_at
        FROM transactions
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 10
    """, (
        callback.from_user.id,
    ))

    rows = cur.fetchall()

    con.close()

    if not rows:

        text = (
            "🧾 <b>Transactions</b>\n\n"
            "No transactions yet."
        )

    else:

        text = "🧾 <b>Recent Transactions</b>\n\n"

        for row in rows:

            text += (
                f"• <b>{row[0]}</b>\n"
                f"Amount: {CURRENCY}{row[1]:.2f}\n"
                f"{row[2]}\n"
                f"ID: <code>{row[3]}</code>\n"
                f"{row[4]}\n\n"
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

        await message.answer(
            "❌ Access denied."
        )

        return

    con = connect()
    cur = con.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM users"
    )

    users = cur.fetchone()[0]

    cur.execute(
        "SELECT COALESCE(SUM(balance), 0) FROM users"
    )

    balance = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM requests
        WHERE status='pending'
    """)

    pending = cur.fetchone()[0]

    con.close()

    await message.answer(

        f"👑 <b>Admin Panel</b>\n\n"
        f"👥 Users: {users}\n"
        f"💰 Total Balance: {CURRENCY}{balance:.2f}\n"
        f"⏳ Pending Requests: {pending}\n\n"
        f"/requests\n"
        f"/users",

        parse_mode="HTML"
    )


# =========================================================
# ADMIN REQUESTS
# =========================================================

@dp.message(Command("requests"))
async def requests(message: Message):

    if message.from_user.id != ADMIN_ID:

        return

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT id, user_id, type, amount, created_at
        FROM requests
        WHERE status='pending'
        ORDER BY id DESC
        LIMIT 20
    """)

    rows = cur.fetchall()

    con.close()

    if not rows:

        await message.answer(
            "✅ No pending requests."
        )

        return

    for row in rows:

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[

                [
                    InlineKeyboardButton(
                        text="✅ Approve",
                        callback_data=f"approve:{row[0]}"
                    ),

                    InlineKeyboardButton(
                        text="❌ Reject",
                        callback_data=f"reject:{row[0]}"
                    )
                ]

            ]
        )

        await message.answer(

            f"🧾 <b>Request #{row[0]}</b>\n\n"
            f"User: <code>{row[1]}</code>\n"
            f"Type: {row[2]}\n"
            f"Amount: {CURRENCY}{row[3]:.2f}\n"
            f"Date: {row[4]}",

            reply_markup=keyboard,

            parse_mode="HTML"
        )


# =========================================================
# APPROVE REQUEST
# =========================================================

@dp.callback_query(
    F.data.startswith("approve:")
)
async def approve_request(
    callback: CallbackQuery
):

    if callback.from_user.id != ADMIN_ID:

        await callback.answer(
            "Access denied.",
            show_alert=True
        )

        return

    request_id = int(
        callback.data.split(":")[1]
    )

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT user_id, type, amount, status
        FROM requests
        WHERE id=?
    """, (request_id,))

    request = cur.fetchone()

    if not request:

        con.close()

        await callback.answer(
            "Request not found.",
            show_alert=True
        )

        return

    if request[3] != "pending":

        con.close()

        await callback.answer(
            "Already processed.",
            show_alert=True
        )

        return

    user_id = request[0]
    req_type = request[1]
    amount = request[2]

    if req_type == "DEPOSIT":

        cur.execute("""
            UPDATE users
            SET balance=balance+?
            WHERE user_id=?
        """, (
            amount,
            user_id
        ))

        txid = generate_txid()

        cur.execute("""
            INSERT INTO transactions
            (
                user_id,
                type,
                amount,
                description,
                txid,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            "DEPOSIT",
            amount,
            "Admin approved deposit",
            txid,
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ))

    elif req_type == "WITHDRAW":

        cur.execute(
            "SELECT balance FROM users WHERE user_id=?",
            (user_id,)
        )

        user = cur.fetchone()

        if not user or user[0] < amount:

            con.close()

            await callback.answer(
                "Insufficient balance.",
                show_alert=True
            )

            return

        cur.execute("""
            UPDATE users
            SET balance=balance-?
            WHERE user_id=?
        """, (
            amount,
            user_id
        ))

        txid = generate_txid()

        cur.execute("""
            INSERT INTO transactions
            (
                user_id,
                type,
                amount,
                description,
                txid,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            "WITHDRAW",
            amount,
            "Admin approved withdrawal",
            txid,
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ))

    else:

        con.close()

        await callback.answer(
            "Invalid request.",
            show_alert=True
        )

        return

    cur.execute("""
        UPDATE requests
        SET status='approved'
        WHERE id=?
    """, (request_id,))

    con.commit()
    con.close()

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.answer(
        "Approved."
    )

    await bot.send_message(

        user_id,

        f"✅ <b>Request Approved</b>\n\n"
        f"Type: {req_type}\n"
        f"Amount: {CURRENCY}{amount:.2f}\n"
        f"Transaction: <code>{txid}</code>",

        parse_mode="HTML"
    )


# =========================================================
# REJECT REQUEST
# =========================================================

@dp.callback_query(
    F.data.startswith("reject:")
)
async def reject_request(
    callback: CallbackQuery
):

    if callback.from_user.id != ADMIN_ID:

        await callback.answer(
            "Access denied.",
            show_alert=True
        )

        return

    request_id = int(
        callback.data.split(":")[1]
    )

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT user_id, type, amount, status
        FROM requests
        WHERE id=?
    """, (
        request_id,
    ))

    request = cur.fetchone()

    if not request:

        con.close()

        await callback.answer(
            "Request not found.",
            show_alert=True
        )

        return

    if request[3] != "pending":

        con.close()

        await callback.answer(
            "Already processed.",
            show_alert=True
        )

        return

    cur.execute("""
        UPDATE requests
        SET status='rejected'
        WHERE id=?
    """, (
        request_id,
    ))

    con.commit()
    con.close()

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.answer(
        "Rejected."
    )

    await bot.send_message(

        request[0],

        f"❌ <b>Request Rejected</b>\n\n"
        f"Type: {request[1]}\n"
        f"Amount: {CURRENCY}{request[2]:.2f}\n"
        f"Request: #{request_id}",

        parse_mode="HTML"
    )


# =========================================================
# ADMIN USERS
# =========================================================

@dp.message(Command("users"))
async def users(message: Message):

    if message.from_user.id != ADMIN_ID:

        return

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT user_id, first_name, account_no, balance
        FROM users
        ORDER BY created_at DESC
        LIMIT 20
    """)

    rows = cur.fetchall()

    con.close()

    if not rows:

        await message.answer(
            "No users."
        )

        return

    text = "👥 <b>Users</b>\n\n"

    for row in rows:

        text += (
            f"👤 {row[1]}\n"
            f"ID: <code>{row[0]}</code>\n"
            f"Account: <code>{row[2]}</code>\n"
            f"Balance: {CURRENCY}{row[3]:.2f}\n\n"
        )

    await message.answer(
        text,
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
