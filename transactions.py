from aiogram import F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from database import connect, get_user


# =========================================================
# HISTORY KEYBOARD
# =========================================================

def history_keyboard(rows):

    buttons = []

    for row in rows:

        tx_id = row[0]
        tx_type = row[1]

        icon = {
            "SEND": "💸",
            "RECEIVE": "💰",
            "DEPOSIT": "➕",
            "WITHDRAW": "➖"
        }.get(tx_type, "🧾")

        buttons.append([
            InlineKeyboardButton(
                text=f"{icon} {tx_type.title()} • #{tx_id}",
                callback_data=f"tx:{tx_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Back",
            callback_data="user_home"
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


# =========================================================
# HISTORY
# =========================================================

async def transactions_page(
    callback: CallbackQuery
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

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT
            id,
            type,
            amount,
            description,
            created_at
        FROM transactions
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 10
    """, (
        user[0],
    ))

    rows = cur.fetchall()

    con.close()

    # -----------------------------------------------------
    # EMPTY HISTORY
    # -----------------------------------------------------

    if not rows:

        await callback.message.edit_text(

            "🧾 <b>TRANSACTION HISTORY</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"

            "📭 <b>No transactions yet</b>\n\n"

            "Your completed transactions will "
            "appear here.",

            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⬅️ Back",
                            callback_data="user_home"
                        )
                    ]
                ]
            ),

            parse_mode="HTML"
        )

        await callback.answer()

        return

    # -----------------------------------------------------
    # HISTORY TEXT
    # -----------------------------------------------------

    text = (
        "🧾 <b>TRANSACTION HISTORY</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )

    for row in rows:

        tx_id = row[0]
        tx_type = row[1]
        amount = float(row[2])
        description = row[3] or "Transaction"
        created_at = row[4]

        if tx_type == "SEND":

            icon = "🔴"
            sign = "-"

        elif tx_type == "RECEIVE":

            icon = "🟢"
            sign = "+"

        elif tx_type == "DEPOSIT":

            icon = "🟢"
            sign = "+"

        elif tx_type == "WITHDRAW":

            icon = "🔴"
            sign = "-"

        else:

            icon = "🧾"
            sign = ""

        text += (
            f"{icon} <b>{tx_type}</b>\n"
            f"   {description}\n"
            f"   <b>{sign}₹{amount:,.2f}</b>\n"
            f"   🕐 {created_at}\n"
            f"   🧾 <code>#{tx_id}</code>\n\n"
        )

    text += "━━━━━━━━━━━━━━━━━━"

    await callback.message.edit_text(

        text,

        reply_markup=history_keyboard(rows),

        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# TRANSACTION DETAILS
# =========================================================

async def transaction_details(
    callback: CallbackQuery
):

    try:

        tx_id = int(
            callback.data.split(":")[1]
        )

    except (ValueError, IndexError):

        await callback.answer(
            "Invalid transaction.",
            show_alert=True
        )

        return

    user = get_user(
        callback.from_user.id
    )

    if not user:

        await callback.answer(
            "Account not found.",
            show_alert=True
        )

        return

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT
            id,
            type,
            amount,
            description,
            created_at
        FROM transactions
        WHERE id=?
        AND user_id=?
        LIMIT 1
    """, (
        tx_id,
        user[0]
    ))

    row = cur.fetchone()

    con.close()

    if not row:

        await callback.answer(
            "Transaction not found.",
            show_alert=True
        )

        return

    tx_id = row[0]
    tx_type = row[1]
    amount = float(row[2])
    description = row[3] or "Transaction"
    created_at = row[4]

    if tx_type == "SEND":

        icon = "💸"
        status = "🔴 Money Sent"

    elif tx_type == "RECEIVE":

        icon = "💰"
        status = "🟢 Money Received"

    elif tx_type == "DEPOSIT":

        icon = "➕"
        status = "🟢 Money Added"

    elif tx_type == "WITHDRAW":

        icon = "➖"
        status = "🔴 Withdrawal"

    else:

        icon = "🧾"
        status = tx_type

    await callback.message.edit_text(

        f"{icon} <b>TRANSACTION DETAILS</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"

        f"📌 Status\n"
        f"<b>{status}</b>\n\n"

        f"💰 Amount\n"
        f"<code>₹ {amount:,.2f}</code>\n\n"

        f"📝 Description\n"
        f"{description}\n\n"

        f"🧾 Transaction ID\n"
        f"<code>#{tx_id}</code>\n\n"

        f"🕐 Date & Time\n"
        f"<code>{created_at}</code>\n\n"

        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔐 Secure Transaction",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[

                [
                    InlineKeyboardButton(
                        text="⬅️ Back to History",
                        callback_data="transactions"
                    )
                ],

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
# REGISTER
# =========================================================

def register_transaction_handlers(dp):

    dp.callback_query.register(
        transactions_page,
        F.data == "transactions"
    )

    dp.callback_query.register(
        transaction_details,
        F.data.startswith("tx:")
    )
