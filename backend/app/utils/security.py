"""Security utilities for authentication and authorisation."""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from dotenv import load_dotenv
from jose import JWTError, jwt
from pydantic import BaseModel

from ..multi_database import get_effective_board_uid
from ..schemas.user import BCRYPT_MAX_PASSWORD_BYTES

load_dotenv()

# JWT configuration
# Known sample values (the historical placeholder "your_jwt_secret_key_here",
# 24 chars) are all rejected by the minimum length.
JWT_SECRET_MIN_LENGTH = 32
# Below this many distinct characters the secret is trivially guessable
# ("a" * 32, 32 spaces...); `openssl rand -hex 32` yields ~16.
JWT_SECRET_MIN_DISTINCT_CHARS = 8


def load_jwt_secret() -> str:
    """Read JWT_SECRET and reject a missing, too short or trivial value."""
    secret = os.getenv("JWT_SECRET", "")
    if (
        len(secret.strip()) < JWT_SECRET_MIN_LENGTH
        or len(set(secret)) < JWT_SECRET_MIN_DISTINCT_CHARS
    ):
        raise RuntimeError(
            f"JWT_SECRET must be set to a random value of at least "
            f"{JWT_SECRET_MIN_LENGTH} non-blank characters "
            f"(generate one with: openssl rand -hex 32)"
        )
    return secret


# Checked at import time: the application refuses to start without a strong secret
SECRET_KEY = load_jwt_secret()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440


class Token(BaseModel):
    """Access token model."""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Token payload data."""

    email: Optional[str] = None
    # User id, board on which the token was issued and user's token_version
    # at that time (a recreated account with the same email gets a new id)
    uid: Optional[int] = None
    board: Optional[str] = None
    ver: Optional[int] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    password_byte_enc = plain_password.encode("utf-8")
    # bcrypt (>= 5) raises ValueError beyond 72 bytes and no stored hash can
    # match a longer password: reject it instead of failing with a 500
    if len(password_byte_enc) > BCRYPT_MAX_PASSWORD_BYTES:
        return False
    hashed_password_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(
        password=password_byte_enc, hashed_password=hashed_password_bytes
    )


def get_password_hash(password: str) -> str:
    """Generate a password hash."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)
    return hashed_password.decode("utf-8")


# Computed at import, before any request can arrive: a lazy (or cached but
# not thread-safe) value would cost the first unknown-account logins a second
# bcrypt, revealing that the account does not exist.
_DUMMY_PASSWORD_HASH = get_password_hash(secrets.token_urlsafe(16))


def dummy_password_hash() -> str:
    """Hash of a random password.

    Checked against when the account is unknown or inactive so that login takes
    the same time whether or not the account exists.
    """
    return _DUMMY_PASSWORD_HASH


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.setdefault("iat", int(now.timestamp()))
    to_encode["exp"] = int(expire.timestamp())
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_user_access_token(user) -> str:
    """Create a session token bound to the current board and user's token_version."""
    return create_access_token(
        data={
            "sub": user.email,
            "uid": user.id,
            "board": get_effective_board_uid(),
            "ver": user.token_version,
        }
    )


def verify_token(token: str, credentials_exception) -> TokenData:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        email: Optional[str] = payload.get("sub", None)
        if email is None:
            raise credentials_exception
        token_data = TokenData(
            email=email,
            uid=payload.get("uid"),
            board=payload.get("board"),
            ver=payload.get("ver"),
        )
    except (JWTError, ValueError, TypeError) as exc:
        raise credentials_exception from exc
    return token_data
