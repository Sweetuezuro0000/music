from aiogram import F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import get_user


# =========================================================
# USER MAIN MENU
# =========================================================

def user_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[

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
                ),
                InlineKeyboardButton(
                    text="🧾 History",
                    callback_data="transactions"
                )
            ],

            [
                InlineKeyboardButton(
                    text="💳 My Card",
                    callback_data="my_card"
                ),
                InlineKeyboardButton(
                    text="👤 Profile",
                    callback_data="profile"
                )
            ],

            [
                InlineKeyboardButton(
                    text="⚙️ Settings",
                    callback_data="settings"
                )
            ]

        ]
    )


# =========================================================
# BACK BUTTON
# =========================================================

def back_button():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Back",
                    callback_data="user_home"
                )
            ]
        ]
    )


# =========================================================
# HOME
# =========================================================

async def user_home(callback: CallbackQuery):

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

        await callback.message.edit_text(
            "🔒 <b>ACCOUNT FROZEN</b>\n\n"
            "Your account is currently frozen.\n"
            "Please contact support.",
            parse_mode="HTML"
        )

        await callback.answer()

        return

    await callback.message.edit_text(

        f"🏦 <b>MYBANK</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"

        f"👋 Welcome back, <b>{user[2]}</b>\n\n"

        f"💰 <b>AVAILABLE BALANCE</b>\n"
        f"<code>₹ {user[4]:,.2f}</code>\n\n"

        f"🔢 Account\n"
        f"<code>{user[3]}</code>\n\n"

        f"🟢 Account Active\n\n"

        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>QUICK ACTIONS</b>",

        reply_markup=user_menu(),

        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# BALANCE
# =========================================================

async def show_balance(callback: CallbackQuery):

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

    await callback.message.edit_text(

        f"💰 <b>YOUR BALANCE</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"

        f"<code>₹ {user[4]:,.2f}</code>\n\n"

        f"🔢 Account Number\n"
        f"<code>{user[3]}</code>\n\n"

        f"🟢 Available Balance\n"
        f"💳 Ready to use",

        reply_markup=back_button(),

        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# PROFILE
# =========================================================

async def show_profile(callback: CallbackQuery):

    user = get_user(
        callback.from_user.id
    )

    if not user:

        await callback.answer(
            "Use /start first.",
            show_alert=True
        )

        return

    status = "🔴 Frozen" if user[6] else "🟢 Active"

    username = (
        f"@{user[1]}"
        if user[1]
        else "Not set"
    )

    await callback.message.edit_text(

        f"👤 <b>MY PROFILE</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"

        f"👤 Name\n"
        f"<b>{user[2]}</b>\n\n"

        f"📱 Username\n"
        f"{username}\n\n"

        f"🆔 Telegram ID\n"
        f"<code>{user[0]}</code>\n\n"

        f"🔢 Account Number\n"
        f"<code>{user[3]}</code>\n\n"

        f"💰 Balance\n"
        f"<code>₹ {user[4]:,.2f}</code>\n\n"

        f"📌 Status\n"
        f"{status}\n\n"

        f"📅 Joined\n"
        f"{user[7]}",

        reply_markup=back_button(),

        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# CARD PLACEHOLDER
# =========================================================

async def show_card(callback: CallbackQuery):

    user = get_user(
        callback.from_user.id
    )

    if not user:

        await callback.answer(
            "Use /start first.",
            show_alert=True
        )

        return

    await callback.message.edit_text(

        "💳 <b>MY CARD</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "┌────────────────────┐\n"
        "│                    │\n"
        "│      🏦 MYBANK     │\n"
        "│                    │\n"
        "│  •••• •••• ••••    │\n"
        "│  1024              │\n"
        "│                    │\n"
        "│  CARD HOLDER       │\n"
        "│  "
        f"{user[2].upper()}"
        "│\n"
        "└────────────────────┘\n\n"

        "🔒 Card details are protected.\n\n"
        "Virtual card features will be added here.",

        reply_markup=back_button(),

        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# SETTINGS
# =========================================================

async def show_settings(callback: CallbackQuery):

    await callback.message.edit_text(

        "⚙️ <b>SETTINGS</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "🔐 Security\n"
        "🔔 Notifications\n"
        "🌐 Language\n"
        "❓ Help & Support\n\n"

        "More settings coming soon.",

        reply_markup=back_button(),

        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# REGISTER
# =========================================================

def register_user_handlers(dp):

    dp.callback_query.register(
        user_home,
        F.data == "user_home"
    )

    dp.callback_query.register(
        show_balance,
        F.data == "balance"
    )

    dp.callback_query.register(
        show_profile,
        F.data == "profile"
    )

    dp.callback_query.register(
        show_card,
        F.data == "my_card"
    )

    dp.callback_query.register(
        show_settings,
        F.data == "settings"
    )
