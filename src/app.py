import os
from datetime import datetime
from pathlib import Path
from threading import Thread

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import db
import downloader

PUBLIC_DIR = Path(__file__).parent / "public"

app = FastAPI()

db.initialize_database()


@app.get("/")
def serve_home_page():
    """Serve the main single-page application."""
    return FileResponse(PUBLIC_DIR / "index.html")


@app.get("/api/search")
def search_media(q: str = "", offset: int = 0, limit: int = 20):
    """Return a paginated list of media, filtered by query if provided."""
    if q:
        items = db.search_media(q, offset, limit)
    else:
        items = db.get_all_media(offset, limit)
    return [
        {
            "id": item["id"],
            "url": item["url"],
            "tags": item["tags"],
            "transcript": item["transcript"],
            "filename": item["filename"],
            "media_type": item["media_type"],
        }
        for item in items
    ]


@app.post("/api/tags/{media_id}")
def update_tags(media_id: int, tags: str = Form("")):
    """Replace the tags on a media record with the submitted comma-separated string."""
    db.update_media_tags(media_id, tags)
    return {"ok": True}


@app.delete("/api/media/{media_id}")
def delete_media(media_id: int):
    """Delete a media record and its associated file from disk."""
    item = db.get_media_by_id(media_id)
    if item:
        filepath = os.path.join(downloader.VIDEOS_DIR, item["filename"])
        if os.path.exists(filepath):
            os.remove(filepath)
        db.delete_media_record(media_id)
    return {"ok": True}


def _transcribe_and_update(media_id: int, filename: str, media_type: str, extra_text: str = ""):
    """Run transcription in the background and update the transcript field when done."""
    transcript = downloader.extract_text_from_media(filename, media_type)
    if extra_text:
        transcript = f"{extra_text}\n{transcript}".strip() if transcript else extra_text
    db.update_media_transcript(media_id, transcript)


@app.post("/api/add")
def add_media_from_url(url: str = Form(...), tags: str = Form("")):
    """Download media from a URL, insert it immediately, then transcribe in the background."""
    filename, media_type, extra_text = downloader.download_media(url)
    media_id = db.insert_media_record(url, tags, None, filename, media_type, datetime.now().isoformat())
    Thread(target=_transcribe_and_update, args=(media_id, filename, media_type, extra_text or ""), daemon=True).start()
    return {"ok": True}


@app.post("/api/upload")
async def upload_media_file(file: UploadFile = File(...), tags: str = Form("")):
    """Save uploaded file immediately, then transcribe in the background."""
    file_bytes = await file.read()
    filename, media_type = downloader.save_uploaded_file(file_bytes, file.filename, file.content_type or "")
    media_id = db.insert_media_record("", tags, None, filename, media_type, datetime.now().isoformat())
    Thread(target=_transcribe_and_update, args=(media_id, filename, media_type), daemon=True).start()
    return {"ok": True}


app.mount("/static", StaticFiles(directory=PUBLIC_DIR), name="static")
app.mount("/videos", StaticFiles(directory=downloader.VIDEOS_DIR), name="videos")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
