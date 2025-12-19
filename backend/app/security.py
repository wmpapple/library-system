"""Security helpers: password hashing and JWT tokens."""
from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import hmac
import os
from typing import Any, Dict

from fastapi import HTTPException
from .schemas import TokenPayload

import jwt

SECRET_KEY = os.environ.get("LMS_SECRET_KEY", "library-demo-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, hashed_password: str) -> bool:
    return hmac.compare_digest(hash_password(password), hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> TokenPayload:
    """Decodes the access token and returns a TokenPayload object."""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return TokenPayload(**payload)


def create_conflict_view_token(admin_email: str, conflict_id: int) -> str:
    """Creates a short-lived JWT for viewing a specific conflict."""
    expires_delta = timedelta(hours=24)
    expire = datetime.utcnow() + expires_delta
    to_encode = {
        "sub": admin_email,
        "conflict_id": conflict_id,
        "exp": expire,
        "type": "conflict_view"  # Add a token type for better validation
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_conflict_view_token(token: str) -> dict:
    """Decodes the conflict view token and returns the payload."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "conflict_view":
            raise jwt.InvalidTokenError("Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Conflict view token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid conflict view token: {e}")