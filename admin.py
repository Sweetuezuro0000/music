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
