"""
使用 Fernet 对称加密存储 SSH 密码与私钥。
优先读取 settings.SERVER_LOGS_FERNET_KEY（44 字符 url-safe base64）；
未设置时由 Django SECRET_KEY 派生 32 字节密钥（开发环境可用，生产建议独立密钥）。
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet_from_secret_key() -> Fernet:
    digest = hashlib.sha256(str(settings.SECRET_KEY).encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def get_credentials_fernet() -> Fernet:
    raw = (getattr(settings, "SERVER_LOGS_FERNET_KEY", None) or "").strip()
    if raw:
        return Fernet(raw.encode("ascii"))
    return _fernet_from_secret_key()


def encrypt_secret(plain: str) -> str:
    if plain is None or plain == "":
        return ""
    token = get_credentials_fernet().encrypt(plain.encode("utf-8"))
    return token.decode("ascii")


def decrypt_secret(ciphertext: str) -> str:
    if not (ciphertext or "").strip():
        return ""
    try:
        return (
            get_credentials_fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
        )
    except InvalidToken:
        return ""
