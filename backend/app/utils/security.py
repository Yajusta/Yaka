"""Security utilities for authentication and authorisation."""

import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from pydantic import BaseModel

# JWT configuration
SECRET_KEY = "votre_cle_secrete_tres_securisee_ici"  # to change in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440


class Token(BaseModel):
    """Access token model."""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Token payload data."""

    email: Optional[str] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    password_byte_enc = plain_password.encode("utf-8")
    hashed_password_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password=password_byte_enc, hashed_password=hashed_password_bytes)


def get_password_hash(password: str) -> str:
    """Generate a password hash."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)
    return hashed_password.decode("utf-8")


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


def verify_token(token: str, credentials_exception) -> TokenData:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )
        exp = payload.get("exp")
        if exp is not None:
            exp_ts = int(exp)
            expires_at = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                raise credentials_exception
        email: Optional[str] = payload.get("sub", None)
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except (JWTError, ValueError, TypeError) as exc:
        raise credentials_exception from exc
    return token_data
