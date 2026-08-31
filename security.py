from aiogram import F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from database import connect, get_user


# =========================================================
# STATES
# =========================================================

class PinSetupState(StatesGroup):
    pin = State()
    confirm = State()


class PinChangeState(StatesGroup):
    old_pin = State()
    new_pin = State()
    confirm = State()


# =========================================================
# KEYBOARDS
# =========================================================

def security_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔐 Set PIN",
                    callback_data="set_pin"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Change PIN",
                    callback_data="change_pin"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Back",
                    callback_data="user_home"
                )
            ]
        ]
    )


def cancel_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="security_cancel"
                )
            ]
        ]
    )


# =========================================================
# SECURITY PAGE
# =========================================================

async def security_page(callback: CallbackQuery):

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

    if user[5]:

        pin_status = "🟢 PIN Active"

    else:

        pin_status = "🔴 PIN Not Set"

    await callback.message.edit_text(

        "🔐 <b>SECURITY CENTER</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"PIN Status\n"
        f"<b>{pin_status}</b>\n\n"

        "Your PIN is required for sensitive "
        "account actions.\n\n"

        "🛡️ Never share your PIN with anyone.",

        reply_markup=security_keyboard(),

        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# SET PIN START
# =========================================================

async def set_pin_start(
    callback: CallbackQuery,
    state: FSMContext
):

    user = get_user(
        callback.from_user.id
    )

    if not user:
        await callback.answer(
            "Account not found.",
            show_alert=True
        )
        return

    if user[5]:

        await callback.answer(
            "PIN already set. Use Change PIN.",
            show_alert=True
        )

        return

    await state.set_state(
        PinSetupState.pin
    )

    await callback.message.edit_text(

        "🔐 <b>SET SECURITY PIN</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "Enter a <b>4-digit PIN</b>.\n\n"

        "Example:\n"
        "<code>2580</code>\n\n"

        "⚠️ Don't share your PIN with anyone.",

        reply_markup=cancel_keyboard(),

        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# SET PIN
# =========================================================

async def set_pin(
    message: Message,
    state: FSMContext
):

    pin = message.text.strip()

    if not pin.isdigit() or len(pin) != 4:

        await message.answer(
            "❌ PIN exactly 4 digits ka hona chahiye.\n\n"
            "Example: <code>2580</code>",
            parse_mode="HTML"
        )

        return

    await state.update_data(
        pin=pin
    )

    await state.set_state(
        PinSetupState.confirm
    )

    await message.answer(
        "🔐 <b>CONFIRM PIN</b>\n\n"
        "Same 4-digit PIN dobara enter karo.",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )


# =========================================================
# CONFIRM PIN
# =========================================================

async def confirm_pin(
    message: Message,
    state: FSMContext
):

    pin = message.text.strip()

    data = await state.get_data()

    if pin != data["pin"]:

        await message.answer(
            "❌ PIN match nahi hua.\n\n"
            "Setup cancelled."
        )

        await state.clear()

        return

    con = connect()
    cur = con.cursor()

    cur.execute("""
        UPDATE users
        SET pin=?
        WHERE user_id=?
    """, (
        pin,
        message.from_user.id
    ))

    con.commit()
    con.close()

    await state.clear()

    await message.answer(
        "✅ <b>PIN SET SUCCESSFULLY</b>\n\n"
        "🔐 Your security PIN is now active.\n\n"
        "⚠️ Never share it with anyone.",
        parse_mode="HTML"
    )


# =========================================================
# CHANGE PIN START
# =========================================================

async def change_pin_start(
    callback: CallbackQuery,
    state: FSMContext
):

    user = get_user(
        callback.from_user.id
    )

    if not user:
        await callback.answer(
            "Account not found.",
            show_alert=True
        )
        return

    if not user[5]:

        await callback.answer(
            "First set your PIN.",
            show_alert=True
        )

        return

    await state.set_state(
        PinChangeState.old_pin
    )

    await callback.message.edit_text(

        "🔄 <b>CHANGE PIN</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "Enter your current PIN:",

        reply_markup=cancel_keyboard(),

        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# OLD PIN
# =========================================================

async def old_pin(
    message: Message,
    state: FSMContext
):

    user = get_user(
        message.from_user.id
    )

    if not user:
        await state.clear()
        return

    if message.text.strip() != user[5]:

        await message.answer(
            "❌ Incorrect current PIN."
        )

        await state.clear()

        return

    await state.set_state(
        PinChangeState.new_pin
    )

    await message.answer(
        "🔐 Enter your new 4-digit PIN:",
        reply_markup=cancel_keyboard()
    )


# =========================================================
# NEW PIN
# =========================================================

async def new_pin(
    message: Message,
    state: FSMContext
):

    pin = message.text.strip()

    if not pin.isdigit() or len(pin) != 4:

        await message.answer(
            "❌ New PIN exactly 4 digits ka hona chahiye."
        )

        return

    await state.update_data(
        new_pin=pin
    )

    await state.set_state(
        PinChangeState.confirm
    )

    await message.answer(
        "🔐 Confirm your new PIN:",
        reply_markup=cancel_keyboard()
    )


# =========================================================
# CONFIRM NEW PIN
# =========================================================

async def confirm_new_pin(
    message: Message,
    state: FSMContext
):

    pin = message.text.strip()

    data = await state.get_data()

    if pin != data["new_pin"]:

        await message.answer(
            "❌ PIN doesn't match.\n\n"
            "Change cancelled."
        )

        await state.clear()

        return

    con = connect()
    cur = con.cursor()

    cur.execute("""
        UPDATE users
        SET pin=?
        WHERE user_id=?
    """, (
        pin,
        message.from_user.id
    ))

    con.commit()
    con.close()

    await state.clear()

    await message.answer(
        "✅ <b>PIN CHANGED</b>\n\n"
        "Your new security PIN is active.",
        parse_mode="HTML"
    )


# =========================================================
# CANCEL
# =========================================================

async def security_cancel(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.clear()

    await callback.message.edit_text(

        "🔐 <b>SECURITY CENTER</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Action cancelled.",

        reply_markup=security_keyboard(),

        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# REGISTER
# =========================================================

def register_security_handlers(dp):

    dp.callback_query.register(
        security_page,
        F.data == "security"
    )

    dp.callback_query.register(
        set_pin_start,
        F.data == "set_pin"
    )

    dp.message.register(
        set_pin,
        PinSetupState.pin
    )

    dp.message.register(
        confirm_pin,
        PinSetupState.confirm
    )

    dp.callback_query.register(
        change_pin_start,
        F.data == "change_pin"
    )

    dp.message.register(
        old_pin,
        PinChangeState.old_pin
    )

    dp.message.register(
        new_pin,
        PinChangeState.new_pin
    )

    dp.message.register(
        confirm_new_pin,
        PinChangeState.confirm
    )

    dp.callback_query.register(
        security_cancel,
        F.data == "security_cancel"
    )
