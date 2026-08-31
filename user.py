from aiogram import F
from aiogram.types import CallbackQuery

from database import get_user


async def show_balance(callback: CallbackQuery):

    user = get_user(callback.from_user.id)

    if not user:
        await callback.answer(
            "Use /start first.",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        f"💰 <b>Your Balance</b>\n\n"
        f"₹{user[4]:.2f}\n\n"
        f"🔢 Account: <code>{user[3]}</code>",
        parse_mode="HTML"
    )

    await callback.answer()


async def show_profile(callback: CallbackQuery):

    user = get_user(callback.from_user.id)

    if not user:
        await callback.answer(
            "Use /start first.",
            show_alert=True
        )
        return

    status = "🔴 Frozen" if user[6] else "🟢 Active"

    await callback.message.edit_text(
        f"👤 <b>Profile</b>\n\n"
        f"Name: {user[2]}\n"
        f"Username: @{user[1] or 'None'}\n"
        f"Account: <code>{user[3]}</code>\n"
        f"Balance: ₹{user[4]:.2f}\n"
        f"Status: {status}\n"
        f"Created: {user[7]}",
        parse_mode="HTML"
    )

    await callback.answer()


def register_user_handlers(dp):

    dp.callback_query.register(
        show_balance,
        F.data == "balance"
    )

    dp.callback_query.register(
        show_profile,
        F.data == "profile"
    )
