"""RSA 密钥服务。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import generate_rsa_keypair
from app.models.rsa_keys import RSAKey


def get_or_create_rsa_key(db: Session) -> RSAKey:
    """查 rsa_keys 表第一行；无则生成并存。返回 RSAKey ORM。"""
    key = db.query(RSAKey).first()
    if key:
        return key

    public_pem, private_pem = generate_rsa_keypair()
    key = RSAKey(public_key_pem=public_pem, private_key_pem=private_pem)
    db.add(key)
    db.commit()
    db.refresh(key)
    return key
