from aiogram import F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import get_user


# =========================================================
# USER MAIN MENU
# =========================================================

def user_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            # Row 1
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

            # Row 2
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

            # Row 3
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

            # Row 4
            [
                InlineKeyboardButton(
                    text="🔐 Security",
                    callback_data="security"
                ),
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

    # Frozen account
    if user[6] == 1:

        await callback.message.edit_text(
            "🔒 <b>ACCOUNT FROZEN</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Your account is currently frozen.\n\n"
            "Please contact support for assistance.",
            parse_mode="HTML"
        )

        await callback.answer()

        return

    await callback.message.edit_text(

        f"🏦 <b>MYBANK</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"

        f"👋 Welcome back,\n"
        f"<b>{user[2]}</b>\n\n"

        f"💰 <b>AVAILABLE BALANCE</b>\n\n"
        f"<code>₹ {user[4]:,.2f}</code>\n\n"

        f"🔢 Account Number\n"
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

        "💰 <b>YOUR BALANCE</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"<code>₹ {user[4]:,.2f}</code>\n\n"

        "🔢 Account Number\n"
        f"<code>{user[3]}</code>\n\n"

        "🟢 Available Balance\n"
        "💳 Ready to use",

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

    status = (
        "🔴 Frozen"
        if user[6]
        else "🟢 Active"
    )

    username = (
        f"@{user[1]}"
        if user[1]
        else "Not set"
    )

    await callback.message.edit_text(

        "👤 <b>MY PROFILE</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

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
# CARD
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

    if user[6] == 1:

        await callback.answer(
            "🔒 Account frozen.",
            show_alert=True
        )

        return

    name = (
        user[2]
        .upper()
        if user[2]
        else "CARD HOLDER"
    )

    await callback.message.edit_text(

        "💳 <b>MY CARD</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "┌────────────────────────┐\n"
        "│                        │\n"
        "│       🏦 MYBANK        │\n"
        "│                        │\n"
        "│   ••••  ••••  ••••     │\n"
        "│              1024      │\n"
        "│                        │\n"
        "│   CARD HOLDER          │\n"
        f"│   {name:<22}│\n"
        "│                        │\n"
        "└────────────────────────┘\n\n"

        "🔒 Card details are protected.\n\n"
        "💳 Virtual card features will be available here.",

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

        "Manage your account preferences.\n\n"

        "🔐 Security\n"
        "🔔 Notifications\n"
        "🌐 Language\n"
        "❓ Help & Support\n\n"

        "Select an option from the menu.",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[

                [
                    InlineKeyboardButton(
                        text="🔐 Security",
                        callback_data="security"
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="🔔 Notifications",
                        callback_data="notifications"
                    )
                ],

                [
                    InlineKeyboardButton(
                        text="❓ Help & Support",
                        callback_data="support"
                    )
                ],

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


# =========================================================
# REGISTER
# =========================================================

def register_user_handlers(dp):

    # Home
    dp.callback_query.register(
        user_home,
        F.data == "user_home"
    )

    # Balance
    dp.callback_query.register(
        show_balance,
        F.data == "balance"
    )

    # Profile
    dp.callback_query.register(
        show_profile,
        F.data == "profile"
    )

    # Card
    dp.callback_query.register(
        show_card,
        F.data == "my_card"
    )

    # Settings
    dp.callback_query.register(
        show_settings,
        F.data == "settings"
    )
