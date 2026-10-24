"""
Cinema X-Ray Automated YouTube Comment & Community Engagement Engine
Compiles high-retention pinned discussion comments, community prompts, and funnel links,
and publishes them to YouTube videos via YouTube Data API v3.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"
COMMENTS_DIR = REPO_ROOT / "output" / "comments"

# Scope required to write and manage comments on the authenticated channel
COMMENT_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

DEFAULT_COMMENTS = {
    "WYLuP9AZMR8": (
        "📌 PINNED BY CINEMA X-RAY:\n"
        "Thor's smile in Age of Ultron proves he felt Mjolnir move. Did Cap intentionally pretend he couldn't lift it to spare Thor's ego, or did he only truly become worthy when he was willing to stand alone against Thanos in Endgame?\n\n"
        "Drop your theory below! 👇\n"
        "▶️ Subscribe to Cinema X-Ray for daily microscopic movie breakdowns."
    ),
    "aXdAAPRFBuk": (
        "📌 PINNED BY CINEMA X-RAY:\n"
        "Notice that Tony's Mark 50 never had an external helmet latch—it completely dissolved his clothes and sealed his skin in raw carbon within 0.4 seconds. Was the Mark 50 his greatest technological triumph, or the physical manifestation of his battle PTSD?\n\n"
        "What detail in Infinity War did you notice first? 👇\n"
        "▶️ Subscribe to Cinema X-Ray for frame-by-frame film analysis."
    ),
    "BtdcHe1b2kY": (
        "📌 PINNED BY CINEMA X-RAY:\n"
        "In game theory, it's called backward induction: Strange surrendered the Time Stone not in defeat, but because Tony Stark was the ONLY human mind in the cosmos capable of inventing the Quantum GPS.\n\n"
        "Did Strange know Tony would have to sacrifice himself from the very beginning? Share your thoughts below! 👇\n"
        "▶️ Subscribe to Cinema X-Ray for deeper cinema deconstructions."
    ),
    "-CyX_dY0xjE": (
        "📌 PINNED BY CINEMA X-RAY:\n"
        "Every single acoustic tick in Hans Zimmer's soundtrack is spaced precisely 1.25 seconds apart—and every tick burns an entire Earth day in Gargantua's gravitational field.\n\n"
        "Which Christopher Nolan sound design secret hit you the hardest? Tell us below! 👇\n"
        "▶️ Subscribe to Cinema X-Ray for microscopic movie lore."
    )
}


def get_comment_service(client_secret_path=None, token_path=None):
    """
    Retrieves authorized YouTube service with youtube.force-ssl scope for comments.
    """
    secret_path = Path(client_secret_path) if client_secret_path else CONFIG_DIR / "client_secrets.json"
    tok_path = Path(token_path) if token_path else CONFIG_DIR / "youtube_token.json"

    creds = None
    if tok_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(tok_path), COMMENT_SCOPES)
        except Exception:
            creds = None

    # Check if creds have force-ssl scope
    has_force_ssl = False
    if creds and creds.scopes:
        has_force_ssl = any("force-ssl" in s for s in creds.scopes)

    if not creds or not creds.valid or not has_force_ssl:
        if creds and creds.expired and creds.refresh_token and has_force_ssl:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds or not creds.valid or not has_force_ssl:
            if not secret_path.exists():
                raise FileNotFoundError(f"client_secrets.json not found at: {secret_path}")

            print("\n[YouTube Comments Auth] One-time authorization needed for comment permissions (youtube.force-ssl)...")
            flow = InstalledAppFlow.from_client_secrets_file(str(secret_path), COMMENT_SCOPES)
            creds = flow.run_local_server(port=0, prompt="consent")

            with open(tok_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            print(f"✅ Updated credentials saved with comment permissions: {tok_path}")

    return build("youtube", "v3", credentials=creds)


def generate_curiosity_comment(movie_name: str, topic_summary: str, question: Optional[str] = None) -> str:
    """Formats high-CTR, pinned creator comment copy."""
    q_text = question if question else f"What hidden detail in {movie_name} blew your mind the most?"
    comment = (
        f"📌 PINNED BY CINEMA X-RAY:\n"
        f"{topic_summary}\n\n"
        f"{q_text} Drop your thoughts below! 👇\n"
        f"▶️ Subscribe to Cinema X-Ray for microscopic movie breakdowns and visual essays."
    )
    return comment


def post_top_level_comment(video_id: str, comment_text: str, service=None) -> Dict[str, Any]:
    """
    Publishes a top-level creator comment on a YouTube video.
    
    Args:
        video_id (str): 11-character YouTube video ID.
        comment_text (str): Full text of the comment.
        service (optional): Authorized googleapiclient service.
    
    Returns:
        dict: Comment ID, publication status, and video ID.
    """
    COMMENTS_DIR.mkdir(parents=True, exist_ok=True)
    if not service:
        service = get_comment_service()

    body = {
        "snippet": {
            "videoId": video_id,
            "topLevelComment": {
                "snippet": {
                    "textOriginal": comment_text
                }
            }
        }
    }

    print(f"\n💬 Posting Creator Highlight Comment on video: {video_id}...")
    request = service.commentThreads().insert(part="snippet", body=body)
    res = request.execute()

    comment_id = res.get("id")
    pub_at = res.get("snippet", {}).get("topLevelComment", {}).get("snippet", {}).get("publishedAt")
    print(f"✅ Comment posted successfully! Comment Thread ID: {comment_id}")

    # Record on disk
    record = {
        "video_id": video_id,
        "comment_id": comment_id,
        "published_at": pub_at,
        "text": comment_text
    }
    rec_file = COMMENTS_DIR / f"{video_id}_comment.json"
    with open(rec_file, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    return record


def post_default_comments():
    """Posts pinned creator comments to all existing uploaded Cinema X-Ray videos."""
    service = get_comment_service()
    results = []
    for vid, text in DEFAULT_COMMENTS.items():
        try:
            r = post_top_level_comment(video_id=vid, comment_text=text, service=service)
            results.append(r)
        except Exception as e:
            print(f"⚠️ Could not post comment on {vid}: {e}")
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cinema X-Ray Pinned Comment Manager")
    parser.add_argument("--auth", action="store_true", help="Authorize YouTube comment permissions")
    parser.add_argument("--video-id", type=str, help="YouTube video ID to comment on")
    parser.add_argument("--text", type=str, help="Comment text")
    parser.add_argument("--all-existing", action="store_true", help="Post highlight comments to all uploaded videos")
    args = parser.parse_args()

    if args.auth:
        srv = get_comment_service()
        print("✅ YouTube comment authorization verified successfully!")
    elif args.video_id and args.text:
        post_top_level_comment(args.video_id, args.text)
    elif args.all_existing:
        post_default_comments()
    else:
        parser.print_help()
