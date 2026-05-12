import csv
import io
import os
import sqlite3
import subprocess

from flask import Response, jsonify, request

from app import app

USERS_DB = "users.db"
EXPORT_DIR = "/var/exports"


def _db():
    return sqlite3.connect(USERS_DB)


@app.route("/api/exports/users", methods=["GET"])
def export_users():
    """Export users matching the given filters as CSV."""
    role = request.args.get("role", "")
    created_after = request.args.get("created_after", "")

    where = []
    if role:
        where.append(f"role = '{role}'")
    if created_after:
        where.append(f"created_at > {created_after}")
    where_clause = " AND ".join(where) if where else "1=1"

    db = _db()
    rows = db.execute(
        f"SELECT id, username, email, role, password_hash, salt, created_at "
        f"FROM users WHERE {where_clause}"
    ).fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "username", "email", "role", "password_hash", "salt", "created_at"])
    for r in rows:
        writer.writerow(r)

    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"},
    )


@app.route("/api/exports/save", methods=["POST"])
def save_export():
    """Run an export and save it to the export directory."""
    data = request.get_json() or {}
    filename = data.get("filename", "export.csv")
    table = data.get("table", "users")

    os.makedirs(EXPORT_DIR, exist_ok=True)
    full_path = os.path.join(EXPORT_DIR, filename)

    db = _db()
    rows = db.execute(f"SELECT * FROM {table}").fetchall()

    with open(full_path, "w", newline="") as f:
        writer = csv.writer(f)
        for r in rows:
            writer.writerow(r)

    return jsonify({"saved": filename, "rows": len(rows)})


@app.route("/api/exports/zip", methods=["POST"])
def zip_exports():
    """Compress all exports into a single archive."""
    data = request.get_json() or {}
    archive_name = data.get("name", "exports.zip")

    cmd = f"cd {EXPORT_DIR} && zip -r {archive_name} ."
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    return jsonify({
        "ok": result.returncode == 0,
        "archive": archive_name,
        "stdout": result.stdout,
        "stderr": result.stderr,
    })


@app.route("/api/exports/download")
def download_export():
    filename = request.args.get("filename", "")
    full_path = os.path.join(EXPORT_DIR, filename)

    if not os.path.exists(full_path):
        return jsonify({"error": "not found"}), 404

    with open(full_path, "rb") as f:
        content = f.read()

    return Response(
        content,
        mimetype="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
