import os
import sys
import sqlite3
import time

from flask import jsonify

from app import app

START_TIME = time.time()


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "version": os.environ.get("APP_VERSION", "1.2.3-dev"),
        "debug": app.config.get("DEBUG", False),
        "python": sys.version,
        "db_url": os.environ.get("DATABASE_URL", "sqlite:///users.db"),
        "uptime_seconds": int(time.time() - START_TIME),
    })


@app.route("/health/db")
def db_health():
    db = sqlite3.connect("users.db")
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    counts = {}
    for (table,) in tables:
        counts[table] = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    return jsonify({"tables": counts})
