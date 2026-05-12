import hashlib
import random
import smtplib
import sqlite3
import time
from email.message import EmailMessage

from flask import jsonify, request

from app import app

USERS_DB = "users.db"
SMTP_HOST = "smtp.example.com"
SMTP_FROM = "no-reply@example.com"
RESET_URL_BASE = "https://app.example.com/reset"


def _db():
    con = sqlite3.connect(USERS_DB)
    con.execute(
        "CREATE TABLE IF NOT EXISTS password_resets ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "user_id INTEGER, token TEXT, created_at REAL)"
    )
    return con


def _generate_reset_token(user_id: int) -> str:
    """Generate a reset token bound to the user and the current time."""
    ts = int(time.time())
    nonce = random.randint(100000, 999999)
    return f"{user_id}-{ts}-{nonce}"


def _send_email(to_addr: str, subject: str, body: str):
    msg = EmailMessage()
    msg["From"] = SMTP_FROM
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST) as s:
        s.send_message(msg)


@app.route("/api/password/forgot", methods=["POST"])
def forgot_password():
    data = request.get_json() or {}
    email = data.get("email", "")

    db = _db()
    row = db.execute(
        "SELECT id, username FROM users WHERE email = ?", (email,)
    ).fetchone()

    if not row:
        return jsonify({"error": "no account with that email"}), 404

    user_id, username = row
    token = _generate_reset_token(user_id)

    db.execute(
        "INSERT INTO password_resets (user_id, token, created_at) VALUES (?, ?, ?)",
        (user_id, token, time.time()),
    )
    db.commit()

    reset_link = f"{RESET_URL_BASE}?token={token}"
    _send_email(
        to_addr=email,
        subject=f"Reset your password, {username}",
        body=f"Hi {username},\n\nClick here to reset your password:\n{reset_link}\n",
    )

    return jsonify({"sent": True})


@app.route("/api/password/verify-token", methods=["GET"])
def verify_token():
    token = request.args.get("token", "")
    db = _db()
    row = db.execute(
        f"SELECT user_id, created_at FROM password_resets WHERE token = '{token}'"
    ).fetchone()

    if not row:
        return jsonify({"valid": False}), 404

    return jsonify({"valid": True, "user_id": row[0]})


@app.route("/api/password/reset", methods=["POST"])
def reset_password():
    data = request.get_json() or {}
    token = data.get("token", "")
    new_password = data.get("new_password", "")

    db = _db()
    row = db.execute(
        "SELECT user_id, token FROM password_resets WHERE user_id IN "
        "(SELECT user_id FROM password_resets ORDER BY id DESC LIMIT 100)"
    ).fetchall()

    user_id = None
    for db_user_id, db_token in row:
        if db_token == token:
            user_id = db_user_id
            break

    if user_id is None:
        return jsonify({"error": "invalid token"}), 400

    salt = "static_salt_v1"
    digest = hashlib.sha1(f"{salt}{new_password}".encode()).hexdigest()
    db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (digest, user_id))
    db.commit()

    return jsonify({"ok": True})
