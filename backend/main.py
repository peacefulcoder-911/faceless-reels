import os
import glob
import json
import uuid
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="FacelessReels Engine API", version="1.0.0")

# Enable CORS for the Vite frontend (port 5173 / localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
FINAL_VIDEO_DIR = os.path.join(OUTPUT_DIR, "final_video")
STATE_DIR = os.path.join(OUTPUT_DIR, "state")
os.makedirs(STATE_DIR, exist_ok=True)

SCENE_IMAGES_DIR = os.path.join(OUTPUT_DIR, "scene_images")
os.makedirs(SCENE_IMAGES_DIR, exist_ok=True)

# Mount video and scene images directory
if os.path.exists(FINAL_VIDEO_DIR):
    app.mount("/videos", StaticFiles(directory=FINAL_VIDEO_DIR), name="videos")
app.mount("/scene-images", StaticFiles(directory=SCENE_IMAGES_DIR), name="scene_images")

# In-memory / persisted jobs store
JOBS_FILE = os.path.join(STATE_DIR, "active_jobs.json")

def load_jobs():
    if os.path.exists(JOBS_FILE):
        try:
            with open(JOBS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_jobs(jobs):
    with open(JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2)

NICHES = [
    {
        "id": "biblical",
        "name": "Biblical Stories",
        "badge": "Epic & Sacred",
        "description": "Dramatic tales of ancient miracles, fallen kingdoms, and timeless scripture.",
        "style": "Renaissance Oil Painting / Dramatic Chiaroscuro",
        "sampleHooks": [
            "What happened during the 3 days of total darkness in Egypt?",
            "The chilling truth about the Garden of Eden nobody mentions...",
            "Why Lucifer's name was never meant to be spoken aloud."
        ],
        "defaultPrompt": "Ancient biblical narrative, dramatic rays of light, hyper-detailed oil painting style, 8k vertical cinema",
        "color": "#eab308"
    },
    {
        "id": "anime",
        "name": "Anime Stories",
        "badge": "Action & Shonen",
        "description": "Heart-pounding anime lore, unseen side stories, and power level breakdowns.",
        "style": "Modern Ufotable / Studio Mappa Anime Art",
        "sampleHooks": [
            "The cursed swordsman who refused to die for 300 years.",
            "What really happens inside the void between anime dimensions?",
            "The forbidden technique that erased an entire clan from memory."
        ],
        "defaultPrompt": "Makoto Shinkai style, vibrant anime visual, glowing katana blade, atmospheric rain, neon highlights",
        "color": "#ec4899"
    },
    {
        "id": "heists",
        "name": "Heists & True Crime",
        "badge": "Suspense & High Stakes",
        "description": "Mind-bending bank robberies, genius cons, and FBI cold cases.",
        "style": "Cinematic 35mm Grain / Fincher Noir",
        "sampleHooks": [
            "How 4 men stole $100M from the world's most secure vault without triggering one alarm.",
            "The counterfeit master that the Secret Service couldn't catch for 20 years.",
            "The midnight diamond exchange that went completely silent."
        ],
        "defaultPrompt": "Cinematic 35mm film photography, low key lighting, suspenseful heist in security vault, gritty realism",
        "color": "#06b6d4"
    },
    {
        "id": "mythology",
        "name": "Mythology & Legends",
        "badge": "Gods & Monsters",
        "description": "Greek, Norse, and Egyptian myths with ferocious creatures and ancient prophecies.",
        "style": "Mythic Dark Fantasy / Concept Art",
        "sampleHooks": [
            "Why the Greek gods feared Typhon more than Tartarus itself.",
            "The forgotten Valkyrie who defied Odin's final command.",
            "The beast sleeping beneath the Antarctic ice sheets."
        ],
        "defaultPrompt": "Epic dark fantasy illustration, towering mythological beast, glowing runes, celestial lighting",
        "color": "#8b5cf6"
    },
    {
        "id": "school_gossip",
        "name": "School Gossip & Drama",
        "badge": "Viral Storytime",
        "description": "Relatable, spicy, and suspenseful teenage storytimes with instant retention.",
        "style": "Modern Webtoon / Cartoon Comic Illustration",
        "sampleHooks": [
            "I found out my roommate had an identical twin taking her exams...",
            "The anonymous confessions account that brought our whole school to a halt.",
            "She swapped my perfume on prom night and regretted it instantly."
        ],
        "defaultPrompt": "Vibrant webtoon 2D digital art, expressive anime teen character, colorful pastel background",
        "color": "#f97316"
    },
    {
        "id": "scary_stories",
        "name": "Scary Stories & Horror",
        "badge": "Chilling Creepypasta",
        "description": "Nightmarish encounters, liminal spaces, and late-night mysteries.",
        "style": "Analog Horror / Creepy Eerie Realism",
        "sampleHooks": [
            "If your GPS tells you to take Exit 73 at 3:14 AM... don't.",
            "My baby monitor started picking up a voice reading bedtime stories.",
            "The deep sea expedition that pulled up a locked iron cage."
        ],
        "defaultPrompt": "Analog horror aesthetic, flashlight illuminating abandoned wooden cabin hallway, eerie suspense",
        "color": "#ef4444"
    },
    {
        "id": "history",
        "name": "Historical Enigmas",
        "badge": "Royal Scandals & Empires",
        "description": "Bizarre ruler decrees, forgotten battles, and ancient secrets.",
        "style": "Regal Oil Portrait / Archival Masterpiece",
        "sampleHooks": [
            "The European king who danced himself into exhaustion for 3 days.",
            "The Roman secret weapon that could burn ships on open water.",
            "Why this royal family was erased from all stone inscriptions."
        ],
        "defaultPrompt": "Opulent royal palace hall, king sitting on ornate gold throne, dramatic baroque lighting, ultra-detailed",
        "color": "#d97706"
    },
    {
        "id": "kindness",
        "name": "Acts of Kindness",
        "badge": "Heartwarming & Wholesome",
        "description": "Tearjerker stories of everyday heroes and heartwarming surprises.",
        "style": "3D Pixar / Disney Cinematic Render",
        "sampleHooks": [
            "He secretly paid off every single medical bill in his neighborhood.",
            "A homeless puppy protected a lost little girl in the woods all night.",
            "The elderly waitress who received an envelope containing $50,000."
        ],
        "defaultPrompt": "Warm 3D Pixar animation style, emotional character expression, soft golden hour lighting, cinematic render",
        "color": "#10b981"
    }
]

VOICES = [
    {"id": "deep_narrator", "name": "Marcus (Deep Cinematic Male)", "gender": "Male", "tone": "Authoritative, Dramatic, Deep"},
    {"id": "storyteller_female", "name": "Elena (Captivating Storyteller)", "gender": "Female", "tone": "Warm, Engaging, Expressive"},
    {"id": "anime_protagonist", "name": "Ren (Intense Anime Voice)", "gender": "Male", "tone": "High Energy, Dramatic, Youthful"},
    {"id": "horror_whisper", "name": "Vincent (Dark & Eerie)", "gender": "Male", "tone": "Suspenseful, Chilling, Low"},
    {"id": "friendly_creator", "name": "Chloe (Viral TikTok Vlogger)", "gender": "Female", "tone": "Upbeat, Casual, High Energy"}
]

CAPTION_STYLES = [
    {
        "id": "mrbeast",
        "name": "MrBeast Viral Gold",
        "font": "Komika Axis / Impact",
        "textColor": "#FFFFFF",
        "highlightColor": "#FACC15",
        "border": "3px black",
        "animation": "bounce"
    },
    {
        "id": "neon_emerald",
        "name": "Neon Emerald",
        "font": "Montserrat Black",
        "textColor": "#FFFFFF",
        "highlightColor": "#10B981",
        "border": "3px black",
        "animation": "pop"
    },
    {
        "id": "cyberpunk_cyan",
        "name": "Cyberpunk Cyan",
        "font": "Outfit ExtraBold",
        "textColor": "#FFFFFF",
        "highlightColor": "#06B6D4",
        "border": "2px #0f172a",
        "animation": "glow"
    },
    {
        "id": "fire_ruby",
        "name": "Blood Red Alert",
        "font": "Arial Black",
        "textColor": "#FFFFFF",
        "highlightColor": "#EF4444",
        "border": "3px black",
        "animation": "pulse"
    }
]

class ScriptRequest(BaseModel):
    niche: str
    topic: str
    targetDuration: int = 45 # seconds
    tone: Optional[str] = "suspenseful"

class VideoCreationRequest(BaseModel):
    niche: str
    topic: str
    script: str
    voiceId: str
    captionStyleId: str
    bgmMood: str = "cinematic_suspense"
    autoPublish: bool = False
    channels: List[str] = []
    scenes: Optional[List[Dict[str, Any]]] = None

@app.get("/api/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/niches")
def get_niches():
    return {"niches": NICHES}

@app.get("/api/options")
def get_options():
    return {
        "niches": NICHES,
        "voices": VOICES,
        "captionStyles": CAPTION_STYLES,
        "bgmMoods": [
            {"id": "cinematic_suspense", "name": "Cinematic Suspense & Tension"},
            {"id": "epic_orchestral", "name": "Epic Orchestral & War Drums"},
            {"id": "dark_synthwave", "name": "Dark Synthwave & Cyberpunk"},
            {"id": "emotional_piano", "name": "Heartwarming Emotional Piano"},
            {"id": "lofi_mystery", "name": "Lo-Fi Mystery & Ambience"}
        ]
    }

from backend.pipeline_bridge import (
    generate_script_engine,
    synthesize_audio_engine,
    generate_subtitles_engine,
    assemble_reel_engine
)

class SceneImageRequest(BaseModel):
    prompt: str
    niche: str = "biblical"

@app.post("/api/generate-scene-image")
def generate_single_scene_image(req: SceneImageRequest):
    from backend.scene_visualizer import generate_ai_scene_image
    filename = f"preview_{uuid.uuid4().hex[:8]}.jpg"
    out_path = os.path.join(SCENE_IMAGES_DIR, filename)
    generate_ai_scene_image(req.prompt, req.niche, out_path)
    return {"imageUrl": f"/scene-images/{filename}"}

@app.post("/api/generate-script")
async def generate_script(req: ScriptRequest):
    # Delegate to pipeline bridge (Gemini structured generator with template resilience)
    result = generate_script_engine(req.niche, req.topic, req.targetDuration)
    return result

async def run_video_generation_job(job_id: str, payload: dict):
    jobs = load_jobs()
    job = jobs.get(job_id, {})
    
    script_text = payload.get("script", "")
    voice_id = payload.get("voiceId", "deep_narrator")
    caption_style_id = payload.get("captionStyleId", "mrbeast")
    
    audio_path = os.path.join(OUTPUT_DIR, "audio", f"reel_{job_id}.wav")
    subtitles_path = os.path.join(OUTPUT_DIR, "temp", f"reel_{job_id}.ass")
    final_output_mp4 = os.path.join(FINAL_VIDEO_DIR, f"faceless_reel_{job_id}.mp4")

    # Stage 1: Script Analysis
    job["stage"] = "analyzing"
    job["stageLabel"] = "Analyzing Script & Scene Keyframes"
    job["progress"] = 20
    job["updatedAt"] = datetime.utcnow().isoformat()
    jobs[job_id] = job
    save_jobs(jobs)
    await asyncio.sleep(1)

    # Stage 2: Audio Synthesis
    job["stage"] = "voiceover"
    job["stageLabel"] = "Synthesizing Studio Quality AI Voiceover"
    job["progress"] = 45
    job["updatedAt"] = datetime.utcnow().isoformat()
    jobs[job_id] = job
    save_jobs(jobs)
    synthesize_audio_engine(script_text, voice_id, audio_path)
    await asyncio.sleep(1)

    # Stage 3: Dynamic Word-by-Word Subtitles
    job["stage"] = "subtitles"
    job["stageLabel"] = f"Formatting ASS Word-by-Word Captions ({caption_style_id})"
    job["progress"] = 70
    job["updatedAt"] = datetime.utcnow().isoformat()
    jobs[job_id] = job
    save_jobs(jobs)
    generate_subtitles_engine(audio_path, script_text, caption_style_id, subtitles_path)
    await asyncio.sleep(1)

    # Stage 4: 9:16 Video Compositing & Render
    job["stage"] = "compositing"
    job["stageLabel"] = "Mixing Audio, Subtitles & 9:16 Vertical Video Assembly"
    job["progress"] = 90
    job["updatedAt"] = datetime.utcnow().isoformat()
    scenes = payload.get("scenes", [])
    niche = payload.get("niche", "biblical")
    assemble_reel_engine(audio_path, subtitles_path, final_output_mp4, scenes=scenes, niche=niche)
    await asyncio.sleep(1)

    # Completed
    video_filename = os.path.basename(final_output_mp4)
    job["status"] = "completed"
    job["progress"] = 100
    job["stage"] = "finished"
    job["stageLabel"] = "Video Ready to Download & Post"
    job["videoUrl"] = f"/videos/{video_filename}"
    job["thumbnailUrl"] = "/videos/thumbnail.jpg"
    job["completedAt"] = datetime.utcnow().isoformat()
    jobs[job_id] = job
    save_jobs(jobs)

@app.post("/api/create-video")
async def create_video(req: VideoCreationRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())[:8]
    jobs = load_jobs()
    
    new_job = {
        "id": job_id,
        "niche": req.niche,
        "topic": req.topic,
        "script": req.script,
        "voiceId": req.voiceId,
        "captionStyleId": req.captionStyleId,
        "bgmMood": req.bgmMood,
        "status": "processing",
        "progress": 5,
        "stage": "queued",
        "stageLabel": "Job Queued in Video Engine",
        "createdAt": datetime.utcnow().isoformat(),
        "videoUrl": None
    }
    jobs[job_id] = new_job
    save_jobs(jobs)

    background_tasks.add_task(run_video_generation_job, job_id, req.dict())

    return {"jobId": job_id, "status": "processing", "message": "Video generation started"}

@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    jobs = load_jobs()
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

@app.get("/api/videos")
def list_videos():
    # Return available rendered videos from cinema-xray final_video output directory
    videos = []
    if os.path.exists(FINAL_VIDEO_DIR):
        files = glob.glob(os.path.join(FINAL_VIDEO_DIR, "*.mp4"))
        for f in sorted(files, key=os.path.getmtime, reverse=True):
            filename = os.path.basename(f)
            stat = os.stat(f)
            # Make readable title
            title = filename.replace(".mp4", "").replace("_", " ").title()
            videos.append({
                "id": filename,
                "title": title,
                "filename": filename,
                "url": f"/videos/{filename}",
                "sizeMb": round(stat.st_size / (1024 * 1024), 1),
                "createdAt": datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %Y %H:%M")
            })
    return {"videos": videos}

@app.get("/api/autopilot-status")
def get_autopilot_status():
    return {
        "enabled": True,
        "frequency": "2 videos / day",
        "nextRun": "Today at 18:00 (6:00 PM)",
        "channels": [
            {"platform": "YouTube Shorts", "handle": "@CinemaXRayShorts", "connected": True, "subscribers": "14.2K"},
            {"platform": "Instagram Reels", "handle": "@cinemaxray.reels", "connected": True, "followers": "32.8K"},
            {"platform": "TikTok", "handle": "@cinemaxray_official", "connected": False, "followers": "0"}
        ],
        "recentPosts": [
            {"title": "The Secret of Mjolnir Worthiness", "views": "142.5K", "platform": "YouTube Shorts", "status": "Posted"},
            {"title": "Interstellar Gargantua Secret Decoded", "views": "389.1K", "platform": "Instagram Reels", "status": "Posted"},
            {"title": "Tony Stark Nanotech Paradox", "views": "92.0K", "platform": "YouTube Shorts", "status": "Posted"}
        ]
    }
