from aiogram import F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from config import ADMIN_ID
from database import (
    connect,
    get_user,
    update_balance,
    set_frozen,
    add_transaction
)


# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin(user_id):
    return user_id == ADMIN_ID


# =========================================================
# MAIN ADMIN KEYBOARD
# =========================================================

def admin_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="👥 Users",
                    callback_data="admin_users"
                ),
                InlineKeyboardButton(
                    text="📋 Requests",
                    callback_data="admin_requests"
                )
            ],

            [
                InlineKeyboardButton(
                    text="📊 Statistics",
                    callback_data="admin_stats"
                ),
                InlineKeyboardButton(
                    text="💰 Balance Tools",
                    callback_data="admin_balance"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🔒 Security",
                    callback_data="admin_security"
                ),
                InlineKeyboardButton(
                    text="⚙️ Settings",
                    callback_data="admin_settings"
                )
            ]

        ]
    )


# =========================================================
# BACK BUTTON
# =========================================================

def back_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="⬅️ Back",
                    callback_data="admin_back"
                )
            ]

        ]
    )


# =========================================================
# ADMIN HOME
# =========================================================

async def admin_panel(message: Message):

    if not is_admin(message.from_user.id):

        await message.answer(
            "❌ <b>Access Denied</b>\n\n"
            "You are not authorized to access the admin panel.",
            parse_mode="HTML"
        )

        return

    await message.answer(

        "👑 <b>ADMIN CONTROL CENTER</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🏦 Welcome back, Admin!\n\n"
        "Manage your virtual bank from the buttons below.\n\n"
        "🔹 Users\n"
        "🔹 Transactions\n"
        "🔹 Requests\n"
        "🔹 Balance\n"
        "🔹 Security\n"
        "🔹 Settings\n\n"
        "━━━━━━━━━━━━━━━━━━",

        reply_markup=admin_keyboard(),

        parse_mode="HTML"
    )


# =========================================================
# BACK TO ADMIN
# =========================================================

async def admin_back(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "Access denied.",
            show_alert=True
        )

        return

    await callback.message.edit_text(

        "👑 <b>ADMIN CONTROL CENTER</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🏦 Welcome back, Admin!\n\n"
        "Select what you want to manage:",
        
        reply_markup=admin_keyboard(),

        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# USERS
# =========================================================

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
        SELECT user_id,
               first_name,
               account_no,
               balance,
               frozen
        FROM users
        ORDER BY created_at DESC
        LIMIT 15
    """)

    rows = cur.fetchall()

    con.close()

    if not rows:

        text = (
            "👥 <b>USER MANAGEMENT</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "No users found."
        )

    else:

        text = (
            "👥 <b>USER MANAGEMENT</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
        )

        for row in rows:

            status = "🔴 Frozen" if row[4] else "🟢 Active"

            text += (
                f"👤 <b>{row[1]}</b>\n"
                f"🆔 ID: <code>{row[0]}</code>\n"
                f"🔢 Account: <code>{row[2]}</code>\n"
                f"💰 Balance: ₹{row[3]:.2f}\n"
                f"📌 Status: {status}\n\n"
            )

    await callback.message.edit_text(

        text,

        reply_markup=back_keyboard(),

        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# REQUESTS
# =========================================================

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
        SELECT id,
               user_id,
               type,
               amount,
               created_at
        FROM requests
        WHERE status='pending'
        ORDER BY id DESC
        LIMIT 20
    """)

    rows = cur.fetchall()

    con.close()

    if not rows:

        text = (
            "📋 <b>PENDING REQUESTS</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "✅ No pending requests."
        )

        await callback.message.edit_text(
            text,
            reply_markup=back_keyboard(),
            parse_mode="HTML"
        )

        await callback.answer()

        return

    text = (
        "📋 <b>PENDING REQUESTS</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )

    keyboard = []

    for row in rows:

        text += (
            f"🧾 <b>Request #{row[0]}</b>\n"
            f"👤 User: <code>{row[1]}</code>\n"
            f"📌 Type: {row[2]}\n"
            f"💰 Amount: ₹{row[3]:.2f}\n"
            f"🕐 {row[4]}\n\n"
        )

        keyboard.append([

            InlineKeyboardButton(
                text=f"✅ Approve #{row[0]}",
                callback_data=f"approve:{row[0]}"
            ),

            InlineKeyboardButton(
                text=f"❌ Reject #{row[0]}",
                callback_data=f"reject:{row[0]}"
            )

        ])

    keyboard.append([

        InlineKeyboardButton(
            text="⬅️ Back",
            callback_data="admin_back"
        )

    ])

    await callback.message.edit_text(

        text,

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard
        ),

        parse_mode="HTML"
    )

    await callback.answer()

# =========================================================
# APPROVE / REJECT REQUESTS
# =========================================================

async def approve_request(callback: CallbackQuery):

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

    # Request check
    cur.execute("""
        SELECT id, user_id, type, amount, status
        FROM requests
        WHERE id=?
    """, (request_id,))

    request = cur.fetchone()

    if not request:

        con.close()

        await callback.answer(
            "❌ Request not found.",
            show_alert=True
        )
        return

    req_id, user_id, req_type, amount, status = request

    if status != "pending":

        con.close()

        await callback.answer(
            f"⚠️ Already {status}.",
            show_alert=True
        )
        return

    # -----------------------------------------------------
    # DEPOSIT APPROVE
    # -----------------------------------------------------

    if req_type == "DEPOSIT":

        cur.execute("""
            UPDATE users
            SET balance = balance + ?
            WHERE user_id=?
        """, (amount, user_id))

        cur.execute("""
            UPDATE requests
            SET status='approved'
            WHERE id=? AND status='pending'
        """, (request_id,))

        # Transaction record
        cur.execute("""
            INSERT INTO transactions
            (
                user_id,
                type,
                amount,
                description,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            "DEPOSIT",
            amount,
            f"Deposit approved #{request_id}",
            __import__("datetime").datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ))

    # -----------------------------------------------------
    # WITHDRAW APPROVE
    # -----------------------------------------------------

    elif req_type == "WITHDRAW":

        cur.execute("""
            UPDATE users
            SET balance = balance - ?
            WHERE user_id=?
              AND balance >= ?
        """, (
            amount,
            user_id,
            amount
        ))

        if cur.rowcount == 0:

            con.rollback()
            con.close()

            await callback.answer(
                "❌ User has insufficient balance.",
                show_alert=True
            )
            return

        cur.execute("""
            UPDATE requests
            SET status='approved'
            WHERE id=? AND status='pending'
        """, (request_id,))

        cur.execute("""
            INSERT INTO transactions
            (
                user_id,
                type,
                amount,
                description,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            "WITHDRAW",
            amount,
            f"Withdrawal approved #{request_id}",
            __import__("datetime").datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ))

    else:

        con.close()

        await callback.answer(
            "❌ Unknown request type.",
            show_alert=True
        )
        return

    con.commit()
    con.close()

    await callback.answer(
        "✅ Request approved!",
        show_alert=True
    )

    # Notify user
    try:

        if req_type == "DEPOSIT":

            await callback.bot.send_message(
                user_id,
                f"✅ <b>DEPOSIT APPROVED</b>\n\n"
                f"💰 Amount: <b>₹{amount:,.2f}</b>\n"
                f"🧾 Request: <code>#{request_id}</code>\n\n"
                f"💳 Amount has been added to your balance.",
                parse_mode="HTML"
            )

        else:

            await callback.bot.send_message(
                user_id,
                f"✅ <b>WITHDRAWAL APPROVED</b>\n\n"
                f"💰 Amount: <b>₹{amount:,.2f}</b>\n"
                f"🧾 Request: <code>#{request_id}</code>",
                parse_mode="HTML"
            )

    except Exception as e:

        print(
            f"User notification failed: {e}"
        )

    # Refresh admin requests
    await admin_requests(callback)


async def reject_request(callback: CallbackQuery):

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
        SELECT id, user_id, type, amount, status
        FROM requests
        WHERE id=?
    """, (request_id,))

    request = cur.fetchone()

    if not request:

        con.close()

        await callback.answer(
            "❌ Request not found.",
            show_alert=True
        )
        return

    req_id, user_id, req_type, amount, status = request

    if status != "pending":

        con.close()

        await callback.answer(
            f"⚠️ Already {status}.",
            show_alert=True
        )
        return

    cur.execute("""
        UPDATE requests
        SET status='rejected'
        WHERE id=? AND status='pending'
    """, (request_id,))

    con.commit()
    con.close()

    await callback.answer(
        "❌ Request rejected.",
        show_alert=True
    )

    # Notify user
    try:

        await callback.bot.send_message(
            user_id,
            f"❌ <b>{req_type} REQUEST REJECTED</b>\n\n"
            f"💰 Amount: <b>₹{amount:,.2f}</b>\n"
            f"🧾 Request: <code>#{request_id}</code>\n\n"
            f"Please contact support if you need help.",
            parse_mode="HTML"
        )

    except Exception as e:

        print(
            f"User notification failed: {e}"
        )

    await admin_requests(callback)


# =========================================================
# STATISTICS
# =========================================================

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

    cur.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE frozen=1
    """)

    frozen = cur.fetchone()[0]

    con.close()

    await callback.message.edit_text(

        "📊 <b>BANK STATISTICS</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"👥 Total Users\n"
        f"   └ {users}\n\n"

        f"💰 Total Balance\n"
        f"   └ ₹{balance:.2f}\n\n"

        f"🧾 Total Transactions\n"
        f"   └ {transactions}\n\n"

        f"📋 Pending Requests\n"
        f"   └ {pending}\n\n"

        f"🔒 Frozen Accounts\n"
        f"   └ {frozen}\n\n"

        "━━━━━━━━━━━━━━━━━━",

        reply_markup=back_keyboard(),

        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# BALANCE TOOLS
# =========================================================

async def admin_balance(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "Access denied.",
            show_alert=True
        )

        return

    await callback.message.edit_text(

        "💰 <b>BALANCE MANAGEMENT</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "Balance tools will be available here.\n\n"

        "➕ Add balance\n"
        "➖ Deduct balance\n"
        "🔎 Search account\n"
        "📄 View balance history",

        reply_markup=back_keyboard(),

        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# SECURITY
# =========================================================

async def admin_security(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "Access denied.",
            show_alert=True
        )

        return

    await callback.message.edit_text(

        "🔒 <b>SECURITY CENTER</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "🛡️ Account protection\n"
        "🔐 PIN system\n"
        "🚫 Freeze suspicious users\n"
        "📋 Security logs\n"
        "⚠️ Fraud controls",

        reply_markup=back_keyboard(),

        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# SETTINGS
# =========================================================

async def admin_settings(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "Access denied.",
            show_alert=True
        )

        return

    await callback.message.edit_text(

        "⚙️ <b>BANK SETTINGS</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "💵 Transaction Fees\n"
        "📈 Daily Limits\n"
        "📅 Monthly Limits\n"
        "💰 Minimum Amount\n"
        "💰 Maximum Amount\n"
        "🔧 Maintenance Mode",

        reply_markup=back_keyboard(),

        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# REGISTER
# =========================================================

def register_admin_handlers(dp):

    dp.message.register(
        admin_panel,
        Command("admin")
    )

    dp.callback_query.register(
        admin_back,
        F.data == "admin_back"
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
        admin_balance,
        F.data == "admin_balance"
    )

    dp.callback_query.register(
        admin_security,
        F.data == "admin_security"
    )

    dp.callback_query.register(
        admin_settings,
        F.data == "admin_settings"
    )
    dp.callback_query.register(
    approve_request,
    F.data.startswith("approve:")
    )

    dp.callback_query.register(
    reject_request,
    F.data.startswith("reject:")
    )
