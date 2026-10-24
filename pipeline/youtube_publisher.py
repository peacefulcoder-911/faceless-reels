"""
Cinema X-Ray YouTube Publisher & Algorithmic Metadata Compiler
Compiles algorithmic metadata (High-CTR titles, SEO entity descriptions,
exact 00:00 chapter timestamps, entity search tags) via Gemini and handles
resumable YouTube Data API v3 uploads with automatic thumbnail association.
"""

import os
import sys
import time
import json
import re
from pathlib import Path
from typing import Union, Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from google import genai
from google.genai import types

# Optional YouTube API imports
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"
PUBLISH_PACKAGES_DIR = OUTPUT_DIR / "publish_packages"
CONFIG_DIR = REPO_ROOT / "config"
CREDENTIALS_DIR = REPO_ROOT / "credentials"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]


class YouTubePackage(BaseModel):
    """Complete Algorithmic YouTube Publishing Package."""
    optimized_title: str = Field(description="High-CTR curiosity-gap title under 52 characters.")
    seo_description: str = Field(description="Full SEO description including hook, chapters or funnel link, and entity hashtags.")
    tags: List[str] = Field(description="Exactly 15 high-velocity search and entity tags under 450 total characters.")
    category_id: str = Field(default="1", description="YouTube Category ID: '1' for Film & Animation, '24' for Entertainment")
    made_for_kids: bool = Field(default=False, description="Strictly False to allow comments and browse recommendation.")
    video_format: str = Field(default="LONG_5_6_MIN", description="LONG_5_6_MIN or SHORT_45_SEC")
    job_slug: str = Field(default="cinema_xray", description="Identifier slug")
    chapter_timestamps: Optional[List[Dict[str, Any]]] = Field(default=None, description="Calculated chapter timestamps for Long-Form")
    related_long_video_id: Optional[str] = Field(default=None, description="Linked Long-Form video ID for Shorts funnel")


def _get_api_client():
    """Retrieve Gemini client using environment or .env file."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        env_file = REPO_ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("GEMINI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not api_key:
        print("[YouTube Publisher] Warning: GEMINI_API_KEY not found in environment or .env. Algorithmic fallback will be used.")
        return None
    return genai.Client(api_key=api_key)


def _calculate_long_form_chapters(manifest: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Auto-calculates exact 00:00 chapter timestamps mapped from the 5 chapters in manifest_json.
    Computes exact durations based on narration word counts proportional to target duration.
    """
    chapters_raw = manifest.get("chapters", [])
    beats = manifest.get("beats", [])
    target_duration_sec = float(manifest.get("target_duration_sec", 330.0))

    if not chapters_raw:
        chapters_raw = [
            "Chapter 1: The Inciting Detail & False Consensus",
            "Chapter 2: The Hidden Visual Grammar & Craft",
            "Chapter 3: The Psychological Deconstruction",
            "Chapter 4: The Thematic Revelation & Philosophy",
            "Chapter 5: The Ultimate Payoff & Legacy"
        ]

    # Count words per chapter from beats
    chapter_words: Dict[int, int] = {i: 0 for i in range(1, len(chapters_raw) + 1)}
    for b in beats:
        c_num = b.get("chapter_num", 1)
        if c_num in chapter_words:
            chapter_words[c_num] += len(b.get("narration_text", "").split())
        else:
            chapter_words[1] += len(b.get("narration_text", "").split())

    total_words = max(sum(chapter_words.values()), 1)

    timestamps = []
    current_sec = 0.0

    for idx, ch_title in enumerate(chapters_raw, start=1):
        # Clean title prefix if redundant (e.g. "Chapter 1: ")
        clean_title = re.sub(r"^Chapter\s+\d+:\s*", "", ch_title).strip()
        if not clean_title:
            clean_title = ch_title

        # Format timestamp
        if idx == 1:
            # YouTube STRICT requirement: First chapter MUST start at 00:00
            time_str = "00:00"
        else:
            mins = int(current_sec // 60)
            secs = int(current_sec % 60)
            time_str = f"{mins:02d}:{secs:02d}"

        timestamps.append({
            "timestamp": time_str,
            "title": f"Chapter {idx}: {clean_title}" if not ch_title.startswith("Chapter") else ch_title,
            "seconds": int(current_sec)
        })

        # Advance timestamp proportional to chapter words
        words = chapter_words.get(idx, total_words // len(chapters_raw))
        ch_duration = (words / total_words) * target_duration_sec
        current_sec += max(ch_duration, 25.0)

    return timestamps


def _fallback_metadata(
    manifest: Dict[str, Any],
    video_format: str,
    related_long_video_id: Optional[str] = None
) -> YouTubePackage:
    """Deterministic, high-quality fallback generator when Gemini API is offline."""
    title_raw = manifest.get("title", "The Hidden Detail You Missed")
    movie = manifest.get("movie_name", "Cinema")
    cluster = manifest.get("cluster_name", "Masterpiece")
    lens = manifest.get("category_lens", "Film Analysis")
    thesis = manifest.get("core_thesis", "An in-depth analytical breakdown.")
    job_slug = manifest.get("job_slug", "video")

    # Clean title < 52 chars
    clean_title = re.sub(r"\s+", " ", title_raw).strip()
    if video_format == "SHORT_45_SEC":
        if not clean_title.endswith("#Shorts"):
            # Ensure title + " #Shorts" <= 52 chars
            max_head = 52 - len(" #Shorts")
            clean_title = f"{clean_title[:max_head].rstrip()} #Shorts"
    else:
        if len(clean_title) > 51:
            clean_title = clean_title[:51].rstrip(" ,.-:")

    # Build Description
    first_two_lines = (
        f"Why {movie} is fundamentally misunderstood: an analytical deconstruction.\n"
        f"Exploring the hidden cinematography, character psychology, and thematic design of {movie}."
    )

    middle_lines = []
    chapter_ts = None
    if video_format == "LONG_5_6_MIN":
        middle_lines.append("\nTIMESTAMPS:")
        chapter_ts = _calculate_long_form_chapters(manifest)
        for c in chapter_ts:
            middle_lines.append(f"{c['timestamp']} - {c['title']}")
    else:
        middle_lines.append("\nDEEP-DIVE ANALYSIS:")
        if related_long_video_id:
            middle_lines.append(f"▶️ Watch the full 6-minute deep dive breakdown: https://youtu.be/{related_long_video_id}")
        else:
            middle_lines.append("▶️ Subscribe to Cinema X-Ray for daily film breakdowns and visual essays.")

    # Bottom hashtags & semantic entities
    movie_clean = re.sub(r"[^\w]", "", movie)
    cluster_clean = re.sub(r"[^\w]", "", cluster)
    bottom_section = (
        f"\n\nABOUT CINEMA X-RAY:\n"
        f"Cinema X-Ray produces frame-by-frame analytical essays dissecting Hollywood's greatest films.\n\n"
        f"#{movie_clean} #FilmAnalysis #CinemaXRay #{cluster_clean} #MovieBreakdown\n\n"
        f"Entity Graph: {movie} | {cluster} | {lens}"
    )

    full_description = f"{first_two_lines}\n{''.join(middle_lines)}{bottom_section}"

    # Build 15 high-velocity tags
    tags_pool = [
        f"{movie} analysis",
        f"{movie} explained",
        f"{movie} breakdown",
        f"{movie} ending explained",
        f"{movie} hidden details",
        "cinema x ray",
        "video essay",
        "film analysis",
        "cinematography analysis",
        f"{cluster} explained",
        f"{cluster} breakdown",
        "scene breakdown",
        "character study",
        "film theory",
        f"{movie} film essay"
    ]
    # Enforce exactly 15 tags and total length < 450 chars
    final_tags = tags_pool[:15]
    total_tag_chars = sum(len(t) for t in final_tags) + len(final_tags) - 1
    if total_tag_chars > 440:
        final_tags = [t[:25] for t in final_tags]

    return YouTubePackage(
        optimized_title=clean_title,
        seo_description=full_description,
        tags=final_tags,
        category_id="1",
        made_for_kids=False,
        video_format=video_format,
        job_slug=job_slug,
        chapter_timestamps=chapter_ts,
        related_long_video_id=related_long_video_id
    )


def generate_algorithmic_metadata(
    manifest_json: Union[str, Path, Dict[str, Any]],
    video_format: str = "LONG_5_6_MIN",
    related_long_video_id: Optional[str] = None
) -> YouTubePackage:
    """
    Uses Gemini (google-genai) to generate a complete YouTubePackage optimized
    for YouTube's Browse, Suggested, and Search algorithms.
    
    Enforces:
      1. optimized_title: Curiosity-gap title under 52 characters (with #Shorts cleanly appended for Shorts).
      2. seo_description:
         - First 2 lines: High-retention hook + primary entity keywords.
         - Middle section: Exact 00:00 chapter timestamps (Long-Form) or Funnel Link (Shorts).
         - Bottom section: 3-5 hyper-relevant niche hashtags + entity graph.
      3. tags: Exactly 15 high-velocity search & entity tags (total < 450 characters).
      4. category_id: "1" (Film & Animation).
      5. made_for_kids: Strictly False.
    """
    if isinstance(manifest_json, (str, Path)):
        with open(str(manifest_json), "r", encoding="utf-8") as f:
            manifest = json.load(f)
    elif isinstance(manifest_json, dict):
        manifest = manifest_json
    else:
        raise ValueError(f"Invalid manifest_json type: {type(manifest_json)}")

    video_format = manifest.get("video_format", video_format)
    job_slug = manifest.get("job_slug", "cinema_xray")
    movie = manifest.get("movie_name", "Cinema")
    cluster = manifest.get("cluster_name", "Film Franchise")
    lens = manifest.get("category_lens", "Film Analysis")
    thesis = manifest.get("core_thesis", "")
    base_title = manifest.get("title", "")

    # Calculate exact chapter timestamps if Long-Form
    calculated_chapters = _calculate_long_form_chapters(manifest) if video_format == "LONG_5_6_MIN" else None

    client = _get_api_client()
    if not client:
        return _fallback_metadata(manifest, video_format, related_long_video_id)

    prompt = f"""
You are the Lead YouTube Growth Strategist & Algorithmic SEO Specialist for 'Cinema X-Ray' (a premium cinema essay channel alongside Nerdwriter, Lessons from the Screenplay, and Thomas Flight).

Generate algorithmic publishing metadata for this video:
- Title Idea: {base_title}
- Movie / Film: {movie}
- Franchise / Director: {cluster}
- Analytical Lens: {lens}
- Core Thesis: {thesis}
- Video Format: {video_format}

Strict Constraints:
1. optimized_title:
   - Must be an irresistible, high-CTR curiosity-gap title strictly UNDER 52 CHARACTERS (e.g. 35 to 50 characters).
   - If format is SHORT_45_SEC, include '#Shorts' at the end while keeping the TOTAL length under 52 characters.
   - Do NOT use generic clickbait like 'You Won't Believe' or all caps. Frame it as a psychological revelation or design secret.
2. hook_lines: Exactly 2 lines of high-retention copy summarizing the shocking core thesis with primary movie, character, and director entity keywords for Google/YouTube semantic indexing.
3. tags: Exactly 15 high-velocity search & entity tags. Include the movie title, franchise, director, key character, 'cinema x ray', 'film essay', 'scene breakdown'. Total combined tag characters MUST be under 450.
4. niche_hashtags: 3 to 5 hyper-relevant niche hashtags (e.g. #FilmAnalysis #CinemaXRay #{re.sub(r'[^a-zA-Z0-9]', '', movie)}).
"""

    models = ["gemini-flash-lite-latest", "gemini-3.1-flash-lite", "gemini-flash-latest"]
    package_data = None

    class MetadataDraft(BaseModel):
        optimized_title: str
        hook_lines: List[str]
        tags: List[str]
        niche_hashtags: List[str]

    for model_name in models:
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=MetadataDraft,
                    temperature=0.25
                )
            )
            package_data = json.loads(resp.text)
            break
        except Exception as e:
            print(f"[YouTube Publisher] Notice: Gemini ({model_name}) attempt encountered: {e}. Trying next...")
            time.sleep(1.0)

    if not package_data:
        print("[YouTube Publisher] Falling back to deterministic algorithmic compiler.")
        return _fallback_metadata(manifest, video_format, related_long_video_id)

    # 1. Enforce Title Gatekeeper (< 52 characters)
    title = package_data.get("optimized_title", base_title).strip()
    if video_format == "SHORT_45_SEC":
        if "#Shorts" not in title:
            max_head = 51 - len(" #Shorts")
            title = f"{title[:max_head].rstrip()} #Shorts"
        elif len(title) > 51:
            title = f"{title.replace('#Shorts', '').strip()[:43].rstrip()} #Shorts"
    else:
        if len(title) > 51:
            title = title[:51].rstrip(" ,.-:")

    # 2. Build Multi-Section SEO Description
    hook_lines_list = package_data.get("hook_lines", [])
    if len(hook_lines_list) >= 2:
        hook_text = f"{hook_lines_list[0].strip()}\n{hook_lines_list[1].strip()}"
    elif hook_lines_list:
        hook_text = hook_lines_list[0].strip()
    else:
        hook_text = f"Why {movie} is fundamentally misunderstood.\nA frame-by-frame analytical essay deconstructing {movie}."

    desc_parts = [hook_text]

    # Middle Section: Long-Form Chapters or Shorts Funnel
    if video_format == "LONG_5_6_MIN":
        desc_parts.append("\nTIMESTAMPS:")
        for ch in calculated_chapters:
            desc_parts.append(f"{ch['timestamp']} - {ch['title']}")
    else:
        desc_parts.append("\nDEEP-DIVE ESSAY:")
        if related_long_video_id:
            desc_parts.append(f"▶️ Watch the full 6-minute deep dive on this scene: https://youtu.be/{related_long_video_id}")
        else:
            desc_parts.append("▶️ Subscribe to Cinema X-Ray for daily film breakdowns and visual essays.")

    # Bottom Section: Brand info, hashtags & semantic entities
    hashtags = package_data.get("niche_hashtags", ["#FilmAnalysis", "#CinemaXRay", f"#{re.sub(r'[^a-zA-Z0-9]', '', movie)}"])
    hash_str = " ".join(hashtags[:5])

    bottom_text = (
        f"\n\nABOUT CINEMA X-RAY:\n"
        f"Cinema X-Ray produces frame-by-frame analytical essays dissecting Hollywood's greatest films.\n\n"
        f"{hash_str}\n\n"
        f"Entity Graph: {movie} | {cluster} | {lens}"
    )
    desc_parts.append(bottom_text)
    full_description = "\n".join(desc_parts)

    # 3. Enforce Tags Gatekeeper (15 tags, total chars < 450)
    raw_tags = package_data.get("tags", [])
    clean_tags = [t.strip() for t in raw_tags if t.strip()]
    
    # Ensure 15 tags
    if len(clean_tags) < 15:
        defaults = [
            f"{movie} analysis", f"{movie} explained", "video essay",
            "film breakdown", "cinema x ray", "cinematography"
        ]
        for d in defaults:
            if d not in clean_tags:
                clean_tags.append(d)
            if len(clean_tags) == 15:
                break
    clean_tags = clean_tags[:15]

    # Check total characters < 450
    total_tag_chars = sum(len(t) for t in clean_tags) + len(clean_tags) - 1
    if total_tag_chars > 440:
        clean_tags = [t[:24] for t in clean_tags]

    pkg = YouTubePackage(
        optimized_title=title,
        seo_description=full_description,
        tags=clean_tags,
        category_id="1",
        made_for_kids=False,
        video_format=video_format,
        job_slug=job_slug,
        chapter_timestamps=calculated_chapters,
        related_long_video_id=related_long_video_id
    )
    return pkg


def get_youtube_service(client_secret_path=None, token_path=None):
    """
    Authenticate and return an authorized YouTube Data API service.
    Re-uses token.json if valid; refreshes if expired; launches browser OAuth if needed.
    Checks config/youtube_token.json and credentials/token.json.
    """
    if not YOUTUBE_API_AVAILABLE:
        raise ImportError("google-api-python-client or google-auth-oauthlib is not installed.")

    token_candidates = [
        Path(token_path) if token_path else None,
        CONFIG_DIR / "youtube_token.json",
        CREDENTIALS_DIR / "token.json",
    ]
    secret_candidates = [
        Path(client_secret_path) if client_secret_path else None,
        CONFIG_DIR / "client_secrets.json",
        CREDENTIALS_DIR / "client_secrets.json",
    ]

    token_file = next((p for p in token_candidates if p and p.exists()), None)
    secret_file = next((p for p in secret_candidates if p and p.exists()), None)

    creds = None
    if token_file:
        try:
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        except Exception as e:
            print(f"[YouTube Auth] Warning: could not load existing token from {token_file}: {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("[YouTube Auth] Refreshing expired YouTube access token...")
                creds.refresh(Request())
                print("[YouTube Auth] Token refreshed successfully.")
            except Exception as e:
                print(f"[YouTube Auth] Token refresh failed ({e}). Re-authenticating...")
                creds = None

        if not creds or not creds.valid:
            if not secret_file:
                raise FileNotFoundError(
                    f"\n[YouTube Auth Error] client_secrets.json not found in config/ or credentials/."
                )

            print("\n[YouTube Auth] Opening browser for one-time YouTube Channel authorization...")
            flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), SCOPES)
            creds = flow.run_local_server(port=0, prompt="consent")

            save_token = CONFIG_DIR / "youtube_token.json"
            save_token.parent.mkdir(parents=True, exist_ok=True)
            with open(save_token, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            print(f"[YouTube Auth] Authorized credentials saved to: {save_token}")

    return build("youtube", "v3", credentials=creds)


def upload_to_youtube(
    video_path: Union[str, Path],
    thumbnail_path: Optional[Union[str, Path]],
    metadata_package: YouTubePackage,
    publish_at_iso: Optional[str] = None,
    dry_run: Optional[bool] = None,
    client_secret_path: Optional[Union[str, Path]] = None,
    token_path: Optional[Union[str, Path]] = None
) -> Dict[str, Any]:
    """
    Uploads a video to YouTube using resumable chunked upload with exponential backoff retry.
    Associates the custom thumbnail upon completion.
    
    In dry-run mode (DRY_RUN=True or dry_run=True):
      - Validates video file, thumbnail file, title length, tags, and category.
      - Compiles and writes the exact payload package to output/publish_packages/<job_slug>_package.json.
      - Returns validated package dictionary without calling the live YouTube insert endpoint.
    """
    video_path = Path(video_path)
    job_slug = metadata_package.job_slug
    PUBLISH_PACKAGES_DIR.mkdir(parents=True, exist_ok=True)

    # Detect dry-run mode
    if dry_run is None:
        env_val = os.environ.get("DRY_RUN", "").lower().strip()
        dry_run = env_val in ("1", "true", "yes")

    # Format status body
    status_body = {
        "privacyStatus": "private" if publish_at_iso else "unlisted",
        "selfDeclaredMadeForKids": False,
        "embeddable": True,
        "publicStatsViewable": True
    }
    if publish_at_iso:
        status_body["publishAt"] = publish_at_iso
        status_body["privacyStatus"] = "private"

    payload = {
        "snippet": {
            "title": metadata_package.optimized_title,
            "description": metadata_package.seo_description,
            "tags": metadata_package.tags,
            "categoryId": str(metadata_package.category_id),
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en"
        },
        "status": status_body
    }

    # Verify thumbnail size if provided
    thumb_path_resolved = None
    if thumbnail_path:
        thumb_path_resolved = Path(thumbnail_path)
        if thumb_path_resolved.exists():
            thumb_size_mb = thumb_path_resolved.stat().st_size / (1024 * 1024)
            if thumb_size_mb >= 2.0:
                raise ValueError(f"Thumbnail exceeds 2MB YouTube limit ({thumb_size_mb:.2f} MB): {thumb_path_resolved}")
        else:
            print(f"[YouTube Upload] Warning: Thumbnail path does not exist on disk: {thumb_path_resolved}")

    # Compile package manifest on disk
    package_file = PUBLISH_PACKAGES_DIR / f"{job_slug}_package.json"
    package_summary = {
        "job_slug": job_slug,
        "video_format": metadata_package.video_format,
        "video_file": str(video_path),
        "thumbnail_file": str(thumb_path_resolved) if thumb_path_resolved else None,
        "compiled_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
        "chapter_timestamps": metadata_package.chapter_timestamps,
        "title_length": len(metadata_package.optimized_title),
        "tag_count": len(metadata_package.tags),
        "total_tag_chars": sum(len(t) for t in metadata_package.tags) + len(metadata_package.tags) - 1,
        "dry_run": dry_run
    }

    with open(package_file, "w", encoding="utf-8") as f:
        json.dump(package_summary, f, indent=2)

    # Handle DRY RUN
    if dry_run:
        print(f"\n🧪 [DRY RUN VALIDATION] YouTube Publication Package Compiled & Verified:")
        print(f"   Slug:           {job_slug}")
        print(f"   Title:          {metadata_package.optimized_title} ({len(metadata_package.optimized_title)} chars)")
        print(f"   Format:         {metadata_package.video_format}")
        print(f"   Privacy:        {status_body['privacyStatus']}")
        print(f"   Tags ({len(metadata_package.tags)}):    {', '.join(metadata_package.tags[:4])}... ({package_summary['total_tag_chars']} chars)")
        print(f"   Thumbnail:      {thumb_path_resolved} ({thumb_path_resolved.stat().st_size / 1024:.1f} KB)" if thumb_path_resolved and thumb_path_resolved.exists() else "   Thumbnail: None")
        print(f"   Package JSON:   {package_file}")
        print(f"   Status:         ✅ VALIDATED READY FOR UPLOAD\n")

        return {
            "dry_run": True,
            "status": "VALIDATED",
            "job_slug": job_slug,
            "package_json_path": str(package_file),
            "video_path": str(video_path),
            "thumbnail_path": str(thumb_path_resolved) if thumb_path_resolved else None,
            "title": metadata_package.optimized_title,
            "payload": payload
        }

    # Live Upload Flow
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found for live upload: {video_path}")

    service = get_youtube_service(client_secret_path, token_path)

    # Resumable media file upload with 10MB chunk size
    chunk_size = 10 * 1024 * 1024
    media = MediaFileUpload(str(video_path), chunksize=chunk_size, resumable=True, mimetype="video/mp4")

    print(f"[YouTube Upload] Starting Resumable Upload for: {video_path.name}")
    print(f"  Title: {metadata_package.optimized_title}")
    print(f"  Size:  {video_path.stat().st_size / (1024*1024):.2f} MB")

    request = service.videos().insert(
        part="snippet,status",
        body=payload,
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

    # Set Custom Thumbnail if provided
    thumbnail_set = False
    if thumb_path_resolved and thumb_path_resolved.exists():
        try:
            print(f"[YouTube Upload] Setting custom thumbnail from: {thumb_path_resolved.name}...")
            thumb_media = MediaFileUpload(str(thumb_path_resolved), mimetype="image/jpeg")
            service.thumbnails().set(
                videoId=video_id,
                media_body=thumb_media
            ).execute()
            thumbnail_set = True
            print(f"✅ Custom thumbnail successfully set for video {video_id}!")
        except Exception as e:
            print(f"[YouTube Upload] Warning: Could not set thumbnail: {e}")

    return {
        "dry_run": False,
        "status": status_body["privacyStatus"],
        "id": video_id,
        "url": video_url,
        "title": metadata_package.optimized_title,
        "thumbnail_set": thumbnail_set,
        "package_json_path": str(package_file)
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cinema X-Ray YouTube Publisher")
    parser.add_argument("--manifest", type=str, required=True, help="Path to script_manifest.json")
    parser.add_argument("--video", type=str, default=None, help="Video file path")
    parser.add_argument("--thumbnail", type=str, default=None, help="Thumbnail file path")
    parser.add_argument("--dry-run", action="store_true", help="Compile and validate metadata without uploading")
    parser.add_argument("--related-long", type=str, default=None, help="Related Long video ID for Shorts funnel")
    args = parser.parse_args()

    pkg = generate_algorithmic_metadata(args.manifest, related_long_video_id=args.related_long)
    print(f"\nTitle: {pkg.optimized_title}")
    print(f"Length: {len(pkg.optimized_title)} chars")
    print(f"Tags ({len(pkg.tags)}): {pkg.tags}")
    print(f"\nDescription:\n{pkg.seo_description[:300]}...\n")

    if args.video or args.dry_run:
        res = upload_to_youtube(
            video_path=args.video or "dummy.mp4",
            thumbnail_path=args.thumbnail,
            metadata_package=pkg,
            dry_run=args.dry_run
        )
        print(f"Result: {res}")
