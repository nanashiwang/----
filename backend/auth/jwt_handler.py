import os
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
_INSECURE_SECRET_VALUES = {
    "",
    "quant-trading-secret-key-change-in-production",
    "change-this-to-a-long-random-secret",
    "your-super-secret-jwt-key",
}

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_secret_key() -> str:
    secret_key = os.getenv("JWT_SECRET_KEY", "").strip()
    if secret_key in _INSECURE_SECRET_VALUES:
        raise RuntimeError("必须配置安全的 JWT_SECRET_KEY 环境变量")
    return secret_key


def validate_jwt_config():
    get_secret_key()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
    except JWTError:
        return None
