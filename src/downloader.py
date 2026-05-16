import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytesseract
import requests
import whisper
from PIL import Image
from playwright.sync_api import sync_playwright

VIDEOS_DIR = str(Path(__file__).parent / "videos")

os.makedirs(VIDEOS_DIR, exist_ok=True)

whisper_model = whisper.load_model("small")


def _get_yt_dlp_executable_path():
    """Return the path to the yt-dlp binary, checking PATH then the venv bin directory."""
    return shutil.which("yt-dlp") or os.path.join(os.path.dirname(sys.executable), "yt-dlp")


def _download_with_yt_dlp(url):
    """Attempt to download media from a URL using yt-dlp. Returns (filename, media_type) or None on failure."""
    filename = f"{uuid.uuid4().hex}.mp4"
    output_path = os.path.join(VIDEOS_DIR, filename)
    try:
        subprocess.run(
            [
                _get_yt_dlp_executable_path(),
                "-f",
                "bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best",
                "--merge-output-format",
                "mp4",
                "-o",
                output_path,
                url,
            ],
            check=True,
            capture_output=True,
        )
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return filename, "video"
    except subprocess.CalledProcessError:
        if os.path.exists(output_path):
            os.remove(output_path)
    return None


def _fetch_reddit_post(url):
    """Fetch post title, body text, and any linked image from the Reddit JSON API.

    Returns (filename, media_type, text) where filename/media_type are None if no image was found.
    """
    clean_url = re.sub(r"\?.*$", "", url.rstrip("/"))
    json_url = clean_url + ".json"
    try:
        resp = requests.get(json_url, headers={"User-Agent": "memex/1.0"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        post = data[0]["data"]["children"][0]["data"]

        title = post.get("title", "")
        selftext = post.get("selftext", "")
        text = f"{title}\n\n{selftext}".strip()

        image_url = post.get("url_overridden_by_dest", "")
        if image_url:
            img_resp = requests.get(image_url, timeout=15)
            img_resp.raise_for_status()
            content_type = img_resp.headers.get("Content-Type", "")
            if content_type.startswith("image/"):
                ext = "." + content_type.split("/")[1].split(";")[0]
                filename = f"{uuid.uuid4().hex}{ext}"
                with open(os.path.join(VIDEOS_DIR, filename), "wb") as f:
                    f.write(img_resp.content)
                return filename, "image", text

        return None, None, text
    except Exception:
        return None, None, None


def _capture_page_screenshot(url):
    """Take a full-viewport screenshot of the given URL using a headless Chromium browser.

    Returns (filename, media_type) or (None, None) if the screenshot is empty.
    """
    filename = f"{uuid.uuid4().hex}.png"
    output_path = os.path.join(VIDEOS_DIR, filename)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            page.screenshot(path=output_path, full_page=False)
            browser.close()
    except Exception:
        if os.path.exists(output_path):
            os.remove(output_path)
        return None, None
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        return filename, "image"
    return None, None


def _is_reddit_url(url):
    """Return True if the URL points to reddit.com."""
    return bool(re.search(r"reddit\.com/", url))


def download_media(url):
    """Download media from a URL using a cascade of strategies.

    Tries yt-dlp first, then platform-specific extraction (Reddit), then falls
    back to a Playwright screenshot. Returns (filename, media_type, extra_text).
    Raises RuntimeError if all strategies fail.
    """
    result = _download_with_yt_dlp(url)
    if result:
        return result[0], result[1], None

    extra_text = None
    if _is_reddit_url(url):
        filename, media_type, text = _fetch_reddit_post(url)
        extra_text = text
        if filename:
            return filename, media_type, extra_text

    filename, media_type = _capture_page_screenshot(url)
    if filename:
        return filename, media_type, extra_text

    raise RuntimeError(f"Could not download or capture: {url}")


def save_uploaded_file(file_bytes, original_filename, content_type=""):
    """Save raw uploaded file bytes to the media directory with a unique filename.

    Returns (filename, media_type).
    """
    ext = os.path.splitext(original_filename)[1].lower() or ".mp4"
    filename = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(VIDEOS_DIR, filename), "wb") as f:
        f.write(file_bytes)
    media_type = "image" if content_type.startswith("image/") else "video"
    return filename, media_type


def extract_text_from_media(filename, media_type):
    """Extract searchable text from a media file.

    Uses Tesseract OCR for images and Whisper transcription for video/audio.
    Returns an empty string if extraction fails.
    """
    filepath = os.path.join(VIDEOS_DIR, filename)
    try:
        if media_type == "image":
            img = Image.open(filepath)
            return pytesseract.image_to_string(img).strip()
        else:
            result = whisper_model.transcribe(filepath)
            return str(result["text"]).strip()
    except Exception:
        return ""
