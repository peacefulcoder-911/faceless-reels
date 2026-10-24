# ⚡ FacelessReels: AI Faceless Video Generator & Auto-Pilot Platform

> **Create viral faceless videos on auto-pilot.**  
> The all-in-one AI platform that scripts, voices, generates art, captions, renders 9:16 vertical reels, and auto-publishes to YouTube Shorts, Instagram Reels, and TikTok.

---

## 🚀 Key Features

* **Visual Niche Showcase:** Curated art styles across 8 viral niches (Biblical Stories, Anime Stories, True Crime / Heists, Mythology & Legends, School Gossip, Creepypasta / Horror, Historical Enigmas, and Wholesome 3D Animation).
* **5-Step Studio Creator Wizard:**
  1. **Niche & Topic Selector:** Choose tested retention hooks or input your own.
  2. **AI Script & Scene Breakdown:** 4-scene retention structure with visual image generation prompts and shot angles.
  3. **Voiceover & Sound:** Deep cinematic narrator, storytelling voices, voice speed control, and background music moods.
  4. **Viral Dynamic Captions:** MrBeast Gold, Neon Emerald, Cyberpunk Cyan, and Fire Ruby with word-by-word bouncing karaoke animations.
  5. **Live 9:16 Compositing & Vertical Player:** Real-time generation progress, 9:16 video player preview, and instant downloads.
* **Auto-Pilot Scheduler:** Connect YouTube, Instagram, and TikTok with daily scheduled autonomous publishing (1x, 2x, 3x per day).
* **Integrated Video Library:** Browse, preview, stream, and manage all rendered video assets.

---

## 🛠️ Tech Stack

* **Frontend:** React, Vite, Lucide Icons, Glassmorphism UI, Google Fonts (`Outfit` & `Inter`)
* **Backend:** Python FastAPI, Uvicorn, Pydantic, Async Background Queue
* **Video Engine:** Python Pipeline (`pipeline/`), FFmpeg, Whisper for word-level captions, AI Voice synthesis

---

## 🏁 Quickstart

### 1. Backend Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit: **[http://localhost:5173](http://localhost:5173)**

---

## 🧪 Testing

Run backend endpoint unit tests:
```bash
python3 -m unittest backend/test_api.py
```

Run frontend build check:
```bash
npm --prefix frontend run build
```
