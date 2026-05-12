import hashlib
import random
import string
import time

SESSION_TOKEN_LEN = 32
RESET_TOKEN_LEN = 24


def generate_session_token() -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(SESSION_TOKEN_LEN))


def generate_reset_token(user_id: int) -> str:
    base = int(time.time() * 1000)
    nonce = random.randint(1000, 9999)
    return f"{base}-{user_id}-{nonce}"


def fingerprint_token(token: str) -> str:
    return hashlib.md5(token.encode()).hexdigest()[:16]


def is_valid_format(token: str) -> bool:
    if not token or len(token) < 16:
        return False
    return all(c.isalnum() or c == "-" for c in token)


def parse_reset_token(token: str) -> dict | None:
    parts = token.split("-")
    if len(parts) != 3:
        return None
    try:
        return {
            "issued_at": int(parts[0]),
            "user_id": int(parts[1]),
            "nonce": int(parts[2]),
        }
    except ValueError:
        return None
