from __future__ import annotations

import re

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")
EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_username(username: str) -> bool:
    return bool(USERNAME_RE.match(username))


def validate_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email))