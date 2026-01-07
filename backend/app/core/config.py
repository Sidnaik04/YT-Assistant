from dotenv import load_dotenv
import os
from pathlib import Path

# load backend/.env (adjust path if config.py moves)
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-by-me")
JWT_ALGO = os.getenv("JWT_ALGO", "HS256")
ACCESS_TOKEN_EXP_MIN = int(os.getenv("ACCESS_TOKEN_EXP_MIN", "15"))
REFRESH_TOKEN_EXP_DAYS = int(os.getenv("REFRESH_TOKEN_EXP_DAYS", "7"))
