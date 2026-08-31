import sqlite3
import secrets
from datetime import datetime

DB_NAME = "bank.db"


def connect():
    return sqlite3.connect(DB_NAME)


def init_db():

    con = connect()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            account_no TEXT UNIQUE,
            balance REAL DEFAULT 0,
            pin TEXT,
            frozen INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount REAL,
            description TEXT,
            txid TEXT UNIQUE,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount REAL,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)

    con.commit()
    con.close()


def get_user(user_id):

    con = connect()
    cur = con.cursor()

    cur.execute(
        "SELECT * FROM users WHERE user_id=?",
        (user_id,)
    )

    user = cur.fetchone()

    con.close()

    return user


def get_user_by_account(account_no):

    con = connect()
    cur = con.cursor()

    cur.execute(
        "SELECT * FROM users WHERE account_no=?",
        (account_no,)
    )

    user = cur.fetchone()

    con.close()

    return user


def create_user(user_id, username, first_name):

    if get_user(user_id):
        return get_user(user_id)

    while True:

        account_no = "10" + "".join(
            secrets.choice("0123456789")
            for _ in range(8)
        )

        if not get_user_by_account(account_no):
            break

    con = connect()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO users
        (
            user_id,
            username,
            first_name,
            account_no,
            balance,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        username or "",
        first_name or "",
        account_no,
        0,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    con.commit()
    con.close()

    return get_user(user_id)


def update_balance(user_id, amount):

    con = connect()
    cur = con.cursor()

    cur.execute("""
        UPDATE users
        SET balance = balance + ?
        WHERE user_id=?
    """, (
        amount,
        user_id
    ))

    con.commit()
    con.close()


def set_frozen(user_id, value):

    con = connect()
    cur = con.cursor()

    cur.execute("""
        UPDATE users
        SET frozen=?
        WHERE user_id=?
    """, (
        value,
        user_id
    ))

    con.commit()
    con.close()


def add_transaction(
    user_id,
    tx_type,
    amount,
    description
):

    txid = "TX" + secrets.token_hex(6).upper()

    con = connect()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO transactions
        (
            user_id,
            type,
            amount,
            description,
            txid,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        tx_type,
        amount,
        description,
        txid,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    con.commit()
    con.close()

    return txid
