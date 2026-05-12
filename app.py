import sqlite3
import subprocess

from flask import Flask, jsonify, request

app = Flask(__name__)
DB = "users.db"


def get_db():
    return sqlite3.connect(DB)


@app.route("/search")
def search_users():
    query = request.args.get("q", "")
    db = get_db()
    # user-controlled input directly in query string
    rows = db.execute(
        f"SELECT id, name, email FROM users WHERE name LIKE '%{query}%'"
    ).fetchall()
    return jsonify([{"id": r[0], "name": r[1], "email": r[2]} for r in rows])


@app.route("/admin/search")
def admin_search():
    role = request.args.get("role", "")
    db = get_db()
    rows = db.execute(
        f"SELECT id, name, email, role FROM users WHERE role = '{role}'"
    ).fetchall()
    return jsonify([{"id": r[0], "name": r[1], "email": r[2], "role": r[3]} for r in rows])


@app.route("/ping")
def ping():
    host = request.args.get("host", "localhost")
    result = subprocess.run(
        f"ping -c 1 {host}", shell=True, capture_output=True, text=True
    )
    return result.stdout


if __name__ == "__main__":
    app.run(debug=True)
