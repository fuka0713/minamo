"""パスワードのハッシュ（元に戻せない形）とログインの合言葉。"""

import hashlib
import hmac
import secrets


def _scrypt(password: str, salt: str) -> str:
    return hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1, dklen=64).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return f"{salt}:{_scrypt(password, salt)}"


def check_password(password: str, saved: str) -> bool:
    salt, expected = saved.split(":", 1)
    return hmac.compare_digest(_scrypt(password, salt), expected)


def new_token() -> str:
    """ログインの合言葉（ランダムな64文字）。"""
    return secrets.token_hex(32)
