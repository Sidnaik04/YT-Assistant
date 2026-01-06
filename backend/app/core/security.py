import uuid
import jwt
import bcrypt
from datetime import datetime, timedelta, UTC
from app.core.config import (
    JWT_SECRET,
    JWT_ALGO,
    ACCESS_TOKEN_EXP_MIN,
    REFRESH_TOKEN_EXP_DAYS,
)
from app.core.redis_client import redis_client


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(user_id: int):
    jti = str(uuid.uuid4())
    payload = {
        "user_id": user_id,
        "exp": datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXP_MIN),
        "iat": datetime.now(UTC),
        "jti": jti,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


# store token jti in redis untill it  naturally expires
def blacklist_token(token_jti: str, exp_seconds: int):
    redis_client.setex(f"jwt:blacklist:{token_jti}", exp_seconds, "1")


def is_token_blacklisted(token_jti: str):
    return redis_client.exists(f"jwt:blacklist:{token_jti}")


def create_refresh_token(user_id: int):
    payload = {
        "user_id": user_id,
        "exp": datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXP_DAYS),
        "iat": datetime.now(UTC),
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decode_token(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        return "expired"
    except:
        return None
