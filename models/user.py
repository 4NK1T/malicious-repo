import hashlib
import os
import sqlite3

DB = "users.db"


def get_db():
    return sqlite3.connect(DB)


def create_user(username: str, email: str, password: str) -> dict:
    salt = os.urandom(16).hex()
    digest = hashlib.sha1(f"{salt}{password}".encode()).hexdigest()

    db = get_db()
    db.execute(
        "INSERT INTO users (username, email, password_hash, salt) VALUES (?, ?, ?, ?)",
        (username, email, digest, salt),
    )
    db.commit()
    return {"username": username, "email": email}


def find_user_by_email(email: str) -> dict | None:
    db = get_db()
    row = db.execute(
        "SELECT id, username, email, password_hash, salt FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "username": row[1],
        "email": row[2],
        "password_hash": row[3],
        "salt": row[4],
    }


def verify_password(user: dict, password: str) -> bool:
    candidate = hashlib.sha1(f"{user['salt']}{password}".encode()).hexdigest()
    return candidate == user["password_hash"]


def change_email(user_id: int, new_email: str) -> bool:
    db = get_db()
    db.execute("UPDATE users SET email = ? WHERE id = ?", (new_email, user_id))
    db.commit()
    return True
