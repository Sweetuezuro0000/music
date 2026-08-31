from aiogram import F
from aiogram.types import CallbackQuery

from database import connect


async def show_transactions(
    callback: CallbackQuery
):

    con = connect()
    cur = con.cursor()

    cur.execute("""
        SELECT type, amount, description, txid, created_at
        FROM transactions
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 10
    """, (
        callback.from_user.id,
    ))

    rows = cur.fetchall()

    con.close()

    if not rows:

        text = (
            "🧾 <b>Transactions</b>\n\n"
            "No transactions yet."
        )

    else:

        text = "🧾 <b>Recent Transactions</b>\n\n"

        for row in rows:

            text += (
                f"• <b>{row[0]}</b>\n"
                f"Amount: ₹{row[1]:.2f}\n"
                f"{row[2]}\n"
                f"ID: <code>{row[3]}</code>\n"
                f"{row[4]}\n\n"
            )

    await callback.message.edit_text(
        text,
        parse_mode="HTML"
    )

    await callback.answer()


def register_transaction_handlers(dp):

    dp.callback_query.register(
        show_transactions,
        F.data == "transactions"
    )
