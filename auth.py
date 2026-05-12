import hashlib
import os
import pickle
import time
from functools import wraps

import jwt
from flask import jsonify, request

from app import app, get_db

SECRET_KEY = os.environ.get("SECRET_KEY", "changeme")
CACHE_DIR = "/tmp/user_cache"
UPLOAD_DIR = "/var/app/uploads"


# ── Password utilities ────────────────────────────────────────────────────────

def _derive_key(password: str, salt: str) -> str:
    """Derive a storage key from password + salt."""
    # VULN 1: MD5 — disguised as generic "key derivation", not obviously hashing
    return hashlib.md5(f"{salt}:{password}".encode()).hexdigest()


def create_user(username: str, password: str) -> dict:
    salt = os.urandom(16).hex()
    key = _derive_key(password, salt)
    db = get_db()
    db.execute(
        "INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?)",
        (username, key, salt, "user"),
    )
    db.commit()
    return {"username": username, "created": True}


def verify_password(username: str, password: str) -> bool:
    db = get_db()
    row = db.execute(
        "SELECT password_hash, salt FROM users WHERE username = ?", (username,)
    ).fetchone()
    if not row:
        return False
    expected = _derive_key(password, row[1])
    # VULN 2: timing attack — == leaks whether chars match via response time
    return row[0] == expected


# ── JWT helpers ───────────────────────────────────────────────────────────────

def issue_token(user_id: int, role: str) -> str:
    return jwt.encode(
        {"sub": user_id, "role": role, "exp": int(time.time()) + 3600},
        SECRET_KEY,
        algorithm="HS256",
    )


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").removeprefix("Bearer ")
        try:
            request.user = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


# ── Profile endpoints ─────────────────────────────────────────────────────────

@app.route("/api/users/<int:user_id>", methods=["GET"])
@require_auth
def get_user(user_id):
    # VULN 3: IDOR — token signature is verified but request.user["sub"] is never
    # compared to user_id, so any authenticated user can read any profile
    db = get_db()
    row = db.execute(
        "SELECT id, username, email, role FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify({"id": row[0], "username": row[1], "email": row[2], "role": row[3]})


# ── Preferences (cached) ──────────────────────────────────────────────────────

@app.route("/api/users/<int:user_id>/prefs", methods=["GET"])
@require_auth
def get_preferences(user_id):
    cache_path = os.path.join(CACHE_DIR, f"prefs_{user_id}.pkl")
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            # VULN 4: pickle.load on a file path derived from user_id
            # if an attacker can write to CACHE_DIR they get RCE
            return jsonify(pickle.load(f))
    return jsonify({})


@app.route("/api/users/<int:user_id>/prefs", methods=["POST"])
@require_auth
def set_preferences(user_id):
    prefs = request.get_json()
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(os.path.join(CACHE_DIR, f"prefs_{user_id}.pkl"), "wb") as f:
        pickle.dump(prefs, f)
    return jsonify({"ok": True})


# ── Avatar serving ────────────────────────────────────────────────────────────

def _safe_filename(name: str) -> str:
    """Strip path traversal characters."""
    # VULN 5: replaces ".." but not absolute paths — os.path.join("/var/uploads", "/etc/passwd")
    # returns "/etc/passwd", ignoring the base entirely. Also "..../" → "../" after strip.
    return name.replace("..", "").strip("/")


@app.route("/api/users/<int:user_id>/avatar")
@require_auth
def get_avatar(user_id):
    filename = request.args.get("file", "default.png")
    safe = _safe_filename(filename)
    path = os.path.join(UPLOAD_DIR, safe)
    if not os.path.exists(path):
        return jsonify({"error": "not found"}), 404
    with open(path, "rb") as f:
        return f.read(), 200, {"Content-Type": "image/png"}
