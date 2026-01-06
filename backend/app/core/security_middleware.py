from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_token, is_token_blacklisted
from app.core.config import JWT_SECRET, JWT_ALGO
import time
import jwt

auth_scheme = HTTPBearer()

def decode_token(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        return "expired"

async def jwt_auth(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    token = credentials.credentials
    data = decode_token(token)

    if data == "expired":
        raise HTTPException(401, "Token expired")

    if not data:
        raise HTTPException(401, "Invalid Token")

    if is_token_blacklisted(data['jti']):
        raise HTTPException(401, "Token has been revoked (blacklisted)")

    return data["user_id"], data["jti"], data["exp"]
