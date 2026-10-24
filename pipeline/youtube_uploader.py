"""
YouTube Data API v3 Video Uploader for Cinema X-Ray
Handles OAuth 2.0 authentication, token caching, chunked resumable video uploads,
and metadata tagging (title, description, tags, category, privacy, scheduling).
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime, timezone
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]

REPO_ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_DIR = REPO_ROOT / "credentials"
DEFAULT_CLIENT_SECRETS = CREDENTIALS_DIR / "client_secrets.json"
DEFAULT_TOKEN_FILE = CREDENTIALS_DIR / "token.json"


def get_youtube_service(client_secret_path=None, token_path=None):
    """
    Authenticate and return an authorized YouTube Data API service.
    Re-uses token.json if valid; refreshes if expired; launches browser OAuth if needed.
    """
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    
    client_secret_path = Path(client_secret_path or DEFAULT_CLIENT_SECRETS)
    token_path = Path(token_path or DEFAULT_TOKEN_FILE)

    creds = None

    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception as e:
            print(f"[YouTube Auth] Warning: could not load existing token: {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("[YouTube Auth] Access token expired, refreshing with refresh_token...")
                creds.refresh(Request())
                print("[YouTube Auth] Token refreshed successfully.")
            except Exception as e:
                print(f"[YouTube Auth] Token refresh failed ({e}). Re-authenticating...")
                creds = None

        if not creds or not creds.valid:
            if not client_secret_path.exists():
                raise FileNotFoundError(
                    f"\n[YouTube Auth Error] client_secrets.json not found at:\n  {client_secret_path}\n"
                    f"Please place your Google OAuth client secret JSON file there."
                )

            print("\n[YouTube Auth] Opening browser for one-time YouTube Channel authorization...")
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
            creds = flow.run_local_server(port=0, prompt="consent")

            with open(token_path, "w") as token_file:
                token_file.write(creds.to_json())
            print(f"[YouTube Auth] Authorized credentials saved to: {token_path}")

    service = build("youtube", "v3", credentials=creds)
    return service


def get_channel_info(service):
    """Fetch and display connected YouTube channel info."""
    try:
        response = service.channels().list(mine=True, part="snippet,statistics").execute()
        items = response.get("items", [])
        if items:
            channel = items[0]
            title = channel["snippet"]["title"]
            channel_id = channel["id"]
            subscribers = channel["statistics"].get("subscriberCount", "Hidden")
            return {
                "title": title,
                "id": channel_id,
                "subscribers": subscribers,
                "url": f"https://www.youtube.com/channel/{channel_id}"
            }
    except Exception as e:
        print(f"[YouTube Auth] Could not fetch channel info: {e}")
    return None


def upload_video(
    file_path,
    title,
    description="",
    tags=None,
    category_id="1",  # 1 = Film & Animation, 24 = Entertainment
    privacy_status="unlisted",  # 'public', 'unlisted', or 'private'
    publish_at=None,
    client_secret_path=None,
    token_path=None
):
    """
    Uploads a video to YouTube with resumable chunks.
    
    Args:
        file_path (str or Path): Path to the video file (.mp4)
        title (str): Video title (max 100 chars)
        description (str): Video description (max 5000 chars)
        tags (list): List of keyword tags
        category_id (str): YouTube Category ID ('1' for Film & Animation)
        privacy_status (str): 'public', 'unlisted', or 'private'
        publish_at (datetime or str): Scheduled release in ISO 8601 UTC (if scheduling)
    
    Returns:
        dict: {'id': video_id, 'url': video_url, 'status': privacy_status}
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Video file not found: {file_path}")

    service = get_youtube_service(client_secret_path, token_path)
    
    channel_info = get_channel_info(service)
    if channel_info:
        print(f"[YouTube Upload] Connected to Channel: '{channel_info['title']}' ({channel_info['url']})")

    # Format tags
    if tags is None:
        tags = ["Cinema X-Ray", "Movie Explainer", "Marvel", "Shorts", "MCU"]
    elif isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    # Format status body
    status_body = {
        "privacyStatus": privacy_status,
        "selfDeclaredMadeForKids": False
    }

    if publish_at:
        if isinstance(publish_at, datetime):
            utc_dt = publish_at.astimezone(timezone.utc)
            publish_time_iso = utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            publish_time_iso = str(publish_at)
        status_body["publishAt"] = publish_time_iso
        status_body["privacyStatus"] = "private"  # Scheduled videos must be private initially
        print(f"[YouTube Upload] Scheduled for release at: {publish_time_iso}")

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags,
            "categoryId": str(category_id)
        },
        "status": status_body
    }

    # Resumable media file upload with 10MB chunk size
    chunk_size = 10 * 1024 * 1024
    media = MediaFileUpload(str(file_path), chunksize=chunk_size, resumable=True, mimetype="video/mp4")

    print(f"[YouTube Upload] Starting upload for: {file_path.name}")
    print(f"  Title: {title}")
    print(f"  Privacy: {status_body['privacyStatus']}")
    print(f"  Size: {file_path.stat().st_size / (1024*1024):.2f} MB")

    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    retry_count = 0
    max_retries = 5

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                percent = int(status.progress() * 100)
                print(f"[YouTube Upload] Uploading... {percent}%")
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                retry_count += 1
                if retry_count > max_retries:
                    raise
                wait_time = 2 ** retry_count
                print(f"[YouTube Upload] Temporary server error ({e.resp.status}). Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise

    video_id = response.get("id")
    video_url = f"https://youtu.be/{video_id}"
    print(f"\n🎉 Video Successfully Uploaded!")
    print(f"   Video ID:  {video_id}")
    print(f"   Watch URL: {video_url}")
    print(f"   Status:    {status_body['privacyStatus']}\n")

    return {
        "id": video_id,
        "url": video_url,
        "status": status_body["privacyStatus"],
        "channel": channel_info
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cinema X-Ray YouTube Video Uploader")
    parser.add_argument("--auth", action="store_true", help="Authorize YouTube Channel and print connected details")
    parser.add_argument("--file", type=str, help="Path to video file to upload")
    parser.add_argument("--title", type=str, default="Cinema X-Ray Video", help="Title of the video")
    parser.add_argument("--description", type=str, default="Created with Cinema X-Ray automation pipeline.", help="Description")
    parser.add_argument("--privacy", choices=["public", "unlisted", "private"], default="unlisted", help="Privacy status")
    parser.add_argument("--schedule", type=str, default=None, help="Scheduled publish time (e.g. 2026-10-25 15:00:00)")
    args = parser.parse_args()

    if args.auth:
        print("[YouTube Auth] Verifying YouTube API credentials...")
        srv = get_youtube_service()
        ch = get_channel_info(srv)
        if ch:
            print(f"✅ Successfully authenticated!")
            print(f"   Channel Name: {ch['title']}")
            print(f"   Channel ID:   {ch['id']}")
            print(f"   Subscribers:  {ch['subscribers']}")
            print(f"   Channel URL:  {ch['url']}")
        else:
            print("⚠️ Authenticated, but could not retrieve channel profile.")
    elif args.file:
        upload_video(
            file_path=args.file,
            title=args.title,
            description=args.description,
            privacy_status=args.privacy,
            publish_at=args.schedule
        )
    else:
        parser.print_help()
