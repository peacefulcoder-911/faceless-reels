import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMP_DIR = REPO_ROOT / "output" / "temp"
CLIPS_DIR = REPO_ROOT / "output" / "clips"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
CLIPS_DIR.mkdir(parents=True, exist_ok=True)

# Curated high-res 9:16 vertical textures & cinematic backdrops for each niche
NICHE_BACKDROPS = {
    "biblical": [
        "https://images.unsplash.com/photo-1543783207-ec64e4d95325?auto=format&fit=crop&w=1080&h=1920&q=85",
        "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=1080&h=1920&q=85",
        "https://images.unsplash.com/photo-1461360370896-922624d12aa1?auto=format&fit=crop&w=1080&h=1920&q=85",
        "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1080&h=1920&q=85"
    ],
    "anime": [
        "https://images.unsplash.com/photo-1578632767115-351597cf2477?auto=format&fit=crop&w=1080&h=1920&q=85",
        "https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=1080&h=1920&q=85",
        "https://images.unsplash.com/photo-1563089145-599997674d42?auto=format&fit=crop&w=1080&h=1920&q=85",
        "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1080&h=1920&q=85"
    ],
    "heists": [
        "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=1080&h=1920&q=85",
        "https://images.unsplash.com/photo-1514565131-fce0801e5785?auto=format&fit=crop&w=1080&h=1920&q=85",
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=1080&h=1920&q=85",
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1080&h=1920&q=85"
    ],
    "mythology": [
        "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1080&h=1920&q=85",
        "https://images.unsplash.com/photo-1543783207-ec64e4d95325?auto=format&fit=crop&w=1080&h=1920&q=85",
        "https://images.unsplash.com/photo-1509114397022-ed747cca3f65?auto=format&fit=crop&w=1080&h=1920&q=85",
        "https://images.unsplash.com/photo-1461360370896-922624d12aa1?auto=format&fit=crop&w=1080&h=1920&q=85"
    ]
}

def render_ken_burns_clip(image_path: str, duration: float, output_clip_path: str, fps: int = 30) -> str:
    """Renders a dynamic vertical 1080x1920 Ken Burns slow-zoom clip from a static visual."""
    os.makedirs(os.path.dirname(output_clip_path), exist_ok=True)
    frames = int(duration * fps)
    
    # Zoom filter: gradual zoom from 1.0 to 1.15 centered on frame
    vf = (
        f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"zoompan=z='min(zoom+0.0012,1.20)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-t", f"{duration:.2f}",
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
        "-an",
        str(output_clip_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg Ken Burns failed: {res.stderr[:200]}")
    return output_clip_path

def create_color_gradient_fallback(output_img_path: str, color_hex: str = "#1e1b4b"):
    """Creates a high quality 1080x1920 vertical canvas fallback."""
    os.makedirs(os.path.dirname(output_img_path), exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={color_hex}:s=1080x1920:d=1",
        "-vframes", "1",
        str(output_img_path)
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_img_path

def compile_scenes_to_video_track(scenes: List[Dict[str, Any]], niche: str, output_track_path: str) -> str:
    """Renders all scene clips with Ken Burns zoom and stitches into a 1080x1920 video track."""
    os.makedirs(os.path.dirname(output_track_path), exist_ok=True)
    clip_paths = []
    
    backdrops = NICHE_BACKDROPS.get(niche, NICHE_BACKDROPS["biblical"])

    for idx, scene in enumerate(scenes):
        duration = float(scene.get("duration", 8))
        img_temp = TEMP_DIR / f"scene_{idx}_{niche}.jpg"
        clip_temp = TEMP_DIR / f"scene_clip_{idx}.mp4"

        # Download or create visual
        url = backdrops[idx % len(backdrops)]
        curl_cmd = ["curl", "-s", "-L", url, "-o", str(img_temp)]
        res = subprocess.run(curl_cmd, capture_output=True)
        
        if not os.path.exists(img_temp) or os.path.getsize(img_temp) < 1000:
            create_color_gradient_fallback(str(img_temp), "#0f172a")

        render_ken_burns_clip(str(img_temp), duration, str(clip_temp))
        clip_paths.append(str(clip_temp))

    # Concat all clips using ffmpeg concat demuxer
    concat_list_file = TEMP_DIR / "concat_clips.txt"
    with open(concat_list_file, "w") as f:
        for p in clip_paths:
            f.write(f"file '{p}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        str(output_track_path)
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return output_track_path
