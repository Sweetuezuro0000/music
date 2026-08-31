import sqlite3
from datetime import datetime, date

from aiogram import F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import (
    ADMIN_ID,
    CURRENCY,
    MAX_SEND,
    MAX_WITHDRAW,
    SEND_DAILY_LIMIT,
    WITHDRAW_DAILY_LIMIT,
    SEND_FEE_PERCENT,
    WITHDRAW_FEE_PERCENT,
)

from database import (
    connect,
    get_user,
    get_user_by_account,
    update_balance,
    add_transaction,
)


# =========================================================
# STATES
# =========================================================

class SendState(StatesGroup):
    account = State()
    amount = State()


class AddMoneyState(StatesGroup):
    amount = State()


class WithdrawState(StatesGroup):
    amount = State()


# =========================================================
# DAILY TOTAL
# =========================================================

def daily_total(user_id, transaction_type):

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
        transaction_type,
        today + "%"
    ))

    total = cur.fetchone()[0]

    con.close()

    return float(total or 0)


# =========================================================
# SEND MONEY - START
# =========================================================

async def send_start(
    callback: CallbackQuery,
    state: FSMContext
):

    user = get_user(callback.from_user.id)

    if not user:
        await callback.answer(
            "Use /start first.",
            show_alert=True
        )
        return

    if user[6] == 1:
        await callback.answer(
            "🚫 Your account is frozen.",
            show_alert=True
        )
        return

    await state.set_state(
        SendState.account
    )

    await callback.message.answer(
        "💸 <b>Send Money</b>\n\n"
        "Receiver ka account number bhejo:",
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# SEND - ACCOUNT
# =========================================================

async def send_account(
    message: Message,
    state: FSMContext
):

    account = message.text.strip()

    receiver = get_user_by_account(account)

    if not receiver:
        await message.answer(
            "❌ Account number nahi mila.\n\n"
            "Dobara valid account number bhejo."
        )
        return

    if receiver[0] == message.from_user.id:
        await message.answer(
            "❌ Khud ko money send nahi kar sakte."
        )
        return

    if receiver[6] == 1:
        await message.answer(
            "❌ Receiver ka account frozen hai."
        )
        return

    await state.update_data(
        receiver_id=receiver[0],
        receiver_account=receiver[3],
        receiver_name=receiver[2],
    )

    await state.set_state(
        SendState.amount
    )

    await message.answer(
        f"👤 <b>Receiver</b>\n\n"
        f"Name: {receiver[2]}\n"
        f"Account: <code>{receiver[3]}</code>\n\n"
        f"💰 Amount bhejo:\n"
        f"Maximum: {CURRENCY}{MAX_SEND:.2f}",
        parse_mode="HTML"
    )


# =========================================================
# SEND - AMOUNT
# =========================================================

async def send_amount(
    message: Message,
    state: FSMContext
):

    try:
        amount = float(
            message.text.strip()
        )
    except ValueError:
        await message.answer(
            "❌ Sirf amount enter karo.\n\n"
            "Example: 500"
        )
        return

    if amount <= 0:
        await message.answer(
            "❌ Amount 0 se greater hona chahiye."
        )
        return

    if amount > MAX_SEND:
        await message.answer(
            f"❌ Maximum send limit "
            f"{CURRENCY}{MAX_SEND:.2f} hai."
        )
        return

    sender = get_user(
        message.from_user.id
    )

    if not sender:
        await message.answer(
            "❌ Account not found."
        )
        await state.clear()
        return

    if sender[6] == 1:
        await message.answer(
            "🚫 Account frozen."
        )
        await state.clear()
        return

    current_daily = daily_total(
        sender[0],
        "SEND"
    )

    if current_daily + amount > SEND_DAILY_LIMIT:
        await message.answer(
            f"❌ Daily send limit exceed.\n\n"
            f"Used: {CURRENCY}{current_daily:.2f}\n"
            f"Limit: {CURRENCY}{SEND_DAILY_LIMIT:.2f}"
        )
        await state.clear()
        return

    fee = (
        amount * SEND_FEE_PERCENT / 100
    )

    total = amount + fee

    if sender[4] < total:
        await message.answer(
            f"❌ Insufficient balance.\n\n"
            f"Required: {CURRENCY}{total:.2f}\n"
            f"Balance: {CURRENCY}{sender[4]:.2f}"
        )
        await state.clear()
        return

    data = await state.get_data()

    receiver_id = data["receiver_id"]

    receiver = get_user(receiver_id)

    if not receiver:
        await message.answer(
            "❌ Receiver account unavailable."
        )
        await state.clear()
        return

    # -----------------------------------------------------
    # ATOMIC TRANSFER
    # -----------------------------------------------------

    con = connect()
    cur = con.cursor()

    try:

        cur.execute("""
            UPDATE users
            SET balance = balance - ?
            WHERE user_id=?
            AND balance >= ?
        """, (
            total,
            sender[0],
            total
        ))

        if cur.rowcount != 1:
            raise Exception(
                "Sender balance changed."
            )

        cur.execute("""
            UPDATE users
            SET balance = balance + ?
            WHERE user_id=?
            AND frozen=0
        """, (
            amount,
            receiver_id
        ))

        if cur.rowcount != 1:
            raise Exception(
                "Receiver unavailable."
            )

        con.commit()

    except Exception:

        con.rollback()
        con.close()

        await message.answer(
            "❌ Transaction failed.\n"
            "Money transfer nahi hua."
        )

        await state.clear()
        return

    con.close()

    # -----------------------------------------------------
    # TRANSACTION RECORDS
    # -----------------------------------------------------

    txid = add_transaction(
        sender[0],
        "SEND",
        amount,
        f"Sent to {data['receiver_account']}"
    )

    add_transaction(
        receiver_id,
        "RECEIVE",
        amount,
        f"Received from {sender[3]}"
    )

    # -----------------------------------------------------
    # SUCCESS
    # -----------------------------------------------------

    await message.answer(
        f"✅ <b>Money Sent Successfully</b>\n\n"
        f"👤 To: {data['receiver_name']}\n"
        f"🔢 Account: <code>{data['receiver_account']}</code>\n"
        f"💸 Amount: {CURRENCY}{amount:.2f}\n"
        f"💵 Fee: {CURRENCY}{fee:.2f}\n"
        f"💰 Total: {CURRENCY}{total:.2f}\n\n"
        f"🧾 Transaction ID:\n"
        f"<code>{txid}</code>",
        parse_mode="HTML"
    )

    # Receiver notification

    try:
        await message.bot.send_message(
            receiver_id,
            f"💰 <b>Money Received</b>\n\n"
            f"From: {sender[2]}\n"
            f"Amount: {CURRENCY}{amount:.2f}\n"
            f"Transaction: <code>{txid}</code>",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await state.clear()


# =========================================================
# ADD MONEY
# =========================================================

async def add_money_start(
    callback: CallbackQuery,
    state: FSMContext
):

    user = get_user(
        callback.from_user.id
    )

    if not user:
        await callback.answer(
            "Use /start first.",
            show_alert=True
        )
        return

    if user[6] == 1:
        await callback.answer(
            "🚫 Account frozen.",
            show_alert=True
        )
        return

    await state.set_state(
        AddMoneyState.amount
    )

    await callback.message.answer(
        "➕ <b>Add Money</b>\n\n"
        "Kitna amount add karna hai?\n\n"
        "Amount enter karo:",
        parse_mode="HTML"
    )

    await callback.answer()


async def add_money_amount(
    message: Message,
    state: FSMContext
):

    try:
        amount = float(
            message.text.strip()
        )
    except ValueError:
        await message.answer(
            "❌ Valid amount enter karo."
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
        (
            user_id,
            type,
            amount,
            status,
            created_at
        )
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
        f"⏳ Admin approval ka wait karo.",
        parse_mode="HTML"
    )

    await message.bot.send_message(
        ADMIN_ID,
        f"💰 <b>New Deposit Request</b>\n\n"
        f"User: <code>{message.from_user.id}</code>\n"
        f"Amount: {CURRENCY}{amount:.2f}\n"
        f"Request: <code>#{request_id}</code>",
        parse_mode="HTML"
    )

    await state.clear()


# =========================================================
# WITHDRAW
# =========================================================

async def withdraw_start(
    callback: CallbackQuery,
    state: FSMContext
):

    user = get_user(
        callback.from_user.id
    )

    if not user:
        await callback.answer(
            "Use /start first.",
            show_alert=True
        )
        return

    if user[6] == 1:
        await callback.answer(
            "🚫 Account frozen.",
            show_alert=True
        )
        return

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
        f"Maximum: {CURRENCY}{MAX_WITHDRAW:.2f}\n\n"
        "Amount enter karo:",
        parse_mode="HTML"
    )

    await callback.answer()


async def withdraw_amount(
    message: Message,
    state: FSMContext
):

    try:
        amount = float(
            message.text.strip()
        )
    except ValueError:
        await message.answer(
            "❌ Valid amount enter karo."
        )
        return

    if amount <= 0:
        await message.answer(
            "❌ Invalid amount."
        )
        return

    if amount > MAX_WITHDRAW:
        await message.answer(
            f"❌ Maximum withdrawal "
            f"{CURRENCY}{MAX_WITHDRAW:.2f} hai."
        )
        return

    user = get_user(
        message.from_user.id
    )

    if not user:
        await message.answer(
            "❌ Account not found."
        )
        await state.clear()
        return

    if user[4] < amount:
        await message.answer(
            "❌ Insufficient balance."
        )
        await state.clear()
        return

    current_daily = daily_total(
        user[0],
        "WITHDRAW"
    )

    if (
        current_daily + amount
        > WITHDRAW_DAILY_LIMIT
    ):
        await message.answer(
            f"❌ Daily withdrawal limit exceed.\n\n"
            f"Used: {CURRENCY}{current_daily:.2f}\n"
            f"Limit: {CURRENCY}{WITHDRAW_DAILY_LIMIT:.2f}"
        )
        await state.clear()
        return

    fee = (
        amount * WITHDRAW_FEE_PERCENT / 100
    )

    total = amount + fee

    if user[4] < total:
        await message.answer(
            f"❌ Balance fee ke saath insufficient hai.\n\n"
            f"Required: {CURRENCY}{total:.2f}"
        )
        await state.clear()
        return

    con = connect()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO requests
        (
            user_id,
            type,
            amount,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        user[0],
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
        f"✅ <b>Withdrawal Request Created</b>\n\n"
        f"Amount: {CURRENCY}{amount:.2f}\n"
        f"Fee: {CURRENCY}{fee:.2f}\n"
        f"Request ID: <code>#{request_id}</code>\n\n"
        f"⏳ Admin approval ka wait karo.",
        parse_mode="HTML"
    )

    await message.bot.send_message(
        ADMIN_ID,
        f"➖ <b>New Withdrawal Request</b>\n\n"
        f"User: <code>{user[0]}</code>\n"
        f"Account: <code>{user[3]}</code>\n"
        f"Amount: {CURRENCY}{amount:.2f}\n"
        f"Request: <code>#{request_id}</code>",
        parse_mode="HTML"
    )

    await state.clear()


# =========================================================
# REGISTER
# =========================================================

def register_payment_handlers(dp):

    dp.callback_query.register(
        send_start,
        F.data == "send"
    )

    dp.message.register(
        send_account,
        SendState.account
    )

    dp.message.register(
        send_amount,
        SendState.amount
    )

    dp.callback_query.register(
        add_money_start,
        F.data == "add_money"
    )

    dp.message.register(
        add_money_amount,
        AddMoneyState.amount
    )

    dp.callback_query.register(
        withdraw_start,
        F.data == "withdraw"
    )

    dp.message.register(
        withdraw_amount,
        WithdrawState.amount
    )
