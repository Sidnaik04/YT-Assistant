from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yt_dlp  # type: ignore
import os
from app.services.llm import chunk_text, summarize_with_gemini

app = FastAPI(title="YT Assistant", version="0.1")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


class VideoRequest(BaseModel):
    url: str


@app.post("/download")
def download_video(req: VideoRequest):
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
def summarize_video(req: VideoRequest):
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

        chunks = chunk_text(transcript_text, max_tokens=2000)
        summaries = [summarize_with_gemini(chunk) for chunk in chunks]
        merged = " ".join(summaries)
        final_summary = summarize_with_gemini(merged)

        return {
            "status": "success",
            "video_id": info.get("id"),
            "title": info.get("title"),
            "summary": final_summary,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Summarization failed: {str(e)}")


@app.get("/health")
def health():
    return {"status": "ok", "service": "YT Assistant"}
