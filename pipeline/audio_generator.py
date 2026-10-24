"""
Cinema X-Ray: Studio Audio Generator
Synthesizes studio-quality 'Achird' voiceover via Gemini TTS with broadcast loudness normalization.
Supports:
  - SHORT_45_SEC: Single-shot high-retention Achird delivery (~40-52s).
  - LONG_5_6_MIN: Chapter-safe partitioned synthesis (5 chapters) with 0.30s acoustic breaths.
Mastered via FFmpeg EBU R128 Loudness Normalization (I=-14 LUFS, TP=-1.5 dB, LRA=11).
"""

import os
import wave
import json
import subprocess
from pathlib import Path
from typing import Union, Dict, Any, List
from google import genai
from google.genai import types

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_env():
    p = REPO_ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
_load_env()


def _get_api_client():
    api_key = os.environ.get("GEMINI_API_KEY", "AIzaSyDStjE_IOWgo7NWUSqrxHi3KBki2Rfyk0k")
    return genai.Client(api_key=api_key)



ELEVENLABS_VOICES = {
    "brian": "nPczCjzI2devNBz1zQrb",   # Deep, Resonant, Analytical (Cinema X-Ray Video Essay)
    "adam": "pNInz6obpgDQGcFmaJgB",    # Dominant, Firm, Dramatic
    "roger": "CwhRBWXzGAHq8TQ4Fs17",   # Resonant, Casual
    "george": "JBFqnCBsd6RMkjVDRZzb",  # British Storyteller
}

def _synthesize_elevenlabs_tts(script_text: str, temp_wav_path: str, voice_name: str = "brian") -> None:
    """Synthesizes audio using ElevenLabs REST API and converts to 24kHz mono PCM WAV."""
    import requests
    api_key = os.environ.get("ELEVENLABS_API_KEY", "sk_5bee36c5d62728dc6c787af78d15981d7112dce3882a1d74")
    voice_id = ELEVENLABS_VOICES.get(voice_name.lower(), voice_name)
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": script_text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.0,
            "use_speaker_boost": True
        }
    }
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    print(f"[ElevenLabs TTS] Generating audio with voice '{voice_name}'...")
    res = requests.post(url, json=payload, headers=headers)
    if res.status_code != 200:
        raise RuntimeError(f"ElevenLabs API failed ({res.status_code}): {res.text}")
    
    os.makedirs(os.path.dirname(temp_wav_path), exist_ok=True)
    temp_mp3 = temp_wav_path + ".temp.mp3"
    with open(temp_mp3, "wb") as f:
        f.write(res.content)
    
    # Convert MP3 to 24kHz mono PCM WAV
    subprocess.run([
        "ffmpeg", "-y", "-v", "quiet",
        "-i", temp_mp3,
        "-ar", "24000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        temp_wav_path
    ], check=True)
    if os.path.exists(temp_mp3):
        os.remove(temp_mp3)

def _synthesize_raw_tts(script_text: str, temp_wav_path: str) -> None:
    """Invokes Gemini TTS for Achird voice and saves raw 24kHz mono PCM WAV."""
    client = _get_api_client()
    models_to_try = ["gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts"]

    prompt_content = f"Read aloud verbatim: {script_text}"

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt_content)]
        )
    ]

    config = types.GenerateContentConfig(
        temperature=0.85,
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Achird")
            )
        )
    )

    last_err = None
    for m in models_to_try:
        try:
            print(f"[Gemini TTS] Connecting to {m} (Achird)...")
            resp = client.models.generate_content(model=m, contents=contents, config=config)
            if resp.candidates and resp.candidates[0].content.parts:
                part = resp.candidates[0].content.parts[0]
                if part.inline_data and part.inline_data.data:
                    raw_data = part.inline_data.data
                    os.makedirs(os.path.dirname(temp_wav_path), exist_ok=True)
                    with wave.open(temp_wav_path, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(24000)
                        wf.writeframes(raw_data)
                    return
        except Exception as e:
            print(f"[Gemini TTS] Model {m} note: {e}")
            last_err = e

    print(f"[Gemini TTS] Warning: Online TTS failed ({last_err}). Falling back to local studio voice (Samantha)...")
    try:
        aiff_path = temp_wav_path + ".aiff"
        voice = "Samantha"
        subprocess.run(["say", "-v", voice, "-o", aiff_path, script_text], check=True)
        subprocess.run([
            "ffmpeg", "-y", "-v", "quiet",
            "-i", aiff_path,
            "-ar", "24000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            temp_wav_path
        ], check=True)
        if os.path.exists(aiff_path):
            os.remove(aiff_path)
        return
    except Exception as fallback_err:
        raise RuntimeError(f"Gemini TTS synthesis and system fallback both failed: {last_err} | {fallback_err}")


def _apply_loudness_normalization(input_wav: str, output_wav: str) -> None:
    """Master audio using FFmpeg EBU R128 loudnorm filter (I=-14, TP=-1.5, LRA=11)."""
    os.makedirs(os.path.dirname(output_wav), exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-v", "quiet",
        "-i", input_wav,
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
        "-ar", "24000",
        "-c:a", "pcm_s16le",
        output_wav
    ]
    subprocess.run(cmd, check=True)


def verify_audio_file(audio_path: str, video_format: str = "SHORT_45_SEC") -> float:
    """Verifies audio integrity, non-zero size, valid headers, and duration bounds."""
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1000:
        raise ValueError(f"Master audio file missing or truncated: {audio_path}")

    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    dur = float(res.stdout.strip())

    if video_format == "SHORT_45_SEC":
        if not (30.0 <= dur <= 65.0):
            print(f"[Audio Warning] Short duration {dur:.2f}s is outside ideal target (35-58s)")
    elif video_format == "LONG_5_6_MIN":
        if not (250.0 <= dur <= 430.0):
            print(f"[Audio Warning] Long-form duration {dur:.2f}s is outside ideal target (270-400s)")

    return dur


def generate_achird_audio(
    script_input: Union[str, Path, Dict[str, Any]],
    output_path: str,
    video_format: str = "SHORT_45_SEC",
    provider: str = None,
    elevenlabs_voice: str = "brian"
) -> float:
    """
    Generates studio-quality Achird voiceover with loudness normalization and smart caching.
    Supports:
      - Plain text string or SHORT_45_SEC: Single-shot synthesis.
      - LONG_5_6_MIN or manifest dictionary/path: Chapter-safe synthesis across 5 chapters with 0.30s pauses.
    """
    output_path = str(output_path)
    temp_dir = Path(output_path).parent / "temp_tts"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Detect if script_input is a manifest path or manifest dictionary
    manifest_data = None
    if isinstance(script_input, (str, Path)) and str(script_input).endswith(".json") and os.path.exists(str(script_input)):
        with open(str(script_input), "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
    elif isinstance(script_input, dict) and "beats" in script_input:
        manifest_data = script_input

    if manifest_data:
        video_format = manifest_data.get("video_format", video_format)

    # 1. Check Smart Disk Cache
    if os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
        try:
            dur = verify_audio_file(output_path, video_format)
            print(f"✅ Reusing existing mastered voiceover: {output_path} ({dur:.2f}s)")
            return dur
        except Exception:
            pass

    # 2. SHORT_45_SEC (or plain string) -> Single-shot generation
    if video_format == "SHORT_45_SEC" or not manifest_data:
        if manifest_data:
            script_text = " ".join(b["narration_text"].strip() for b in manifest_data["beats"])
        elif isinstance(script_input, (str, Path)) and os.path.exists(str(script_input)) and not str(script_input).endswith(".json"):
            script_text = Path(script_input).read_text(encoding="utf-8").strip()
        else:
            script_text = str(script_input).strip()

        raw_unmastered = str(temp_dir / f"raw_{Path(output_path).stem}.wav")
        if provider == "elevenlabs":
            _synthesize_elevenlabs_tts(script_text, raw_unmastered, voice_name=elevenlabs_voice)
        else:
            _synthesize_raw_tts(script_text, raw_unmastered)

        print("[Audio Mastering] Normalizing loudness to broadcast standard (-14 LUFS)...")
        _apply_loudness_normalization(raw_unmastered, output_path)

    # 3. LONG_5_6_MIN -> Partitioned 5-Chapter synthesis with 0.30s breath gaps
    else:
        beats = manifest_data.get("beats", [])
        # Group beats by chapter_num
        chapters_dict: Dict[int, List[str]] = {}
        for b in beats:
            c_num = b.get("chapter_num", 1)
            chapters_dict.setdefault(c_num, []).append(b["narration_text"].strip())

        chapter_keys = sorted(chapters_dict.keys())
        print(f"[Long-Form TTS] Synthesizing {len(chapter_keys)} distinct chapters for {manifest_data.get('title')}...")

        # Generate 0.30s silence breath WAV
        silence_wav = temp_dir / "silence_0_30s.wav"
        subprocess.run([
            "ffmpeg", "-y", "-v", "quiet",
            "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
            "-t", "0.30", "-c:a", "pcm_s16le", str(silence_wav)
        ], check=True)

        chapter_wavs = []
        for ch_idx, ch_num in enumerate(chapter_keys, start=1):
            ch_text = " ".join(chapters_dict[ch_num])
            ch_wav = temp_dir / f"chapter_{ch_num:02d}_{Path(output_path).stem}.wav"

            # Check chapter cache
            if not ch_wav.exists() or ch_wav.stat().st_size < 5000:
                print(f"  🎙️ Synthesizing Chapter {ch_idx}/{len(chapter_keys)} ({len(ch_text.split())} words)...")
                if provider == "elevenlabs":
                    _synthesize_elevenlabs_tts(ch_text, str(ch_wav), voice_name=elevenlabs_voice)
                else:
                    _synthesize_raw_tts(ch_text, str(ch_wav))
            else:
                print(f"  ♻️ Reusing cached Chapter {ch_idx}/{len(chapter_keys)}...")

            chapter_wavs.append(str(ch_wav))

        # Build FFmpeg concat list with natural 0.30s breaths between chapters
        concat_list_file = temp_dir / f"concat_{Path(output_path).stem}.txt"
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for idx, cw in enumerate(chapter_wavs):
                f.write(f"file '{cw}'\n")
                if idx < len(chapter_wavs) - 1:
                    f.write(f"file '{silence_wav}'\n")

        stitched_unmastered = temp_dir / f"stitched_{Path(output_path).stem}.wav"
        subprocess.run([
            "ffmpeg", "-y", "-v", "quiet",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list_file),
            "-c:a", "pcm_s16le", str(stitched_unmastered)
        ], check=True)

        print("[Audio Mastering] Normalizing Long-Form audio to broadcast standard (-14 LUFS)...")
        _apply_loudness_normalization(str(stitched_unmastered), output_path)

    # 4. Final Gatekeeper Verification
    dur = verify_audio_file(output_path, video_format)
    print(f"✅ Voiceover Mastered & Verified: {output_path} ({dur:.2f}s | {video_format})")
    return dur


if __name__ == "__main__":
    test_script = "In Age of Ultron, when Steve Rogers barely nudged Thor's hammer, Thor's smile instantly vanished."
    dur = generate_achird_audio(test_script, "/tmp/test_achird_short.wav")
    print(f"Short test duration: {dur:.2f}s")

def generate_elevenlabs_audio(
    script_input: Union[str, Path, Dict[str, Any]],
    output_path: str,
    voice_name: str = "brian",
    video_format: str = "SHORT_45_SEC"
) -> float:
    """Generates broadcast-mastered ElevenLabs audio for Short-Form or Long-Form."""
    return generate_achird_audio(
        script_input=script_input,
        output_path=output_path,
        video_format=video_format,
        provider="elevenlabs",
        elevenlabs_voice=voice_name
    )
