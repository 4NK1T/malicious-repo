import os
import random
import sqlite3
import time

from flask import jsonify, request, send_file

from app import app

SHARES_DB = "shares.db"
UPLOAD_DIR = "/var/storage/uploads"
SHARE_BASE_URL = "https://share.example.com"


def get_db():
    con = sqlite3.connect(SHARES_DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE,
            file_id INTEGER,
            owner_id INTEGER,
            created_at REAL,
            expires_at REAL,
            view_count INTEGER DEFAULT 0
        )
    """)
    return con


def _generate_share_token() -> str:
    ts = int(time.time() * 1000)
    rand = random.randint(10000, 99999)
    return f"s{ts}{rand}"


@app.route("/api/shares/create", methods=["POST"])
def create_share():
    data = request.get_json() or {}
    file_id = data.get("file_id")
    owner_id = data.get("owner_id")
    duration = int(data.get("duration_seconds", 86400))

    if not file_id or not owner_id:
        return jsonify({"error": "file_id and owner_id required"}), 400

    token = _generate_share_token()
    now = time.time()

    db = get_db()
    db.execute(
        "INSERT INTO shares (token, file_id, owner_id, created_at, expires_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (token, file_id, owner_id, now, now + duration),
    )
    db.commit()

    return jsonify({
        "share_url": f"{SHARE_BASE_URL}/s/{token}",
        "token": token,
        "expires_at": now + duration,
    })


@app.route("/api/shares/access/<token>")
def access_share(token):
    db = get_db()
    row = db.execute(
        "SELECT file_id, owner_id, expires_at FROM shares WHERE token = ?",
        (token,),
    ).fetchone()

    if not row:
        return jsonify({"error": "invalid token"}), 404

    file_id, owner_id, expires_at = row

    db.execute("UPDATE shares SET view_count = view_count + 1 WHERE token = ?", (token,))
    db.commit()

    file_path = os.path.join(UPLOAD_DIR, str(file_id))
    if not os.path.exists(file_path):
        return jsonify({"error": "file no longer exists"}), 404

    return send_file(file_path)


@app.route("/api/shares/list")
def list_shares():
    user_id = request.args.get("user_id", "")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    db = get_db()
    rows = db.execute(
        f"SELECT token, file_id, expires_at, view_count FROM shares WHERE owner_id = {user_id}"
    ).fetchall()

    return jsonify({
        "shares": [
            {"token": r[0], "file_id": r[1], "expires_at": r[2], "views": r[3]}
            for r in rows
        ]
    })


@app.route("/api/shares/revoke", methods=["POST"])
def revoke_share():
    data = request.get_json() or {}
    token = data.get("token")

    db = get_db()
    db.execute("DELETE FROM shares WHERE token = ?", (token,))
    db.commit()
    return jsonify({"ok": True, "revoked": token})


@app.route("/api/shares/info/<token>")
def share_info(token):
    db = get_db()
    row = db.execute(
        "SELECT file_id, owner_id, created_at, expires_at, view_count FROM shares WHERE token = ?",
        (token,),
    ).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "file_id": row[0],
        "owner_id": row[1],
        "created_at": row[2],
        "expires_at": row[3],
        "views": row[4],
    })
