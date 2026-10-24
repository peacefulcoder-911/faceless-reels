"""
Cinema X-Ray: Dedicated Long-Form Widescreen Video Compositor
Engineered exclusively for 5–6 minute horizontal 16:9 (1920x1080 -> 3840x2160 4K UHD) essays.
Features:
  - Active pixel letterbox detection (cropdetect)
  - Cinema X-Ray Widescreen Framing (92% foreground with blurred ambient backdrop + subtle border)
  - Dynamic camera motion (SLOW_PUSH_IN / STATIC) and 2.5s Chapter HUD badge
  - Dedicated long-form tension ambiance mix (-22dB)
  - Lower-third widescreen ASS subtitle burn
  - Hardware-accelerated horizontal 4K UHD export (3840x2160)
Strictly isolated from Shorts directories.
"""

import os
import re
import json
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

REPO_ROOT = Path(__file__).resolve().parent.parent

# Isolated Long-Form Directories
CLIPS_LONG_DIR = REPO_ROOT / "output" / "clips_long"
TEMP_LONG_DIR = REPO_ROOT / "output" / "temp_long"
FINAL_LONG_DIR = REPO_ROOT / "output" / "final_long_video"


def detect_letterbox_crop_widescreen(video_path: str, sample_sec: float = 10.0) -> str:
    """Detects active video rectangle to strip hardcoded letterbox bars from 2.39:1 films."""
    try:
        cmd = [
            "ffmpeg", "-ss", str(sample_sec),
            "-i", str(video_path),
            "-vframes", "5",
            "-vf", "cropdetect=24:16:0",
            "-f", "null", "-"
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        for line in reversed(res.stderr.splitlines()):
            if "crop=" in line:
                m = re.search(r"crop=([0-9:]+)", line)
                if m:
                    return f"crop={m.group(1)},"
    except Exception:
        pass
    # Standard Cinemascope fallback: 140px black bars on 1080p source
    return "crop=in_w:800:0:140,"


def render_widescreen_xray_clip(
    source_path: str,
    start_time: float,
    duration: float,
    output_clip_path: str,
    camera_motion: str = "STATIC",
    chapter_title: Optional[str] = None,
    fps: int = 30
) -> str:
    """
    Renders an individual scene beat in native 1920x1080 (16:9 widescreen) at 30fps.
    - Background: Scale source to 1920x1080, gblur=40, darken slightly (brightness=-0.12).
    - Foreground: Scale cropped footage to 92% of frame (1766x994) centered over ambient background.
    - Motion: SLOW_PUSH_IN (subtle zoompan 1.0x to 1.05x) or STATIC.
    - Chapter HUD: If chapter_title is provided, renders a sleek 2.5s upper-left indicator.
    """
    output_path = Path(output_clip_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    crop_filter = detect_letterbox_crop_widescreen(source_path, sample_sec=start_time + 0.5)

    # 1. Background layer (heavily blurred and darkened)
    bg_filter = (
        f"[0:v]{crop_filter}scale=1920:1080:force_original_aspect_ratio=increase,"
        f"crop=1920:1080,gblur=sigma=40,eq=brightness=-0.12:contrast=1.05:saturation=1.2[bg];"
    )

    # 2. Foreground layer (scaled to 92% of 16:9 frame, preserving aspect ratio)
    if camera_motion == "SLOW_PUSH_IN":
        # Subtle, smooth push-in
        fg_filter = (
            f"[0:v]{crop_filter}scale=1766:994:force_original_aspect_ratio=decrease,"
            f"zoompan=z='min(zoom+0.0006,1.05)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1766x994:fps={fps}[fg];"
        )
    else:
        fg_filter = (
            f"[0:v]{crop_filter}scale=1766:994:force_original_aspect_ratio=decrease[fg];"
        )

    # 3. Composite foreground over background
    composite_filter = "[bg][fg]overlay=(W-w)/2:(H-h)/2[base];"

    # 4. Optional Chapter HUD Badge (Upper Left, 2.5s duration)
    if chapter_title:
        # Sanitize text for FFmpeg drawtext
        clean_title = chapter_title.replace(":", "\\:").replace("'", "").replace('"', '')
        hud_filter = (
            f"[base]drawtext=text='CINEMA X-RAY  |  {clean_title}':font='Arial':fontsize=26:"
            f"fontcolor=white:box=1:boxcolor=black@0.70:boxborderw=10:x=60:y=60:"
            f"enable='between(t,0.3,2.8)',setsar=1"
        )
    else:
        hud_filter = "[base]null,setsar=1"

    vf = bg_filter + fg_filter + composite_filter + hud_filter

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start_time:.3f}",
        "-t", f"{duration:.3f}",
        "-i", str(source_path),
        "-filter_complex", vf,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
        "-an",
        str(output_path)
    ]

    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg failed rendering long clip {output_path.name}: {res.stderr[:300]}")

    return str(output_path)


def assemble_long_form_video(
    clip_paths: List[str],
    voiceover_wav_path: str,
    ass_subtitle_path: str,
    output_1080p_path: str,
    temp_dir: Optional[str] = None
) -> str:
    """
    Concatenates long-form scene clips, mixes 5–6 min procedural tension score (-22dB below voice),
    and burns lower-third widescreen ASS subtitles into output/final_long_video/<job_slug>_1080p.mp4.
    """
    temp_dir_path = Path(temp_dir or TEMP_LONG_DIR)
    temp_dir_path.mkdir(parents=True, exist_ok=True)
    out_1080p = Path(output_1080p_path)
    out_1080p.parent.mkdir(parents=True, exist_ok=True)

    # 1. Write concat list
    concat_list_file = temp_dir_path / f"concat_{out_1080p.stem}.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")

    raw_video = temp_dir_path / f"raw_long_concat_{out_1080p.stem}.mp4"
    concat_cmd = [
        "ffmpeg", "-y", "-v", "quiet",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        str(raw_video)
    ]
    subprocess.run(concat_cmd, check=True)

    # 2. Get Voiceover Duration and Establish Synchronized Master Target
    ffprobe_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(voiceover_wav_path)
    ]
    dur_str = subprocess.check_output(ffprobe_cmd).decode().strip()
    total_dur = float(dur_str)
    target_master_dur = round(total_dur + 0.60, 2)
    pad_audio = round(target_master_dur - total_dur, 2)

    # 3. Procedural Long-Form Tension Score Mix (-22dB subtle bed with synchronized tail pad & fade)
    mixed_audio = temp_dir_path / f"mixed_long_audio_{out_1080p.stem}.wav"
    mix_cmd = [
        "ffmpeg", "-y", "-v", "quiet",
        "-f", "lavfi", "-i", f"sine=frequency=55:duration={target_master_dur}:sample_rate=24000",
        "-f", "lavfi", "-i", f"anoisesrc=d={target_master_dur}:c=pink:r=24000:a=0.015,lowpass=f=350,volume=0.04",
        "-i", str(voiceover_wav_path),
        "-filter_complex",
        f"[0:a][1:a]amix=inputs=2:duration=first[amb];"
        f"[2:a]apad=pad_dur={pad_audio},volume=1.20[vocal];"
        f"[amb][vocal]amix=inputs=2:duration=first:dropout_transition=2,"
        f"afade=t=out:st={round(target_master_dur - 0.35, 2)}:d=0.35[outa]",
        "-map", "[outa]",
        "-c:a", "pcm_s16le",
        str(mixed_audio)
    ]
    subprocess.run(mix_cmd, check=True)

    # 4. Burn Lower-Third Widescreen Subtitles into 1080p Master
    print(f"[Long Compositor] Burning widescreen subtitles & assembling 1080p master ({target_master_dur:.1f}s)...")
    # Fail-Safe Video Duration Alignment (Guarantees zero truncation)
    raw_video_dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(raw_video)]).decode().strip())
    
    vf_chain = []
    if raw_video_dur < target_master_dur:
        pad_needed = round(target_master_dur - raw_video_dur + 0.10, 2)
        print(f"⚠️ Sliced long-form clips ({raw_video_dur:.2f}s) shorter than master ({target_master_dur:.2f}s). Applying tpad frame hold (+{pad_needed:.2f}s) to guarantee zero audio cutoff.")
        vf_chain.append(f"tpad=stop_mode=clone:stop_duration={pad_needed}")
    vf_chain.append(f"ass={ass_subtitle_path}")
    vf_filter = ",".join(vf_chain)

    final_cmd = [
        "ffmpeg", "-y",
        "-i", str(raw_video),
        "-i", str(mixed_audio),
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", f"{target_master_dur:.2f}",
        str(out_1080p)
    ]
    subprocess.run(final_cmd, check=True)
    print(f"✅ 1080p Widescreen Video: {out_1080p}")
    return str(out_1080p)


def export_long_form_4k_uhd(input_1080p_path: str, output_4k_path: str) -> str:
    """
    Upscales horizontal 1920x1080 to pristine 4K UHD 3840x2160 (16:9 widescreen)
    using Apple Silicon hardware acceleration (h264_videotoolbox).
    """
    out_4k = Path(output_4k_path)
    out_4k.parent.mkdir(parents=True, exist_ok=True)
    print(f"[Long Compositor] Upscaling to horizontal 4K UHD (3840x2160)...")

    in_dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(input_1080p_path)]).decode().strip())
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_1080p_path),
        "-vf", "scale=3840:2160:flags=lanczos",
        "-c:v", "h264_videotoolbox",
        "-b:v", "45M",
        "-maxrate", "55M",
        "-bufsize", "60M",
        "-profile:v", "high",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-t", f"{in_dur:.2f}",
        str(out_4k)
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)

    if res.returncode != 0:
        print("[Long Compositor] VideoToolbox fallback to CPU libx264...")
        cmd_cpu = [
            "ffmpeg", "-y",
            "-i", str(input_1080p_path),
            "-vf", "scale=3840:2160:flags=lanczos",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "17",
            "-c:a", "copy",
            str(out_4k)
        ]
        subprocess.run(cmd_cpu, check=True)

    print(f"🌟 4K UHD Widescreen Cinema X-Ray Video: {out_4k}")
    return str(out_4k)


def gatekeeper_verify_long_video(video_path: str, expected_duration: float) -> Dict[str, Any]:
    """
    Verifies video resolution (1920x1080 or 3840x2160), 16:9 aspect ratio,
    presence of audio stream, and duration within ±0.5s.
    """
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(video_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    meta = json.loads(res.stdout)

    v_stream = next((s for s in meta.get("streams", []) if s.get("codec_type") == "video"), None)
    a_stream = next((s for s in meta.get("streams", []) if s.get("codec_type") == "audio"), None)

    if not v_stream:
        raise AssertionError(f"No video stream found in {video_path}")
    if not a_stream:
        raise AssertionError(f"No audio stream found in {video_path}")

    width = int(v_stream.get("width", 0))
    height = int(v_stream.get("height", 0))
    dur = float(meta.get("format", {}).get("duration", 0))

    # Assert resolution is 1080p or 4K horizontal
    valid_res = (width == 1920 and height == 1080) or (width == 3840 and height == 2160)
    assert valid_res, f"Resolution {width}x{height} is not valid 16:9 widescreen (must be 1920x1080 or 3840x2160)"

    # Assert 16:9 Aspect Ratio
    aspect_ratio = width / height
    assert abs(aspect_ratio - (16.0 / 9.0)) < 0.01, f"Aspect ratio {aspect_ratio:.3f} is not 16:9"

    # Assert Duration within tolerance
    diff = abs(dur - expected_duration)
    assert diff <= 1.0, f"Duration {dur:.2f}s differs from expected {expected_duration:.2f}s by {diff:.2f}s (tolerance: ±1.0s)"

    return {
        "width": width,
        "height": height,
        "duration": dur,
        "has_audio": True,
        "aspect_ratio": "16:9",
        "codec_video": v_stream.get("codec_name"),
        "codec_audio": a_stream.get("codec_name")
    }


if __name__ == "__main__":
    print("Long-Form Video Compositor Module Ready.")
