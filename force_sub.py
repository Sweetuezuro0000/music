from aiogram import F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.enums import ChatMemberStatus


GROUP = "@sweetu_friends_group"


def subscribe_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="👥 Join Group",
                    url="https://t.me/sweetu_friends_group"
                )
            ],

            [
                InlineKeyboardButton(
                    text="✅ I've Joined",
                    callback_data="check_subscription"
                )
            ]

        ]
    )


async def check_subscription(bot, user_id):

    try:

        member = await bot.get_chat_member(
            chat_id=GROUP,
            user_id=user_id
        )

        print(
            f"SUB CHECK | user={user_id} "
            f"| status={member.status}"
        )

        return member.status in [
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR
        ]

    except Exception as e:

        print(
            f"SUB CHECK ERROR | user={user_id} | {e}"
        )

        return False


async def subscription_required(message):

    await message.answer(

        "🔒 <b>JOIN REQUIRED</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "Welcome to <b>MyBank</b> 🏦\n\n"

        "To continue, first join our official group:\n\n"

        "👥 <b>@sweetu_friends_group</b>\n\n"

        "After joining, press "
        "<b>I've Joined</b> below.",

        reply_markup=subscribe_keyboard(),

        parse_mode="HTML"
    )


async def check_subscription_callback(
    callback: CallbackQuery
):

    joined = await check_subscription(
        callback.bot,
        callback.from_user.id
    )

    if not joined:

        await callback.answer(
            "❌ You haven't joined the group yet.",
            show_alert=True
        )

        return

    await callback.message.edit_text(

        "✅ <b>MEMBERSHIP VERIFIED</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "You can now access your MyBank account.",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[

                [
                    InlineKeyboardButton(
                        text="🏦 Open MyBank",
                        callback_data="user_home"
                    )
                ]

            ]
        ),

        parse_mode="HTML"
    )

    await callback.answer(
        "✅ Verified!"
    )


def register_force_sub_handlers(dp):

    dp.callback_query.register(
        check_subscription_callback,
        F.data == "check_subscription"
    )
