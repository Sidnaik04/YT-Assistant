from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import yt_dlp  # type: ignore
import os
import time
from app.services.llm import chunk_text, summarize_with_gemini
from app.db.database import engine, Base, get_db
from sqlalchemy.orm import Session
from app.models.user import User
import bcrypt
from app.core.security import (
    create_refresh_token,
    create_access_token,
    hash_password,
    verify_password,
    blacklist_token,
)
from app.core.security_middleware import auth_scheme, jwt_auth
from app.core.redis_client import redis_client

app = FastAPI(title="YT Assistant", version="0.1")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


class VideoRequest(BaseModel):
    url: str


class AuthRequest(BaseModel):
    email: str
    password: str


@app.post("/download")
def download_video(req: VideoRequest, user=Depends(jwt_auth)):
    user_id, jti, exp = user

    try:
        ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=True)

        return {
            "status": "downloaded",
            "video_id": info.get("id"),
            "title": info.get("title"),
            "resolution": info.get("resolution"),
            "filesize": info.get("filesize"),
            "ext": info.get("ext"),
            "path": f"{DOWNLOAD_DIR}/{info.get('id')}.mp4",
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Download Failed: {str(e)}")


@app.post("/transcript")
def get_transcript(req: VideoRequest):
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en"],
            "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s"),
            "quiet": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            video_id = info.get("id")

            ydl.download([req.url])

        subtitle_file = None
        for file in os.listdir(DOWNLOAD_DIR):
            if file.startswith(video_id) and file.endswith(".vtt"):
                subtitle_file = os.path.join(DOWNLOAD_DIR, file)
                break

        if not subtitle_file:
            raise HTTPException(status_code=404, detail="Transcript not found")

        with open(subtitle_file, "r", encoding="utf-8") as f:
            transcript = f.read()

        return {
            "status": "success",
            "video_id": info.get("id"),
            "title": info.get("title"),
            "transcript": transcript[:8000],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Transcript extraction failed: {str(e)}"
        )


@app.post("/summarize")
def summarize_video(req: VideoRequest, user=Depends(jwt_auth)):
    user_id, jti, exp = user

    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en"],
            "quiet": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            video_id = info.get("id")
            ydl.download([req.url])

        subtitle_file = None
        for file in os.listdir(DOWNLOAD_DIR):
            if file.startswith(video_id) and file.endswith(".vtt"):
                subtitle_file = os.path.join(DOWNLOAD_DIR, file)
                break

        if not subtitle_file:
            raise HTTPException(status_code=404, detail="Transcript not found")

        with open(subtitle_file, "r", encoding="utf-8") as f:
            transcript_text = f.read()

        cache_key = f"summary: {info.get('id')}"

        # 1. check cache first
        cached = redis_client.get(cache_key)
        if cached:
            return {
                "status": "success",
                "video_id": info.get("id"),
                "title": info.get("title"),
                "summary": cached,
                "cached": True,
            }

        # 2. if not cached, generate summary
        chunks = chunk_text(transcript_text, max_tokens=2000)
        summaries = [summarize_with_gemini(chunk) for chunk in chunks]
        merged = " ".join(summaries)
        final_summary = summarize_with_gemini(merged)

        # store in cache for 24 hrs
        redis_client.setex(cache_key, 86400, final_summary)

        return {
            "status": "success",
            "video_id": info.get("id"),
            "title": info.get("title"),
            "summary": final_summary,
            "cached": False,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Summarization failed: {str(e)}")


@app.post("/register")
def register(req: AuthRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(400, "User already exists")

    user = User(email=req.email, password=hash_password(req.password))

    db.add(user)
    db.commit()

    return {"status": "registered", "email": req.email}


@app.post("/login")
def login(req: AuthRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password):
        raise HTTPException(404, "Invalid credentials")

    return {
        "access_token": create_access_token(user.id),
        "refresh_tolen": create_refresh_token(user.id),
    }


@app.get("/me")
def me(user_id: int = Depends(jwt_auth)):
    return {"user_id": user_id}


@app.post("/logout")
def logout(user=Depends(jwt_auth)):
    user_id, jti, exp = user
    ttl = int(exp - time.time())
    blacklist_token(jti, ttl)
    return {"status": "logged out", "token_revoked": True}


@app.get("/health")
def health():
    return {"status": "ok", "service": "YT Assistant"}
