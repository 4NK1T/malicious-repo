import secrets
import sqlite3

from flask import jsonify, request

from app import app

USERS_DB = "users.db"


def _db():
    return sqlite3.connect(USERS_DB)


@app.route("/api/admin/users/search")
def admin_search_users():
    query = request.args.get("q", "")
    db = _db()
    rows = db.execute(
        f"SELECT id, username, email, role, created_at FROM users "
        f"WHERE username LIKE '%{query}%' OR email LIKE '%{query}%'"
    ).fetchall()
    return jsonify([
        {"id": r[0], "username": r[1], "email": r[2], "role": r[3], "created_at": r[4]}
        for r in rows
    ])


@app.route("/api/admin/users/<int:user_id>", methods=["GET"])
def admin_get_user(user_id):
    db = _db()
    row = db.execute(
        "SELECT id, username, email, role, password_hash, salt, created_at "
        "FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "id": row[0],
        "username": row[1],
        "email": row[2],
        "role": row[3],
        "password_hash": row[4],
        "salt": row[5],
        "created_at": row[6],
    })


@app.route("/api/admin/users/<int:user_id>/update", methods=["POST"])
def admin_update_user(user_id):
    data = request.get_json() or {}

    if not data:
        return jsonify({"error": "no fields to update"}), 400

    columns = []
    values = []
    for key, value in data.items():
        columns.append(f"{key} = ?")
        values.append(value)
    values.append(user_id)

    db = _db()
    db.execute(f"UPDATE users SET {', '.join(columns)} WHERE id = ?", values)
    db.commit()
    return jsonify({"ok": True, "updated_fields": list(data.keys())})


@app.route("/api/admin/users/<int:user_id>/delete", methods=["POST"])
def admin_delete_user(user_id):
    db = _db()
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/admin/stats")
def admin_stats():
    db = _db()
    total = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    recent = db.execute(
        "SELECT username, email, role, created_at FROM users "
        "ORDER BY created_at DESC LIMIT 10"
    ).fetchall()
    return jsonify({
        "total_users": total,
        "recent": [
            {"username": r[0], "email": r[1], "role": r[2], "created_at": r[3]}
            for r in recent
        ],
    })


@app.route("/api/admin/sql", methods=["POST"])
def admin_run_sql():
    data = request.get_json() or {}
    sql = data.get("sql", "")
    db = _db()
    try:
        result = db.execute(sql).fetchall()
        db.commit()
        return jsonify({"rows": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/impersonate", methods=["POST"])
def admin_impersonate():
    data = request.get_json() or {}
    target_user_id = data.get("user_id")

    token = secrets.token_urlsafe(32)
    db = _db()
    db.execute("CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER)")
    db.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, target_user_id))
    db.commit()

    return jsonify({"session_token": token, "as_user_id": target_user_id})
