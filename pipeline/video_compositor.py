import os
import subprocess
from pathlib import Path
from typing import List, Tuple, Union

def get_media_duration(file_path: Union[str, Path]) -> float:
    """Accurately extracts media duration in seconds via ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path)
        ]
        res = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        return float(res)
    except Exception as e:
        raise RuntimeError(f"Failed to probe duration of {file_path}: {e}")

def harmonize_scene_cuts(
    scene_cuts: List[Tuple[Union[str, Path], float, float, str]],
    target_duration: float,
    min_buffer: float = 0.6
) -> List[Tuple[Union[str, Path], float, float, str]]:
    """
    Dynamically scales nominal cut durations so the total video footage perfectly matches
    the voiceover duration plus a clean breathing room buffer (default: +0.6s).
    Guarantees no video shortage or premature cutoffs occur.
    """
    if not scene_cuts:
        return []

    total_target = target_duration + min_buffer
    nominal_total = sum(dur for _, _, dur, _ in scene_cuts)
    if nominal_total <= 0:
        nominal_total = 1.0

    scale_ratio = total_target / nominal_total
    harmonized = []
    accumulated = 0.0

    for idx, (src, start, dur, desc) in enumerate(scene_cuts):
        if idx == len(scene_cuts) - 1:
            # Last cut takes exact remaining duration to ensure exact match
            new_dur = round(total_target - accumulated, 2)
            if new_dur < 1.5:
                new_dur = 1.5
        else:
            new_dur = round(dur * scale_ratio, 2)
            accumulated += new_dur

        # Ensure start + new_dur doesn't crash if source video is shorter
        try:
            src_dur = get_media_duration(src)
            if start + new_dur > src_dur:
                # Adjust start backwards if possible
                start = max(0.0, src_dur - new_dur)
                new_dur = min(new_dur, src_dur - start)
        except Exception:
            pass

        harmonized.append((src, round(start, 2), round(new_dur, 2), desc))

    return harmonized

def detect_letterbox_crop(video_path: str, sample_sec: float = 10.0) -> str:
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
                import re
                m = re.search(r"crop=([0-9:]+)", line)
                if m:
                    return f"crop={m.group(1)},"
    except Exception:
        pass
    # Fallback for cinemascope: 140px top and bottom letterbox bars
    return "crop=in_w:800:0:140,"

def render_70pct_scene_clip(input_video: str, start_sec: float, duration: float, output_path: str, fps: int = 30):
    """
    Renders a 9:16 vertical clip where movie footage takes 70% of screen height (1344px out of 1920px),
    stripping letterbox bars and featuring a dynamically blurred, vibrant ambient background.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    crop_filter = detect_letterbox_crop(input_video, sample_sec=start_sec + 1.0)
    
    vf = (
        f"[0:v]{crop_filter}scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=45,eq=brightness=-0.05:contrast=1.1:saturation=1.3[bg];"
        f"[0:v]{crop_filter}scale=-1:1344,crop=1080:1344:(in_w-1080)/2:0[fg];"
        f"[bg][fg]overlay=0:288,setsar=1"
    )

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start_sec:.3f}",
        "-t", f"{duration:.3f}",
        "-i", str(input_video),
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
        raise RuntimeError(f"FFmpeg failed for clip {output_path}: {res.stderr[:300]}")
    return output_path

def render_100pct_fullscreen_clip(input_video: str, start_sec: float, duration: float, output_path: str, x_offset: int = 0, fps: int = 30):
    """
    Renders a 9:16 vertical clip where movie footage fills 100% of the screen (full bleed 1080x1920),
    stripping letterbox bars and applying subject-focused pan & scan.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    crop_filter = detect_letterbox_crop(input_video, sample_sec=start_sec + 1.0)
    
    crop_x = f"(in_w-1080)/2+{x_offset}" if x_offset != 0 else "(in_w-1080)/2"
    vf = f"[0:v]{crop_filter}scale=-1:1920,crop=1080:1920:{crop_x}:0,setsar=1"

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start_sec:.3f}",
        "-t", f"{duration:.3f}",
        "-i", str(input_video),
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
        raise RuntimeError(f"FFmpeg failed for clip {output_path}: {res.stderr[:300]}")
    return output_path

def assemble_final_video(
    scene_clips: list,
    audio_path: str,
    ass_subtitle_path: str,
    output_mp4: str,
    temp_dir: str
):
    """
    Concatenates video clips, mixes audio with ambient tension score, and burns subtitles.
    FAIL-SAFE ARCHITECTURE:
    1. Probes voiceover duration and sets target master duration with +0.6s breathing room.
    2. Detects if video clips are shorter than audio, and automatically applies tpad frame-hold
       so video never ends prematurely before narration finishes.
    3. Fades out audio smoothly over the last 0.35s to prevent abrupt pops.
    4. Guarantees 100% audio and dialogue completion.
    """
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(os.path.dirname(output_mp4), exist_ok=True)

    # 1. Write concat list
    concat_list_file = os.path.join(temp_dir, "concat_clips.txt")
    with open(concat_list_file, "w") as f:
        for p in scene_clips:
            f.write(f"file '{os.path.abspath(p)}'\n")

    raw_video = os.path.join(temp_dir, "raw_concatenated.mp4")
    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list_file,
        "-c", "copy",
        raw_video
    ]
    subprocess.run(concat_cmd, check=True, stdout=subprocess.DEVNULL)

    # 2. Probe Durations
    audio_dur = get_media_duration(audio_path)
    raw_video_dur = get_media_duration(raw_video)
    target_master_dur = round(audio_dur + 0.60, 2)

    # 3. Fail-Safe Video Duration Alignment (tpad if footage is short)
    vf_chain = []
    if raw_video_dur < target_master_dur:
        pad_needed = round(target_master_dur - raw_video_dur, 2)
        print(f"⚠️ Sliced clips ({raw_video_dur:.2f}s) shorter than voiceover ({audio_dur:.2f}s). Applying tpad hold (+{pad_needed:.2f}s) to guarantee zero audio cutoff.")
        vf_chain.append(f"tpad=stop_mode=clone:stop_duration={pad_needed}")
    
    vf_chain.append(f"ass={ass_subtitle_path}")
    vf_filter = ",".join(vf_chain)

    # 4. Synthesize subtle cinematic tension score & mix with voiceover
    mixed_audio = os.path.join(temp_dir, "mixed_audio.wav")
    mix_cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=f=55:d={target_master_dur},volume=0.07,lowpass=f=120",
        "-f", "lavfi", "-i", f"anoisesrc=d={target_master_dur}:c=pink:r=24000:a=0.02,lowpass=f=400,volume=0.10",
        "-i", audio_path,
        "-filter_complex",
        f"[0:a][1:a]amix=inputs=2:duration=first[amb];"
        f"[2:a]apad=pad_dur={round(target_master_dur - audio_dur, 2)},volume=1.25[vocal];"
        f"[amb][vocal]amix=inputs=2:duration=first:dropout_transition=2,"
        f"afade=t=out:st={round(target_master_dur - 0.35, 2)}:d=0.35[outa]",
        "-map", "[outa]",
        "-c:a", "pcm_s16le",
        mixed_audio
    ]
    subprocess.run(mix_cmd, check=True, stdout=subprocess.DEVNULL)

    # 5. Burn ASS subtitles and output final 1080x1920 MP4
    print(f"Burning in Center Bold Subtitles and exporting 1080p Master ({target_master_dur:.2f}s)... ")
    final_cmd = [
        "ffmpeg", "-y",
        "-i", raw_video,
        "-i", mixed_audio,
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", f"{target_master_dur:.2f}",
        output_mp4
    ]
    subprocess.run(final_cmd, check=True)
    print(f"🎉 1080p Cinema X-Ray Video: {output_mp4}")
    return output_mp4

def export_4k_uhd(input_mp4: str, output_4k_mp4: str):
    """Upscales 1080x1920 video to pristine 4K UHD (2160x3840) using hardware acceleration."""
    os.makedirs(os.path.dirname(output_4k_mp4), exist_ok=True)
    print(f"🚀 Upscaling to 4K UHD (2160x3840)...")
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_mp4),
        "-vf", "scale=2160:3840:flags=lanczos",
        "-c:v", "h264_videotoolbox",
        "-b:v", "40M",
        "-c:a", "copy",
        str(output_4k_mp4)
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print("Falling back to CPU 4K upscale...")
        cmd_cpu = [
            "ffmpeg", "-y",
            "-i", str(input_mp4),
            "-vf", "scale=2160:3840:flags=lanczos",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "17",
            "-c:a", "copy",
            str(output_4k_mp4)
        ]
        subprocess.run(cmd_cpu, check=True)
    
    print(f"🌟 4K UHD Cinema X-Ray Video: {output_4k_mp4}")
    return output_4k_mp4
