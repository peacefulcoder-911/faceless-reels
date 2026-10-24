"""
Cinema X-Ray Unified Brand Thumbnail Generator
Deterministic thumbnail engine using OpenCV, Pillow, and FFmpeg.
Enforces the exact same visual brand identity across the entire channel
for both Long-Form (1280x720, 16:9) and Shorts (1080x1920, 9:16).
"""

import os
import re
import cv2
import numpy as np
from pathlib import Path
from typing import Union, Optional, Tuple, List
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"
THUMBNAILS_LONG_DIR = OUTPUT_DIR / "thumbnails_long"
THUMBNAILS_SHORT_DIR = OUTPUT_DIR / "thumbnails_short"

# Signature Brand Palette
COLOR_GOLD = (255, 229, 0)         # Electric Gold #FFE500
COLOR_WHITE = (255, 255, 255)      # Pure White #FFFFFF
COLOR_BLACK = (0, 0, 0)            # Deep Black #000000
COLOR_HUD_BG = (10, 13, 20, 220)   # Dark Translucent HUD
COLOR_HUD_BORDER = (255, 229, 0, 160)


def _get_font(size: int, prefer_black: bool = True) -> ImageFont.FreeTypeFont:
    """Find and load high-impact bold typography (Arial Black or robust fallbacks)."""
    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
        "/Library/Fonts/Arial Black.ttf",
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/HelveticaNeue-Bold.otf",
        "/System/Library/Fonts/SFNSBold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    try:
        return ImageFont.truetype("arialbd.ttf", size)
    except Exception:
        return ImageFont.load_default()


def _get_mono_font(size: int) -> ImageFont.FreeTypeFont:
    """Find a sleek monospace/HUD font for technical telemetry."""
    mono_paths = [
        "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
        "/System/Library/Fonts/SFMono-Bold.otf",
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
    ]
    for p in mono_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return _get_font(size)


def extract_best_keyframe(
    video_path: Union[str, Path],
    start_sec: float = 0.0,
    end_sec: Optional[float] = None,
    sample_count: int = 15
) -> np.ndarray:
    """
    Samples frames from the video clip and calculates a composite score based on:
      1. Laplacian variance (sharpness / focus)
      2. Brightness penalties (never pick dark blackouts or overexposed white flash cuts)
      3. Contrast score (avoids flat, low-detail frames)
    
    Returns the highest-scoring frame as an RGB numpy array.
    """
    video_path = str(video_path)
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found for keyframe extraction: {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_duration = total_frames / fps if fps > 0 else 10.0

    if end_sec is None or end_sec > video_duration:
        end_sec = video_duration

    if end_sec <= start_sec:
        start_sec = 0.0
        end_sec = max(video_duration, 1.0)

    # Sample timestamps evenly
    timestamps = np.linspace(start_sec, end_sec, num=max(sample_count, 3))
    best_score = -1.0
    best_frame_rgb = None

    for t in timestamps:
        cap.set(cv2.CAP_PROP_POS_MSEC, float(t * 1000.0))
        ret, frame_bgr = cap.read()
        if not ret or frame_bgr is None:
            continue

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        
        # 1. Sharpness: Laplacian variance
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        
        # 2. Brightness distribution
        mean_brightness = float(np.mean(gray))
        
        # 3. Contrast: Standard deviation of pixel intensities
        contrast_std = float(np.std(gray))

        # Brightness penalty curve:
        # Heavily penalize dark transitions (mean < 35) and blown-out whites (mean > 230)
        if mean_brightness < 35.0:
            bright_factor = max(0.01, (mean_brightness / 35.0) ** 2)
        elif mean_brightness > 225.0:
            bright_factor = max(0.01, ((255.0 - mean_brightness) / 30.0) ** 2)
        else:
            bright_factor = 1.0

        # Contrast multiplier
        contrast_factor = np.clip(contrast_std / 45.0, 0.2, 1.8)

        # Composite score
        composite_score = laplacian_var * contrast_factor * bright_factor

        if composite_score > best_score:
            best_score = composite_score
            best_frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

    cap.release()

    if best_frame_rgb is None:
        # Fallback: create high-end dark gradient frame if no video frame was read
        print(f"[Thumbnail] Warning: Could not sample valid frame from {video_path}, creating procedural base.")
        best_frame_rgb = np.zeros((720, 1280, 3), dtype=np.uint8)
        best_frame_rgb[:, :] = [14, 18, 28]

    return best_frame_rgb


def _crop_and_resize_to_aspect(
    img: Image.Image,
    target_w: int,
    target_h: int
) -> Image.Image:
    """Smartly crops and resizes image to exact target dimensions without stretching."""
    orig_w, orig_h = img.size
    target_aspect = target_w / target_h
    orig_aspect = orig_w / orig_h

    if abs(orig_aspect - target_aspect) < 0.01:
        return img.resize((target_w, target_h), Image.Resampling.LANCZOS)

    if orig_aspect > target_aspect:
        # Source is wider than target: crop horizontally
        new_w = int(orig_h * target_aspect)
        left = (orig_w - new_w) // 2
        right = left + new_w
        cropped = img.crop((left, 0, right, orig_h))
    else:
        # Source is taller than target: crop vertically (keep slightly above center for cinematic heads)
        new_h = int(orig_w / target_aspect)
        top = max(0, int((orig_h - new_h) * 0.40))
        bottom = top + new_h
        cropped = img.crop((0, top, orig_w, bottom))

    return cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)


def _draw_hud_brackets(
    draw: ImageDraw.ImageDraw,
    width: int,
    height: int,
    margin: int = 36,
    arm_len: int = 50,
    line_w: int = 3,
    color: Tuple[int, int, int, int] = (255, 229, 0, 180)
):
    """Draws Cinema X-Ray signature HUD corner framing brackets."""
    # Top-Left
    draw.line([(margin, margin + arm_len), (margin, margin), (margin + arm_len, margin)], fill=color, width=line_w)
    # Top-Right
    draw.line([(width - margin - arm_len, margin), (width - margin, margin), (width - margin, margin + arm_len)], fill=color, width=line_w)
    # Bottom-Left
    draw.line([(margin, height - margin - arm_len), (margin, height - margin), (margin + arm_len, height - margin)], fill=color, width=line_w)
    # Bottom-Right
    draw.line([(width - margin - arm_len, height - margin), (width - margin, height - margin), (width - margin, height - margin - arm_len)], fill=color, width=line_w)


def _draw_focal_ring(
    draw: ImageDraw.ImageDraw,
    box: Tuple[int, int, int, int],
    hud_font: ImageFont.FreeTypeFont
):
    """Draws a subtle glowing gold analytical focus reticle around the focal region."""
    x1, y1, x2, y2 = box
    reticle_color = (255, 229, 0, 200)
    corner_arm = max(16, int((x2 - x1) * 0.20))
    line_w = 2

    # Corner brackets around focal box
    # Top-left
    draw.line([(x1, y1 + corner_arm), (x1, y1), (x1 + corner_arm, y1)], fill=reticle_color, width=line_w)
    # Top-right
    draw.line([(x2 - corner_arm, y1), (x2, y1), (x2, y1 + corner_arm)], fill=reticle_color, width=line_w)
    # Bottom-left
    draw.line([(x1, y2 - corner_arm), (x1, y2), (x1 + corner_arm, y2)], fill=reticle_color, width=line_w)
    # Bottom-right
    draw.line([(x2 - corner_arm, y2), (x2, y2), (x2, y2 - corner_arm)], fill=reticle_color, width=line_w)

    # Center crosshair
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    cross_len = 10
    draw.line([(cx - cross_len, cy), (cx + cross_len, cy)], fill=(255, 255, 255, 140), width=1)
    draw.line([(cx, cy - cross_len), (cx, cy + cross_len)], fill=(255, 255, 255, 140), width=1)

    # Telemetry text
    tag_text = "FOCAL ANALYSIS // LENS: 35mm"
    draw.text((x1 + 4, y1 - 16), tag_text, font=hud_font, fill=(255, 229, 0, 220))


def apply_cinema_xray_theme(
    frame_img: Union[Image.Image, np.ndarray, str, Path],
    hook_text: str,
    highlight_word: str = "",
    video_format: str = "LONG_5_6_MIN",
    output_path: Optional[Union[str, Path]] = None,
    job_slug: str = "cinema_xray",
    focal_box: Optional[Tuple[int, int, int, int]] = None
) -> str:
    """
    Applies the unified Cinema X-Ray brand styling to a keyframe:
      - Aspect ratio enforcement (1280x720 16:9 for Long-Form, 1080x1920 9:16 for Shorts)
      - Contrast and saturation grading (+18%)
      - Deep gradient vignette for 100% mobile text legibility
      - HUD framing brackets + [ CINEMA X-RAY ] badge
      - Analytical focal reticle
      - High-impact bold typography: highlight_word in Electric Gold (#FFE500), others in White,
        with 8px black stroke and deep drop shadow (contrast ratio > 7:1)
      - Ensures strictly under 2MB for YouTube API compatibility
    """
    # 1. Convert input to PIL Image
    if isinstance(frame_img, (str, Path)):
        img = Image.open(str(frame_img)).convert("RGB")
    elif isinstance(frame_img, np.ndarray):
        img = Image.fromarray(frame_img).convert("RGB")
    elif isinstance(frame_img, Image.Image):
        img = frame_img.convert("RGB")
    else:
        raise ValueError(f"Unsupported frame_img type: {type(frame_img)}")

    # 2. Determine target dimensions and destination paths
    if video_format == "LONG_5_6_MIN":
        target_w, target_h = 1280, 720
        default_dir = THUMBNAILS_LONG_DIR
    elif video_format == "SHORT_45_SEC":
        target_w, target_h = 1080, 1920
        default_dir = THUMBNAILS_SHORT_DIR
    else:
        target_w, target_h = 1280, 720
        default_dir = THUMBNAILS_LONG_DIR

    default_dir.mkdir(parents=True, exist_ok=True)
    if not output_path:
        output_path = default_dir / f"{job_slug}_thumb.jpg"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # 3. Crop & Resize to Target Aspect Ratio
    img = _crop_and_resize_to_aspect(img, target_w, target_h)

    # 4. Color Grading: Boost Contrast & Saturation (+18%)
    enhancer_color = ImageEnhance.Color(img)
    img = enhancer_color.enhance(1.18)
    enhancer_contrast = ImageEnhance.Contrast(img)
    img = enhancer_contrast.enhance(1.18)

    # 5. Build Vignette / Contrast Underlay Layer
    # Convert base to RGBA for clean overlay composition
    base_rgba = img.convert("RGBA")
    overlay = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    # Subtle radial vignette on edges
    # Bottom gradient underlay for typography
    if video_format == "LONG_5_6_MIN":
        # Gradient starting at 35% height down to 100% height
        grad_start = int(target_h * 0.32)
        grad_len = target_h - grad_start
        for y in range(grad_start, target_h):
            ratio = (y - grad_start) / max(grad_len, 1)
            # Smooth ease-in curve
            alpha = int(225 * (ratio ** 1.35))
            overlay_draw.line([(0, y), (target_w, y)], fill=(6, 8, 14, alpha))

        # Subtle top gradient for HUD badge
        for y in range(0, int(target_h * 0.16)):
            ratio = 1.0 - (y / (target_h * 0.16))
            alpha = int(140 * ratio)
            overlay_draw.line([(0, y), (target_w, y)], fill=(6, 8, 14, alpha))

    else:
        # Shorts (9:16): dark gradient in middle/lower sections
        grad_start = int(target_h * 0.38)
        grad_len = int(target_h * 0.40)
        for y in range(grad_start, grad_start + grad_len):
            ratio = (y - grad_start) / max(grad_len, 1)
            alpha = int(210 * (ratio ** 1.2))
            overlay_draw.line([(0, y), (target_w, y)], fill=(6, 8, 14, alpha))

        # Top gradient for HUD
        for y in range(0, int(target_h * 0.14)):
            ratio = 1.0 - (y / (target_h * 0.14))
            alpha = int(170 * ratio)
            overlay_draw.line([(0, y), (target_w, y)], fill=(6, 8, 14, alpha))

    # 6. Draw HUD Framing Elements
    _draw_hud_brackets(overlay_draw, target_w, target_h, margin=32, arm_len=45, line_w=3)

    mono_font_sm = _get_mono_font(16 if video_format == "LONG_5_6_MIN" else 22)

    # Top-Left [ CINEMA X-RAY ] Badge
    badge_x = 42
    badge_y = 38 if video_format == "LONG_5_6_MIN" else 75
    badge_text = "[ CINEMA X-RAY ]"
    badge_sub = "ANALYTICAL DECONSTRUCTION"

    # Pill background for badge
    bbox = mono_font_sm.getbbox(f"{badge_text}  {badge_sub}")
    bw = (bbox[2] - bbox[0]) + 24
    bh = (bbox[3] - bbox[1]) + 16
    overlay_draw.rounded_rectangle(
        [(badge_x, badge_y), (badge_x + bw, badge_y + bh)],
        radius=6,
        fill=COLOR_HUD_BG,
        outline=COLOR_HUD_BORDER,
        width=1
    )
    overlay_draw.text((badge_x + 12, badge_y + 8), badge_text, font=mono_font_sm, fill=COLOR_GOLD)
    overlay_draw.text((badge_x + 12 + mono_font_sm.getbbox(badge_text + " ")[2], badge_y + 8), badge_sub, font=mono_font_sm, fill=(200, 210, 225, 220))

    # Analytical Focal Box / Reticle
    if focal_box is None:
        # Default analytical focal box in upper-third / subject zone
        if video_format == "LONG_5_6_MIN":
            focal_box = (int(target_w * 0.38), int(target_h * 0.18), int(target_w * 0.62), int(target_h * 0.46))
        else:
            focal_box = (int(target_w * 0.25), int(target_h * 0.22), int(target_w * 0.75), int(target_h * 0.42))

    _draw_focal_ring(overlay_draw, focal_box, mono_font_sm)

    # Composite overlay on graded base
    composed = Image.alpha_composite(base_rgba, overlay)
    draw_final = ImageDraw.Draw(composed)

    # 7. Signature Typography
    # Clean and restrict hook_text to 2-4 punchy words
    clean_words = [re.sub(r"[^\w\'-]", "", w).upper() for w in hook_text.strip().split() if w.strip()]
    if len(clean_words) > 4:
        # Strictly 2-4 punchy words maximum
        clean_words = clean_words[:4]
    elif len(clean_words) < 2 and hook_text:
        clean_words = [w.upper() for w in hook_text.strip().split()][:4]

    clean_highlight = re.sub(r"[^\w\'-]", "", highlight_word).upper().strip()

    # Font sizing & line structuring
    if video_format == "LONG_5_6_MIN":
        font_size = 78
        impact_font = _get_font(font_size)
        
        # Test if words fit on a single line or 2 lines
        full_line = " ".join(clean_words)
        test_box = draw_final.textbbox((0, 0), full_line, font=impact_font, stroke_width=8)
        text_w = test_box[2] - test_box[0]
        
        if text_w > (target_w - 180) and len(clean_words) >= 3:
            # Split into 2 lines
            mid = len(clean_words) // 2
            lines = [clean_words[:mid], clean_words[mid:]]
        else:
            lines = [clean_words]

        # Calculate Y position (lower third)
        line_height = int(font_size * 1.15)
        total_text_h = len(lines) * line_height
        start_y = target_h - total_text_h - 45

    else:
        # Shorts (9:16): Large stacked typography in upper-middle zone
        font_size = 108
        impact_font = _get_font(font_size)
        
        if len(clean_words) >= 3:
            mid = (len(clean_words) + 1) // 2
            lines = [clean_words[:mid], clean_words[mid:]]
        else:
            lines = [clean_words]

        line_height = int(font_size * 1.20)
        total_text_h = len(lines) * line_height
        start_y = int(target_h * 0.52) - (total_text_h // 2)

    # Render each line with Electric Gold highlight + Pure White remaining words
    curr_y = start_y
    stroke_w = 8
    shadow_offset = (6, 6)

    for line_words in lines:
        # Compute exact word dimensions with space
        space_w = draw_final.textbbox((0, 0), " ", font=impact_font, stroke_width=stroke_w)[2]
        word_metrics = []
        total_line_w = 0

        for idx, w in enumerate(line_words):
            bbox = draw_final.textbbox((0, 0), w, font=impact_font, stroke_width=stroke_w)
            w_width = bbox[2] - bbox[0]
            word_metrics.append((w, w_width))
            total_line_w += w_width
            if idx < len(line_words) - 1:
                total_line_w += space_w

        # Center horizontally
        curr_x = (target_w - total_line_w) // 2

        for idx, (w, w_width) in enumerate(word_metrics):
            # Check highlight word match
            is_highlight = (clean_highlight and (clean_highlight == w or clean_highlight in w))
            word_color = COLOR_GOLD if is_highlight else COLOR_WHITE

            # 1. Deep Drop Shadow (Offset +6, +6)
            sx = curr_x + shadow_offset[0]
            sy = curr_y + shadow_offset[1]
            draw_final.text(
                (sx, sy),
                w,
                font=impact_font,
                fill=COLOR_BLACK,
                stroke_width=stroke_w + 2,
                stroke_fill=COLOR_BLACK
            )

            # 2. Main Text with Thick 8px Black Stroke
            draw_final.text(
                (curr_x, curr_y),
                w,
                font=impact_font,
                fill=word_color,
                stroke_width=stroke_w,
                stroke_fill=COLOR_BLACK
            )

            curr_x += w_width + space_w

        curr_y += line_height

    # 8. Save and Enforce Size Limit (< 2MB strictly for YouTube API)
    rgb_final = composed.convert("RGB")
    quality = 93
    max_bytes = 1_950_000  # Strictly under 2,000,000 bytes

    while quality >= 65:
        rgb_final.save(str(output_path), "JPEG", quality=quality, optimize=True)
        size_bytes = os.path.getsize(str(output_path))
        if size_bytes <= max_bytes:
            break
        quality -= 5

    final_size_mb = os.path.getsize(str(output_path)) / (1024 * 1024)
    print(f"✅ Generated Cinema X-Ray Thumbnail [{video_format}]:")
    print(f"   Path: {output_path}")
    print(f"   Resolution: {target_w}x{target_h}")
    print(f"   File Size:  {final_size_mb:.2f} MB (< 2.0 MB YouTube limit)")

    return str(output_path)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cinema X-Ray Thumbnail Generator")
    parser.add_argument("--video", type=str, help="Source video clip to extract keyframe from")
    parser.add_argument("--hook", type=str, default="WHY THANOS WAS BROKEN", help="Punchy hook text (2-4 words)")
    parser.add_argument("--highlight", type=str, default="BROKEN", help="Word to highlight in Electric Gold")
    parser.add_argument("--format", choices=["LONG_5_6_MIN", "SHORT_45_SEC"], default="LONG_5_6_MIN", help="Video format")
    parser.add_argument("--slug", type=str, default="test_sample", help="Job slug")
    args = parser.parse_args()

    if args.video and os.path.exists(args.video):
        print(f"[Thumbnail Generator] Extracting best keyframe from {args.video}...")
        frame = extract_best_keyframe(args.video, 0.0, 10.0)
    else:
        # Procedural fallback test frame
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame[:, :] = [30, 35, 50]

    out = apply_cinema_xray_theme(
        frame_img=frame,
        hook_text=args.hook,
        highlight_word=args.highlight,
        video_format=args.format,
        job_slug=args.slug
    )
    print(f"Result thumbnail: {out}")
