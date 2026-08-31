from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_ID
from database import connect, get_user, update_balance, set_frozen, add_transaction


def is_admin(user_id):
    return user_id == ADMIN_ID


async def admin_panel(message: Message):

    if not is_admin(message.from_user.id):
        await message.answer("❌ Access denied.")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Users",
                    callback_data="admin_users"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Requests",
                    callback_data="admin_requests"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Statistics",
                    callback_data="admin_stats"
                )
            ]
        ]
    )

    await message.answer(
        "👑 <b>Admin Panel</b>\n\n"
        "Select an option:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


async def admin_stats(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Access denied.",
            show_alert=True
        )
        return

    con = connect()
    cur = con.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM users"
    )
    users = cur.fetchone()[0]

    cur.execute(
        "SELECT COALESCE(SUM(balance),0) FROM users"
    )
    balance = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM transactions"
    )
    transactions = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM requests
        WHERE status='pending'
    """)
    pending = cur.fetchone()[0]

    con.close()

    await callback.message.edit_text(
        f"📊 <b>Statistics</b>\n\n"
        f"👥 Users: {users}\n"
        f"💰 Total Balance: ₹{balance:.2f}\n"
        f"🧾 Transactions: {transactions}\n"
        f"⏳ Pending Requests: {pending}",
        parse_mode="HTML"
    )

    await callback.answer()


async def admin_users(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Access denied.",
            show_alert=True
        )
        return

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT user_id, first_name, account_no, balance, frozen
        FROM users
        ORDER BY created_at DESC
        LIMIT 20
    """)

    rows = cur.fetchall()

    con.close()

    if not rows:

        await callback.message.edit_text(
            "👥 No users."
        )

        return

    text = "👥 <b>Users</b>\n\n"

    for row in rows:

        status = "🔴" if row[4] else "🟢"

        text += (
            f"{status} {row[1]}\n"
            f"ID: <code>{row[0]}</code>\n"
            f"Account: <code>{row[2]}</code>\n"
            f"Balance: ₹{row[3]:.2f}\n\n"
        )

    await callback.message.edit_text(
        text,
        parse_mode="HTML"
    )

    await callback.answer()


async def admin_requests(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Access denied.",
            show_alert=True
        )
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

        await callback.message.edit_text(
            "📋 No pending requests."
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

        await callback.message.answer(
            f"📋 <b>Request #{row[0]}</b>\n\n"
            f"User: <code>{row[1]}</code>\n"
            f"Type: {row[2]}\n"
            f"Amount: ₹{row[3]:.2f}\n"
            f"Date: {row[4]}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    await callback.answer()


async def approve(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
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

    if not request or request[3] != "pending":

        con.close()

        await callback.answer(
            "Request already processed.",
            show_alert=True
        )

        return

    user_id = request[0]
    request_type = request[1]
    amount = request[2]

    if request_type == "DEPOSIT":

        update_balance(
            user_id,
            amount
        )

        txid = add_transaction(
            user_id,
            "DEPOSIT",
            amount,
            "Admin approved deposit"
        )

    elif request_type == "WITHDRAW":

        user = get_user(user_id)

        if not user or user[4] < amount:

            con.close()

            await callback.answer(
                "Insufficient balance.",
                show_alert=True
            )

            return

        update_balance(
            user_id,
            -amount
        )

        txid = add_transaction(
            user_id,
            "WITHDRAW",
            amount,
            "Admin approved withdrawal"
        )

    else:

        con.close()

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
        "✅ Approved"
    )


async def reject(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
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
        UPDATE requests
        SET status='rejected'
        WHERE id=?
        AND status='pending'
    """, (
        request_id,
    ))

    con.commit()
    con.close()

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.answer(
        "❌ Rejected"
    )


def register_admin_handlers(dp):

    dp.message.register(
        admin_panel,
        Command("admin")
    )

    dp.callback_query.register(
        admin_users,
        F.data == "admin_users"
    )

    dp.callback_query.register(
        admin_requests,
        F.data == "admin_requests"
    )

    dp.callback_query.register(
        admin_stats,
        F.data == "admin_stats"
    )

    dp.callback_query.register(
        approve,
        F.data.startswith("approve:")
    )

    dp.callback_query.register(
        reject,
        F.data.startswith("reject:")
    )
