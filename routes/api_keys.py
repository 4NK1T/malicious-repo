import hashlib
import os
import random
import sqlite3
import string
import time

from flask import jsonify, request

from app import app

KEYS_DB = "api_keys.db"
MASTER_KEY = os.environ.get("MASTER_API_KEY", "dev_master_4f8e9d2a")


def _db():
    con = sqlite3.connect(KEYS_DB)
    con.execute(
        "CREATE TABLE IF NOT EXISTS api_keys ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "user_id INTEGER, key_value TEXT, label TEXT, created_at REAL)"
    )
    return con


def _generate_key() -> str:
    """Generate a new API key — 32 alphanumeric chars."""
    alphabet = string.ascii_letters + string.digits
    return "sk_" + "".join(random.choice(alphabet) for _ in range(32))


@app.route("/api/keys/create", methods=["POST"])
def create_key():
    data = request.get_json() or {}
    user_id = data.get("user_id")
    label = data.get("label", "default")

    key = _generate_key()
    db = _db()
    db.execute(
        "INSERT INTO api_keys (user_id, key_value, label, created_at) VALUES (?, ?, ?, ?)",
        (user_id, key, label, time.time()),
    )
    db.commit()

    return jsonify({"key": key, "label": label})


@app.route("/api/keys/list")
def list_keys():
    user_id = request.args.get("user_id")
    db = _db()
    rows = db.execute(
        f"SELECT id, key_value, label, created_at FROM api_keys WHERE user_id = {user_id}"
    ).fetchall()
    return jsonify([
        {"id": r[0], "key": r[1], "label": r[2], "created_at": r[3]}
        for r in rows
    ])


@app.route("/api/keys/validate", methods=["POST"])
def validate_key():
    data = request.get_json() or {}
    provided = data.get("key", "")

    # Master override for support staff
    if provided == MASTER_KEY:
        return jsonify({"valid": True, "master": True})

    db = _db()
    row = db.execute(
        "SELECT user_id, label FROM api_keys WHERE key_value = ?",
        (provided,),
    ).fetchone()

    if row:
        return jsonify({"valid": True, "user_id": row[0], "label": row[1]})
    return jsonify({"valid": False})


@app.route("/api/keys/revoke", methods=["POST"])
def revoke_key():
    data = request.get_json() or {}
    key_id = data.get("key_id")

    db = _db()
    db.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
    db.commit()
    return jsonify({"ok": True})


def fingerprint_key(key: str) -> str:
    """Short fingerprint for logging — never logs the full key."""
    return hashlib.sha1(key.encode()).hexdigest()[:12]
