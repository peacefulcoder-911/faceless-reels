import os
import uuid
import urllib.parse
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"
TEMP_DIR = OUTPUT_DIR / "temp"
CLIPS_DIR = OUTPUT_DIR / "clips"
SCENE_IMAGES_DIR = OUTPUT_DIR / "scene_images"

for d in [TEMP_DIR, CLIPS_DIR, SCENE_IMAGES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

NICHE_STYLES = {
    "biblical": "ancient biblical era, dramatic chiaroscuro oil painting, divine golden rays, renaissance masterpiece, hyper-detailed",
    "anime": "makoto shinkai ufotable anime visual, vibrant colors, glowing highlights, atmospheric aesthetic, cinematic anime",
    "heists": "gritty cinematic 35mm film still, david fincher noir lighting, high suspense, moody realistic photography",
    "mythology": "epic mythic fantasy concept art, glowing celestial runes, towering ancient monuments, artstation trending",
    "school_gossip": "vibrant 2D modern webtoon storytime illustration, expressive characters, colorful comic aesthetic",
    "scary_stories": "creepy analog horror, liminal space aesthetic, eerie darkness, atmospheric flashlight illumination",
    "history": "baroque royal portrait, grand opulent palace hall, regal golden drapery, historical museum masterpiece",
    "kindness": "warm 3D pixar disney animation style, emotional expressive characters, soft golden hour lighting, cinematic render"
}

def generate_ai_scene_image(prompt: str, niche: str, output_path: str) -> str:
    """
    Generates a 9:16 vertical AI artwork tailored to the scene prompt and niche style.
    Uses high-speed FLUX neural synthesis with niche aesthetic conditioning.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    style_suffix = NICHE_STYLES.get(niche, NICHE_STYLES["biblical"])
    clean_prompt = prompt.replace("\n", " ").strip()
    full_prompt = f"{clean_prompt}, {style_suffix}, vertical 9:16 framing, highly detailed, 8k resolution"
    encoded_prompt = urllib.parse.quote(full_prompt)
    
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&model=flux&nologo=true"
    cmd = ["curl", "-s", "-L", "--max-time", "15", url, "-o", str(output_path)]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
        create_color_gradient_fallback(output_path, "#0f172a")

    return output_path

def render_ken_burns_clip(
    image_path: str,
    duration: float,
    output_clip_path: str,
    motion_type: int = 0,
    fps: int = 30
) -> str:
    """
    Renders dynamic vertical 1080x1920 Ken Burns motion editing from a scene image.
    Varies motion style (slow zoom-in, slow zoom-out, pan/tilt) for professional video rhythm.
    """
    os.makedirs(os.path.dirname(output_clip_path), exist_ok=True)
    frames = max(30, int(duration * fps))
    
    # 4 distinct cinematic motion presets for rhythm
    motion_index = motion_type % 4
    if motion_index == 0:
        # Slow Cinematic Zoom In: 1.0 -> 1.15
        zoom_filter = f"zoompan=z='min(zoom+0.0012,1.15)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}"
    elif motion_index == 1:
        # Slow Dramatic Zoom Out: 1.15 -> 1.01
        zoom_filter = f"zoompan=z='if(lte(zoom,1.0),1.15,max(1.001,zoom-0.0012))':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}"
    elif motion_index == 2:
        # Pan Downwards with subtle 1.1x zoom
        zoom_filter = f"zoompan=z='1.10':d={frames}:x='iw/2-(iw/zoom/2)':y='if(lte(on,1),0,min(ih-ih/zoom,y+0.6))':s=1080x1920:fps={fps}"
    else:
        # Climax Dramatic Push-In: 1.0 -> 1.20
        zoom_filter = f"zoompan=z='min(zoom+0.0016,1.20)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}"

    vf = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{zoom_filter}"

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

def compile_scenes_to_video_track(
    scenes: List[Dict[str, Any]],
    niche: str,
    output_track_path: str,
    target_total_duration: Optional[float] = None
) -> str:
    """
    Renders custom AI images for every scene matching the exact story narrative,
    animates each scene with Ken Burns motion, and stitches them into a 1080x1920 video track.
    If target_total_duration is provided, durations are normalized to match audio precisely.
    """
    os.makedirs(os.path.dirname(output_track_path), exist_ok=True)
    num_scenes = max(1, len(scenes))
    
    # Calculate scene durations
    if target_total_duration and target_total_duration > 0:
        base_dur = target_total_duration / num_scenes
        durations = [base_dur] * num_scenes
    else:
        durations = [float(s.get("duration", 8)) for s in scenes]

    clip_paths = []

    for idx, scene in enumerate(scenes):
        duration = durations[idx]
        scene_prompt = scene.get("visualPrompt") or scene.get("text") or f"scene {idx + 1}"
        
        # 1. Check if scene already has an approved/generated image
        img_url = scene.get("imageUrl")
        chosen_img_path = None
        if img_url:
            clean_name = os.path.basename(img_url)
            candidate = SCENE_IMAGES_DIR / clean_name
            if candidate.exists() and candidate.stat().st_size > 1000:
                chosen_img_path = str(candidate)

        # 2. If no image yet, generate AI scene art matching the theme & story beat
        if not chosen_img_path:
            img_file = SCENE_IMAGES_DIR / f"scene_{uuid.uuid4().hex[:6]}_{idx}_{niche}.jpg"
            generate_ai_scene_image(scene_prompt, niche, str(img_file))
            chosen_img_path = str(img_file)

        # 3. Render Ken Burns animated clip with motion preset
        clip_temp = TEMP_DIR / f"clip_{uuid.uuid4().hex[:6]}_{idx}.mp4"
        render_ken_burns_clip(chosen_img_path, duration, str(clip_temp), motion_type=idx)
        clip_paths.append(str(clip_temp))

    # 4. Concat all scene clips seamlessly into video track
    concat_list_file = TEMP_DIR / f"concat_{uuid.uuid4().hex[:6]}.txt"
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
