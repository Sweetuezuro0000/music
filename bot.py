from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import BOT_TOKEN
from database import init_db, create_user, get_user

from user import register_user_handlers
from transactions import register_transaction_handlers
from admin import register_admin_handlers


bot = Bot(BOT_TOKEN)
dp = Dispatcher()


def main_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="💰 Balance",
                    callback_data="balance"
                ),
                InlineKeyboardButton(
                    text="👤 Profile",
                    callback_data="profile"
                )
            ],

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
                )
            ],

            [
                InlineKeyboardButton(
                    text="🧾 Transactions",
                    callback_data="transactions"
                )
            ]
        ]
    )


@dp.message(CommandStart())
async def start(message: Message):

    user = create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )

    if user[6] == 1:

        await message.answer(
            "🚫 Your account is frozen."
        )

        return

    await message.answer(

        f"🏦 <b>MyBank</b>\n\n"
        f"Welcome {message.from_user.first_name} 👋\n\n"
        f"🔢 Account: <code>{user[3]}</code>\n"
        f"💰 Balance: ₹{user[4]:.2f}\n\n"
        f"Select an option:",

        reply_markup=main_menu(),

        parse_mode="HTML"
    )


def register_handlers():

    register_user_handlers(dp)
    register_transaction_handlers(dp)
    register_admin_handlers(dp)


async def main():

    init_db()

    register_handlers()

    print("🏦 MyBank Bot Started")

    await dp.start_polling(bot)


if __name__ == "__main__":

    import asyncio

    asyncio.run(main())
