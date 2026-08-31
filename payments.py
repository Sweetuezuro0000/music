from aiogram import F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from config import (
    CURRENCY,
    MAX_SEND,
    SEND_DAILY_LIMIT,
    SEND_FEE_PERCENT,
    MAX_WITHDRAW,
    WITHDRAW_DAILY_LIMIT,
    WITHDRAW_FEE_PERCENT,
    ADMIN_ID
)

from database import (
    connect,
    get_user,
    get_user_by_account,
    add_transaction
)
import qrcode
import os
import time

from aiogram.types import FSInputFile

# =========================================================
# STATES
# =========================================================

class SendState(StatesGroup):
    account = State()
    amount = State()
    pin = State()


class AddMoneyState(StatesGroup):
    amount = State()


class WithdrawState(StatesGroup):
    amount = State()


# =========================================================
# DAILY TOTAL
# =========================================================

def daily_total(user_id, transaction_type):

    today = __import__("datetime").date.today().strftime(
        "%Y-%m-%d"
    )

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
# SEND START
# =========================================================

async def send_start(
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
            "🔒 Your account is frozen.",
            show_alert=True
        )
        return

    # PIN required
    if not user[5]:

        await callback.answer(
            "🔐 First set your Security PIN.",
            show_alert=True
        )

        return

    await state.set_state(
        SendState.account
    )

    await callback.message.edit_text(

        "💸 <b>SEND MONEY</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "Enter receiver's account number.\n\n"

        "🔢 Example:\n"
        "<code>1234567890</code>",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="❌ Cancel",
                        callback_data="send_cancel"
                    )
                ]
            ]
        ),

        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# SEND ACCOUNT
# =========================================================

async def send_account(
    message: Message,
    state: FSMContext
):

    account = message.text.strip()

    receiver = get_user_by_account(
        account
    )

    if not receiver:

        await message.answer(
            "❌ <b>Account Not Found</b>\n\n"
            "Please enter a valid account number.",
            parse_mode="HTML"
        )
        return

    if receiver[0] == message.from_user.id:

        await message.answer(
            "❌ You cannot send money to yourself."
        )
        return

    if receiver[6] == 1:

        await message.answer(
            "❌ Receiver's account is frozen."
        )
        return

    await state.update_data(
        receiver_id=receiver[0],
        receiver_account=receiver[3],
        receiver_name=receiver[2]
    )

    await state.set_state(
        SendState.amount
    )

    await message.answer(

        f"👤 <b>RECEIVER</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"

        f"Name\n"
        f"<b>{receiver[2]}</b>\n\n"

        f"Account\n"
        f"<code>{receiver[3]}</code>\n\n"

        f"💰 Enter amount\n"
        f"Maximum: {CURRENCY}{MAX_SEND:,.2f}",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="❌ Cancel",
                        callback_data="send_cancel"
                    )
                ]
            ]
        ),

        parse_mode="HTML"
    )


# =========================================================
# SEND AMOUNT
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
            "❌ Please enter a valid amount.\n\n"
            "Example: <code>500</code>",
            parse_mode="HTML"
        )

        return

    if amount <= 0:

        await message.answer(
            "❌ Amount must be greater than 0."
        )

        return

    if amount > MAX_SEND:

        await message.answer(
            f"❌ Maximum send limit is "
            f"{CURRENCY}{MAX_SEND:,.2f}."
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
            "🔒 Account frozen."
        )

        await state.clear()

        return

    # Daily limit
    current_daily = daily_total(
        sender[0],
        "SEND"
    )

    if current_daily + amount > SEND_DAILY_LIMIT:

        await message.answer(

            f"❌ <b>Daily Limit Exceeded</b>\n\n"
            f"Used: {CURRENCY}{current_daily:,.2f}\n"
            f"Limit: {CURRENCY}{SEND_DAILY_LIMIT:,.2f}",

            parse_mode="HTML"
        )

        await state.clear()

        return

    fee = (
        amount *
        SEND_FEE_PERCENT /
        100
    )

    total = amount + fee

    if sender[4] < total:

        await message.answer(

            f"❌ <b>Insufficient Balance</b>\n\n"
            f"Amount: {CURRENCY}{amount:,.2f}\n"
            f"Fee: {CURRENCY}{fee:,.2f}\n"
            f"Required: {CURRENCY}{total:,.2f}\n\n"
            f"Available: {CURRENCY}{sender[4]:,.2f}",

            parse_mode="HTML"
        )

        await state.clear()

        return

    data = await state.get_data()

    await state.update_data(
        amount=amount,
        fee=fee,
        total=total
    )

    await state.set_state(
        SendState.pin
    )

    # =====================================================
    # PIN SCREEN
    # =====================================================

    await message.answer(

        "🔐 <b>SECURITY VERIFICATION</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"👤 To: <b>{data['receiver_name']}</b>\n"
        f"💰 Amount: <b>{CURRENCY}{amount:,.2f}</b>\n"
        f"💵 Fee: <b>{CURRENCY}{fee:,.2f}</b>\n"
        f"💳 Total: <b>{CURRENCY}{total:,.2f}</b>\n\n"

        "Enter your <b>4-digit Security PIN</b> "
        "to continue.",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="❌ Cancel",
                        callback_data="send_cancel"
                    )
                ]
            ]
        ),

        parse_mode="HTML"
    )


# =========================================================
# PIN VERIFY
# =========================================================

async def send_pin(
    message: Message,
    state: FSMContext
):

    pin = message.text.strip()

    if (
        not pin.isdigit()
        or len(pin) != 4
    ):

        await message.answer(
            "❌ PIN must contain exactly 4 digits."
        )

        return

    sender = get_user(
        message.from_user.id
    )

    if not sender:

        await state.clear()

        await message.answer(
            "❌ Account not found."
        )

        return

    # -----------------------------------------------------
    # WRONG PIN
    # -----------------------------------------------------

    if pin != str(sender[5]):

        await message.answer(
            "❌ <b>Incorrect PIN</b>\n\n"
            "Transaction cancelled for your security.",
            parse_mode="HTML"
        )

        await state.clear()

        return

    # -----------------------------------------------------
    # PIN CORRECT
    # -----------------------------------------------------

    data = await state.get_data()

    await state.clear()

    # Final confirmation keyboard
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="✅ Confirm Transfer",
                    callback_data="confirm_transfer"
                )
            ],

            [
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="send_cancel"
                )
            ]

        ]
    )

    # Store confirmation data again
    # Using FSM requires state to remain active,
    # so we create a temporary confirmation state.

    await state.update_data(
        receiver_id=data["receiver_id"],
        receiver_account=data["receiver_account"],
        receiver_name=data["receiver_name"],
        amount=data["amount"],
        fee=data["fee"],
        total=data["total"]
    )

    await state.set_state(
        SendState.pin
    )

    await message.answer(

        "✅ <b>PIN VERIFIED</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "Please review the transfer:\n\n"

        f"👤 Receiver\n"
        f"<b>{data['receiver_name']}</b>\n"
        f"<code>{data['receiver_account']}</code>\n\n"

        f"💰 Amount\n"
        f"<b>{CURRENCY}{data['amount']:,.2f}</b>\n\n"

        f"💵 Fee\n"
        f"<b>{CURRENCY}{data['fee']:,.2f}</b>\n\n"

        f"💳 Total\n"
        f"<b>{CURRENCY}{data['total']:,.2f}</b>\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "⚠️ Confirm only if all details are correct.",

        reply_markup=keyboard,

        parse_mode="HTML"
    )


# =========================================================
# CONFIRM TRANSFER
# =========================================================

async def confirm_transfer(
    callback: CallbackQuery,
    state: FSMContext
):

    data = await state.get_data()

    if not data:

        await callback.answer(
            "Transaction expired.",
            show_alert=True
        )

        await state.clear()

        return

    sender = get_user(
        callback.from_user.id
    )

    receiver = get_user(
        data["receiver_id"]
    )

    if not sender or not receiver:

        await callback.message.edit_text(
            "❌ <b>TRANSFER FAILED</b>\n\n"
            "Account information is no longer available.",
            parse_mode="HTML"
        )

        await state.clear()

        await callback.answer()

        return

    if sender[6] == 1:

        await callback.answer(
            "🔒 Account frozen.",
            show_alert=True
        )

        await state.clear()

        return

    if receiver[6] == 1:

        await callback.message.edit_text(
            "❌ <b>TRANSFER FAILED</b>\n\n"
            "Receiver account is frozen.",
            parse_mode="HTML"
        )

        await state.clear()

        await callback.answer()

        return

    amount = float(data["amount"])
    fee = float(data["fee"])
    total = float(data["total"])

    # Re-check balance
    if sender[4] < total:

        await callback.message.edit_text(
            "❌ <b>TRANSFER FAILED</b>\n\n"
            "Insufficient balance.",
            parse_mode="HTML"
        )

        await state.clear()

        await callback.answer()

        return

    # =====================================================
    # ATOMIC TRANSFER
    # =====================================================

    con = connect()
    cur = con.cursor()

    try:

        cur.execute("BEGIN")

        cur.execute("""
            UPDATE users
            SET balance = balance - ?
            WHERE user_id=?
            AND balance >= ?
            AND frozen=0
        """, (
            total,
            sender[0],
            total
        ))

        if cur.rowcount != 1:
            raise Exception(
                "Sender balance update failed"
            )

        cur.execute("""
            UPDATE users
            SET balance = balance + ?
            WHERE user_id=?
            AND frozen=0
        """, (
            amount,
            receiver[0]
        ))

        if cur.rowcount != 1:
            raise Exception(
                "Receiver balance update failed"
            )

        con.commit()

    except Exception:

        con.rollback()
        con.close()

        await callback.message.edit_text(
            "❌ <b>TRANSFER FAILED</b>\n\n"
            "No money was deducted.",
            parse_mode="HTML"
        )

        await state.clear()

        await callback.answer()

        return

    con.close()

    # =====================================================
    # TRANSACTION RECORDS
    # =====================================================

    txid = add_transaction(
        sender[0],
        "SEND",
        amount,
        f"Sent to {data['receiver_account']}"
    )

    add_transaction(
        receiver[0],
        "RECEIVE",
        amount,
        f"Received from {sender[3]}"
    )

    # =====================================================
    # SUCCESS RECEIPT
    # =====================================================

    await callback.message.edit_text(

        "✅ <b>TRANSFER SUCCESSFUL</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"👤 To\n"
        f"<b>{data['receiver_name']}</b>\n"
        f"<code>{data['receiver_account']}</code>\n\n"

        f"💰 Amount\n"
        f"<b>{CURRENCY}{amount:,.2f}</b>\n\n"

        f"💵 Fee\n"
        f"<b>{CURRENCY}{fee:,.2f}</b>\n\n"

        f"💳 Total Paid\n"
        f"<b>{CURRENCY}{total:,.2f}</b>\n\n"

        f"🧾 Transaction ID\n"
        f"<code>{txid}</code>\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "🔐 Secure Transaction",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🏠 Main Menu",
                        callback_data="user_home"
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="🧾 History",
                        callback_data="transactions"
                    )
                ]
            ]
        ),

        parse_mode="HTML"
    )

    # Receiver notification
    try:

        await callback.bot.send_message(

            receiver[0],

            "💰 <b>MONEY RECEIVED</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"

            f"From: <b>{sender[2]}</b>\n"
            f"Amount: <b>{CURRENCY}{amount:,.2f}</b>\n\n"
            f"🧾 Transaction\n"
            f"<code>{txid}</code>",

            parse_mode="HTML"
        )

    except Exception:
        pass

    await state.clear()
    await callback.answer()


# =========================================================
# SEND CANCEL
# =========================================================

async def send_cancel(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.clear()

    await callback.message.edit_text(

        "❌ <b>TRANSFER CANCELLED</b>\n\n"
        "No money was deducted.",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🏠 Main Menu",
                        callback_data="user_home"
                    )
                ]
            ]
        ),

        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# ADD MONEY START
# =========================================================

async def add_money_start(
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
            "🔒 Account frozen.",
            show_alert=True
        )
        return

    await state.set_state(
        AddMoneyState.amount
    )

    await callback.message.edit_text(

        "➕ <b>ADD MONEY</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "💰 Enter the amount you want to add.\n\n"
        "You will receive a UPI QR for the "
        "exact amount.\n\n"

        "Example:\n"
        "<code>500</code>",

        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# ADD MONEY AMOUNT → QR
# =========================================================

async def add_money_amount(
    message: Message,
    state: FSMContext
):

    try:
        amount = float(message.text.strip())

    except ValueError:
        await message.answer(
            "❌ Please enter a valid amount."
        )
        return

    if amount <= 0:
        await message.answer(
            "❌ Amount must be greater than ₹0."
        )
        return

    if amount > MAX_SEND:
        await message.answer(
            f"❌ Maximum allowed amount is "
            f"{CURRENCY}{MAX_SEND:,.2f}."
        )
        return

    amount_text = f"{amount:.2f}"

    # UPI payment URI
    upi_uri = (
        "upi://pay?"
        "pa=emiakura00@oksbi"
        "&pn=MyBank"
        f"&am={amount_text}"
        "&cu=INR"
    )

    # QR folder
    os.makedirs("qr_codes", exist_ok=True)

    filename = (
        f"qr_codes/"
        f"{message.from_user.id}_"
        f"{int(time.time())}.png"
    )

    # Generate QR
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )

    qr.add_data(upi_uri)
    qr.make(fit=True)

    img = qr.make_image()

    img.save(filename)

    await state.update_data(
        amount=amount,
        qr_file=filename
    )

    await message.answer_photo(

        photo=FSInputFile(filename),

        caption=(

            "💳 <b>ADD MONEY</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"

            f"💰 Amount\n"
            f"<b>₹ {amount:,.2f}</b>\n\n"

            "📲 Scan this QR using any supported "
            "UPI app.\n\n"

            "⚠️ Pay the exact amount shown above.\n"
            "After payment, tap the button below "
            "to continue."

        ),

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[

                [
                    InlineKeyboardButton(
                        text="✅ I Have Paid",
                        callback_data="money_paid"
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="❌ Cancel",
                        callback_data="add_money_cancel"
                    )
                ]

            ]
        ),

        parse_mode="HTML"
    )


# =========================================================
# I HAVE PAID
# =========================================================

async def money_paid(
    callback: CallbackQuery,
    state: FSMContext
):

    data = await state.get_data()

    amount = data.get("amount")

    if not amount:

        await callback.answer(
            "Payment session expired.",
            show_alert=True
        )

        await state.clear()
        return

    user = get_user(
        callback.from_user.id
    )

    if not user:

        await callback.answer(
            "Account not found.",
            show_alert=True
        )

        await state.clear()
        return

    # Create pending deposit request
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
        "DEPOSIT",
        amount,
        "pending",
        __import__("datetime").datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    ))

    request_id = cur.lastrowid

    con.commit()
    con.close()

    await state.clear()

    await callback.message.edit_caption(

        caption=(

            "⏳ <b>PAYMENT UNDER REVIEW</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"

            f"💰 Amount\n"
            f"<b>₹ {amount:,.2f}</b>\n\n"

            f"🧾 Request ID\n"
            f"<code>#{request_id}</code>\n\n"

            "Your deposit request has been "
            "submitted for verification.\n\n"

            "💡 Balance will be updated only "
            "after the payment is verified."

        ),

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[

                [
                    InlineKeyboardButton(
                        text="🏠 Main Menu",
                        callback_data="user_home"
                    )
                ]

            ]
        ),

        parse_mode="HTML"
    )

    # Admin notification
    try:

        await callback.bot.send_message(

            ADMIN_ID,

            "💰 <b>NEW DEPOSIT REQUEST</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"

            f"👤 User: <code>{user[0]}</code>\n"
            f"🔢 Account: <code>{user[3]}</code>\n"
            f"💰 Amount: <b>₹ {amount:,.2f}</b>\n"
            f"🧾 Request: <code>#{request_id}</code>\n\n"

            "⏳ Status: <b>PENDING</b>",

            parse_mode="HTML"
        )

    except Exception:
        pass

    await callback.answer()


# =========================================================
# ADD MONEY CANCEL
# =========================================================

async def add_money_cancel(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.clear()

    await callback.message.edit_caption(

        caption=(
            "❌ <b>ADD MONEY CANCELLED</b>\n\n"
            "No deposit request was created."
        ),

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🏠 Main Menu",
                        callback_data="user_home"
                    )
                ]
            ]
        ),

        parse_mode="HTML"
    )

    await callback.answer()# =========================================================
# WITHDRAW START
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
            "🔒 Account frozen.",
            show_alert=True
        )
        return

    await state.set_state(
        WithdrawState.amount
    )

    await callback.message.edit_text(

        "➖ <b>WITHDRAW</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"Available: <b>{CURRENCY}{user[4]:,.2f}</b>\n"
        f"Maximum: <b>{CURRENCY}{MAX_WITHDRAW:,.2f}</b>\n\n"

        "Enter withdrawal amount:",

        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# WITHDRAW AMOUNT
# =========================================================

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
            f"{CURRENCY}{MAX_WITHDRAW:,.2f}."
        )

        return

    user = get_user(
        message.from_user.id
    )

    if not user:

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
            f"❌ Daily withdrawal limit exceeded.\n\n"
            f"Used: {CURRENCY}{current_daily:,.2f}\n"
            f"Limit: {CURRENCY}{WITHDRAW_DAILY_LIMIT:,.2f}"
        )

        await state.clear()

        return

    fee = (
        amount *
        WITHDRAW_FEE_PERCENT /
        100
    )

    total = amount + fee

    if user[4] < total:

        await message.answer(
            f"❌ Insufficient balance.\n\n"
            f"Required: {CURRENCY}{total:,.2f}"
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
        __import__("datetime").datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    ))

    request_id = cur.lastrowid

    con.commit()
    con.close()

    await message.answer(

        f"✅ <b>WITHDRAWAL REQUEST CREATED</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"

        f"💰 Amount: <b>{CURRENCY}{amount:,.2f}</b>\n"
        f"💵 Fee: <b>{CURRENCY}{fee:,.2f}</b>\n"
        f"🧾 Request: <code>#{request_id}</code>\n\n"

        "⏳ Waiting for admin approval.",

        parse_mode="HTML"
    )

    await message.bot.send_message(

        ADMIN_ID,

        f"➖ <b>NEW WITHDRAWAL REQUEST</b>\n\n"
        f"👤 User: <code>{user[0]}</code>\n"
        f"🔢 Account: <code>{user[3]}</code>\n"
        f"💰 Amount: <b>{CURRENCY}{amount:,.2f}</b>\n"
        f"🧾 Request: <code>#{request_id}</code>",

        parse_mode="HTML"
    )

    await state.clear()


# =========================================================
# REGISTER
# =========================================================

def register_payment_handlers(dp):

    # Send
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

    dp.message.register(
        send_pin,
        SendState.pin
    )

    dp.callback_query.register(
        confirm_transfer,
        F.data == "confirm_transfer"
    )

    dp.callback_query.register(
        send_cancel,
        F.data == "send_cancel"
    )

    # Add Money
    dp.callback_query.register(
        add_money_start,
        F.data == "add_money"
    )

    dp.message.register(
        add_money_amount,
        AddMoneyState.amount
    )

    # Withdraw
    dp.callback_query.register(
        withdraw_start,
        F.data == "withdraw"
    )

    dp.message.register(
        withdraw_amount,
        WithdrawState.amount
    )
