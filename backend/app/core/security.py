"""安全工具：RSA、bcrypt、密码规则。"""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from passlib.context import CryptContext

_pwd = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
    bcrypt__truncate_error=False,
)


def generate_rsa_keypair() -> tuple[str, str]:
    """返回 (public_pem, private_pem)，RSA-2048，PKCS8，PEM 文本。"""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    return public_pem, private_pem


def rsa_decrypt(private_pem: str, ciphertext_b64: str) -> str:
    """base64 解码 -> PKCS1v15 解密 -> 返回明文。解密失败抛 ValueError。"""
    try:
        loaded = serialization.load_pem_private_key(private_pem.encode("utf-8"), password=None)
        if not isinstance(loaded, RSAPrivateKey):
            raise ValueError("Not an RSA private key")
        ciphertext = base64.b64decode(ciphertext_b64)
        plaintext = loaded.decrypt(ciphertext, padding.PKCS1v15())
        return plaintext.decode("utf-8")
    except Exception as e:
        raise ValueError(f"RSA decrypt failed: {e}") from e


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def validate_password(plain: str) -> list[str]:
    """返回错误信息列表；空列表表示合法。
    规则：长度 8-128；至少含 数字/字母/符号 中两类。
    """
    errors: list[str] = []
    if len(plain) < 8:
        errors.append("Password must be at least 8 characters")
    if len(plain) > 128:
        errors.append("Password must be at most 128 characters")

    has_digit = any(c.isdigit() for c in plain)
    has_alpha = any(c.isalpha() for c in plain)
    has_symbol = any(not c.isalnum() and c.isprintable() for c in plain)
    category_count = sum([has_digit, has_alpha, has_symbol])
    if category_count < 2:
        errors.append("Password must contain at least 2 of: digits, letters, symbols")

    return errors
