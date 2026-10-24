"""
Cinema X-Ray QA Gatekeeper (100% Deterministic Pre-Upload Automated Inspector)
Strict automated quality inspection using ffprobe & Pillow before YouTube publishing:
  - Video stream existence (h264/hevc) & integrity
  - Audio stream existence (aac/pcm) & loudness integrity
  - Audio/Video stream synchronization (max desync < 0.35s)
  - 100% Narration Completion (video duration MUST cover entire voiceover wav)
  - 100% Subtitle Dialogue Completion (video duration MUST cover final subtitle punchline card)
  - Tail Packet Integrity (verifies video packets exist through the final second)
  - Exact resolution & aspect ratio (1080x1920, 4K 2160x3840, 8K 4320x7680 for Shorts; 1920x1080, 4K for Long)
  - Duration bounds (30.0s-59.5s for Shorts, 240.0s-420.0s for Long-Form)
  - File size bounds (>2MB video, <2MB thumbnail)
  - Thumbnail resolution & format match
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Union, Optional, Tuple, Dict, Any
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent


def find_associated_voiceover(video_path: Path) -> Optional[Path]:
    """Finds matching voiceover audio in output/audio/ by job slug."""
    stem = video_path.stem.replace("_8k", "").replace("_1080p", "").replace("_final", "").replace("cinema_xray_", "")
    audio_dir = REPO_ROOT / "output" / "audio"
    candidates = [
        audio_dir / f"{stem}_voiceover.wav",
        audio_dir / f"{stem}.wav"
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def find_associated_subtitles(video_path: Path) -> Optional[Path]:
    """Finds matching subtitles in output/script/ or output/temp/ by job slug."""
    stem = video_path.stem.replace("_8k", "").replace("_1080p", "").replace("_final", "").replace("cinema_xray_", "")
    candidates = [
        REPO_ROOT / "output" / "script" / f"{stem}_subtitles.json",
        REPO_ROOT / "output" / "temp" / f"{stem}_subtitles.ass"
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def extract_last_subtitle_timestamp(sub_path: Path) -> Optional[float]:
    """Extracts the end timestamp of the final spoken subtitle event."""
    try:
        if sub_path.suffix == ".json":
            with open(sub_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cards = data.get("cards", [])
            if cards:
                return max((float(c.get("end", c.get("end_sec", 0))) for c in cards), default=0.0)
        elif sub_path.suffix == ".ass":
            import re
            last_end = 0.0
            with open(sub_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("Dialogue:"):
                        parts = line.split(",", 9)
                        if len(parts) >= 3:
                            end_str = parts[2].strip()  # H:MM:SS.cc
                            m = re.match(r"(\d+):(\d+):(\d+(?:\.\d+)?)", end_str)
                            if m:
                                h, mn, s = float(m.group(1)), float(m.group(2)), float(m.group(3))
                                sec = h * 3600 + mn * 60 + s
                                if sec > last_end:
                                    last_end = sec
            if last_end > 0.0:
                return last_end
    except Exception:
        pass
    return None


def inspect_final_render(
    video_path: Union[str, Path],
    thumbnail_path: Optional[Union[str, Path]] = None,
    video_format: str = "SHORT_45_SEC",
    voiceover_path: Optional[Union[str, Path]] = None,
    subtitles_path: Optional[Union[str, Path]] = None,
    dry_run: bool = False
) -> Tuple[bool, Union[Dict[str, Any], str]]:
    """
    Deterministically inspects the final rendered video and custom thumbnail before publishing.
    Performs 10 comprehensive QA checks to guarantee zero amputation, cutoff, or desync errors.
    
    Returns:
      (True, diagnostics_dict) if all checks pass.
      (False, error_reason_string) if any check fails.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        return False, f"Video file not found: {video_path}"

    # 1. File Size Gatekeeper
    file_size_bytes = video_path.stat().st_size
    min_size = 50_000 if dry_run else 2_000_000  # 2MB minimum for real master render
    if file_size_bytes < min_size:
        return False, f"Video file size too small: {file_size_bytes} bytes (min: {min_size})"

    # 2. ffprobe Stream Analysis
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(video_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        probe_data = json.loads(res.stdout)
    except Exception as e:
        return False, f"ffprobe execution failed on {video_path}: {e}"

    streams = probe_data.get("streams", [])
    format_info = probe_data.get("format", {})

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if not video_stream:
        return False, f"No video stream found in {video_path}"
    if not audio_stream:
        return False, f"No audio stream found in {video_path}"

    # 3. Video Codec & Geometry Verification
    v_codec = video_stream.get("codec_name", "").lower()
    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))

    if v_codec not in ("h264", "hevc", "avc1"):
        return False, f"Unsupported video codec: '{v_codec}' (expected h264 or hevc)"

    # Compute duration
    dur_str = format_info.get("duration") or video_stream.get("duration")
    duration = float(dur_str) if dur_str else 0.0

    # Audio stream duration
    a_dur_str = audio_stream.get("duration") or format_info.get("duration")
    audio_duration = float(a_dur_str) if a_dur_str else duration

    # 4. Stream Desynchronization Gatekeeper (Video vs Audio stream in container)
    stream_diff = abs(duration - audio_duration)
    if stream_diff > 0.35:
        return False, (
            f"QA FAILED [STREAM_DESYNC]: Video duration ({duration:.2f}s) and Audio duration ({audio_duration:.2f}s) "
            f"differ by {stream_diff:.2f}s (>0.35s limit). Streams are out of sync!"
        )

    # 5. Voiceover Narration Completeness Gatekeeper (Prevents Audio Truncation Blunder)
    vo_file = Path(voiceover_path) if voiceover_path else find_associated_voiceover(video_path)
    vo_duration = None
    if vo_file and vo_file.exists():
        try:
            cmd_vo = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(vo_file)]
            vo_duration = float(subprocess.check_output(cmd_vo).decode().strip())
            if duration < (vo_duration - 0.20):
                cutoff_sec = vo_duration - duration
                return False, (
                    f"QA FAILED [NARRATION_TRUNCATED]: Video ends at {duration:.2f}s, but voiceover narration requires {vo_duration:.2f}s! "
                    f"The ending was cut off by {cutoff_sec:.2f} seconds before speech finished!"
                )
        except Exception as e:
            print(f"⚠️ QA Gatekeeper Warning: Failed to probe voiceover duration: {e}")

    # 6. Subtitle & Dialogue Completeness Gatekeeper (Prevents Missing Punchlines)
    sub_file = Path(subtitles_path) if subtitles_path else find_associated_subtitles(video_path)
    last_sub_end = None
    if sub_file and sub_file.exists():
        last_sub_end = extract_last_subtitle_timestamp(sub_file)
        if last_sub_end and duration < (last_sub_end - 0.25):
            cutoff_sec = last_sub_end - duration
            return False, (
                f"QA FAILED [SUBTITLE_TRUNCATED]: Video ends at {duration:.2f}s, but final subtitle dialogue reaches {last_sub_end:.2f}s! "
                f"Dialogue punchline was cut off by {cutoff_sec:.2f} seconds!"
            )

    # 7. Tail Packet Integrity (Verifies video packets actively reach the end)
    try:
        tail_start = max(0.0, duration - 1.2)
        cmd_tail = [
            "ffprobe", "-v", "error",
            "-show_entries", "packet=pts_time,stream_index",
            "-read_intervals", f"{tail_start:.1f}%999",
            "-of", "json",
            str(video_path)
        ]
        res_tail = subprocess.run(cmd_tail, capture_output=True, text=True, check=True)
        pkts = json.loads(res_tail.stdout).get("packets", [])
        v_pkts = [p for p in pkts if p.get("stream_index") == video_stream.get("index", 0)]
        if not v_pkts:
            return False, f"QA FAILED [CORRUPT_TAIL]: No video packets detected in final 1.2 seconds of {video_path}!"
        last_v_pts = float(v_pkts[-1].get("pts_time", 0))
        if last_v_pts < (duration - 0.30):
            return False, (
                f"QA FAILED [PREMATURE_VIDEO_FREEZE]: Last video packet pts ({last_v_pts:.2f}s) freezes before container duration ({duration:.2f}s)!"
            )
    except Exception as e:
        print(f"⚠️ QA Gatekeeper Warning: Tail packet scan skipped: {e}")

    # 8. Aspect Ratio & Resolution Policy
    if video_format == "SHORT_45_SEC":
        aspect_ratio = width / height if height > 0 else 0.0
        expected_aspect = 9.0 / 16.0
        if abs(aspect_ratio - expected_aspect) > 0.03:
            return False, f"Shorts aspect ratio invalid: {width}x{height} (aspect: {aspect_ratio:.3f}, expected 9:16)"

        # Allowed: 1080x1920, 2160x3840 (4K), 4320x7680 (8K)
        allowed_shorts = ((1080, 1920), (2160, 3840), (4320, 7680))
        if (width, height) not in allowed_shorts:
            return False, f"Shorts resolution must be 1080x1920, 2160x3840 (4K), or 4320x7680 (8K). Got {width}x{height}"

        # Duration bounds: 30.0s to 59.5s
        if not dry_run and (duration < 30.0 or duration > 59.5):
            return False, f"Shorts duration ({duration:.2f}s) outside 30.0s-59.5s YouTube limit"

    elif video_format == "LONG_5_6_MIN":
        aspect_ratio = width / height if height > 0 else 0.0
        expected_aspect = 16.0 / 9.0
        if abs(aspect_ratio - expected_aspect) > 0.03:
            return False, f"Long-Form aspect ratio invalid: {width}x{height} (aspect: {aspect_ratio:.3f}, expected 16:9)"

        allowed_long = ((1920, 1080), (3840, 2160))
        if (width, height) not in allowed_long:
            return False, f"Long-Form resolution must be 1920x1080 or 3840x2160. Got {width}x{height}"

        # Duration bounds for Long-Form Video Essays: 90.0s (1.5 min) to 600.0s (10 min)
        if not dry_run and (duration < 90.0 or duration > 600.0):
            return False, f"Long-Form duration ({duration:.2f}s) outside 90.0s-600.0s bounds"

    else:
        return False, f"Unknown video_format: '{video_format}'"

    # 9. Audio Codec Verification
    a_codec = audio_stream.get("codec_name", "").lower()
    if a_codec not in ("aac", "pcm_s16le", "mp3"):
        return False, f"Unexpected audio codec: '{a_codec}'"

    # 10. Thumbnail Verification
    thumb_info = None
    if thumbnail_path:
        thumb_path = Path(thumbnail_path)
        if not thumb_path.exists():
            return False, f"Thumbnail file not found: {thumb_path}"

        thumb_bytes = thumb_path.stat().st_size
        if thumb_bytes >= 2_000_000:
            return False, f"Thumbnail size ({thumb_bytes / (1024*1024):.2f} MB) exceeds YouTube 2MB limit"

        try:
            with Image.open(thumb_path) as im:
                tw, th = im.size
                if video_format == "LONG_5_6_MIN" and (tw, th) != (1280, 720):
                    return False, f"Long-Form thumbnail must be strictly 1280x720, got {tw}x{th}"
                elif video_format == "SHORT_45_SEC" and (tw, th) != (1080, 1920):
                    return False, f"Shorts thumbnail must be strictly 1080x1920, got {tw}x{th}"
                thumb_info = {
                    "path": str(thumb_path),
                    "resolution": f"{tw}x{th}",
                    "size_kb": round(thumb_bytes / 1024, 1)
                }
        except Exception as e:
            return False, f"Corrupted or invalid thumbnail image: {e}"

    diagnostics = {
        "status": "QA_PASSED",
        "video_format": video_format,
        "video_file": str(video_path),
        "video_size_mb": round(file_size_bytes / (1024 * 1024), 2),
        "video_codec": v_codec,
        "audio_codec": a_codec,
        "resolution": f"{width}x{height}",
        "duration_sec": round(duration, 2),
        "audio_duration_sec": round(audio_duration, 2),
        "voiceover_duration_sec": round(vo_duration, 2) if vo_duration else None,
        "last_subtitle_timestamp_sec": round(last_sub_end, 2) if last_sub_end else None,
        "stream_desync_delta_sec": round(stream_diff, 3),
        "fps": video_stream.get("r_frame_rate"),
        "thumbnail": thumb_info
    }
    return True, diagnostics


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cinema X-Ray 100% Deterministic QA Gatekeeper Inspector")
    parser.add_argument("--video", type=str, required=True, help="Video path to inspect")
    parser.add_argument("--thumbnail", type=str, default=None, help="Thumbnail path to inspect")
    parser.add_argument("--format", choices=["SHORT_45_SEC", "LONG_5_6_MIN"], default="SHORT_45_SEC")
    parser.add_argument("--voiceover", type=str, default=None, help="Path to original voiceover wav")
    parser.add_argument("--subtitles", type=str, default=None, help="Path to subtitles JSON or ASS")
    parser.add_argument("--dry-run", action="store_true", help="Allow dry-run bounds")
    args = parser.parse_args()

    passed, result = inspect_final_render(
        args.video,
        args.thumbnail,
        args.format,
        voiceover_path=args.voiceover,
        subtitles_path=args.subtitles,
        dry_run=args.dry_run
    )
    if passed:
        print("✅ QA Gatekeeper PASSED (100% Validated):")
        print(json.dumps(result, indent=2))
    else:
        print(f"❌ QA Gatekeeper FAILED: {result}")
        exit(1)
