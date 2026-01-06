import os

JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-by-me")
JWT_ALGO = "HS256"
ACCESS_TOKEN_EXP_MIN = 15
REFRESH_TOKEN_EXP_DAYS = 7
