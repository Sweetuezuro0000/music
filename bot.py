import asyncio

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from config import BOT_TOKEN
from database import init_db, create_user

from user import (
    register_user_handlers,
    user_menu
)

from transactions import (
    register_transaction_handlers
)

from payments import (
    register_payment_handlers
)

from admin import (
    register_admin_handlers
)
from security import register_security_handlers
from force_sub import check_subscription, subscription_required
# =========================================================
# BOT
# =========================================================

bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):

    user = create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )

    # FORCE SUBSCRIBE
    joined = await check_subscription(
        bot,
        message.from_user.id
    )

    if not joined:

        await subscription_required(
            message
        )

        return

    # FROZEN ACCOUNT
    if user[6] == 1:

        await message.answer(
            "🔒 <b>ACCOUNT FROZEN</b>\n\n"
            "Your account is currently frozen.\n"
            "Please contact support.",
            parse_mode="HTML"
        )

        return

    # NORMAL HOME
    await message.answer(
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
# =========================================================
# REGISTER ALL MODULES
# =========================================================

def register_handlers():

    # User
    register_user_handlers(dp)

    # Transactions
    register_transaction_handlers(dp)

    # Payments
    register_payment_handlers(dp)

    # Admin
    register_admin_handlers(dp)
    register_security_handlers(dp)
    register_force_sub_handlers(dp)
# =========================================================
# MAIN
# =========================================================

async def main():

    # Create database/tables
    init_db()

    # Register handlers
    register_handlers()

    print("🏦 MyBank Bot Started")

    # Start bot
    await dp.start_polling(bot)


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        print(
            "🛑 MyBank Bot Stopped"
        )
