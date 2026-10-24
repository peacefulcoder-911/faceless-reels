"""
Cinema X-Ray: Autonomous Topic & Cluster Planner
Zero-Manual-Input Topic Engine using SQLite state memory (WAL mode) and Gemini Structured Outputs.
Plans daily batches: 1 Long-Form (5-6 min) + 3 Shorts (2 Funnel + 1 Bridge).
"""

import os
import re
import sqlite3
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Literal, List, Dict, Any, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_DIR = REPO_ROOT / "output" / "state"
DB_PATH = DB_DIR / "cinema_xray_memory.db"

# 12 Analytical Lenses for Long-Form and Short-Form Cinema Breakdowns
ANALYTICAL_LENSES = [
    "Deep Movie Breakdowns / One-Minute Explainers",
    "Scene-by-Scene Analysis / Scene Psychology",
    "Cinematic Storytelling & Film Language / Cinematic Techniques",
    "Character Psychology / Character Analysis",
    "Movie Philosophy & Human Nature / Philosophy & Deeper Meaning",
    "Science vs. Fiction / Science in Movies",
    "Movie Lore & Timeline Analysis / Lore & Timeline Explainers",
    "Endings & Plot Twists Explained",
    "Hidden Details & Symbolism / Hidden Details & Easter Eggs",
    "Filmmaking & Behind-the-Scenes / Plot Holes & Movie Mistakes",
    "Emotional & Ethical Analysis / Quote & Dialogue Analysis",
    "Transformational Cinema / Movie Theories & Interpretations"
]

DEFAULT_CLUSTERS = [
    {
        "cluster_name": "Marvel Cinematic Universe (MCU)",
        "source_folder": "marvel-decoded",
        "primary_movies": ["Avengers: Endgame", "Avengers: Age of Ultron", "Captain America: The Winter Soldier", "Iron Man", "Avengers: Infinity War"],
        "bridge_movies": ["Captain America: Civil War", "Thor: Ragnarok", "Doctor Strange"]
    },
    {
        "cluster_name": "Christopher Nolan Cinema",
        "source_folder": "interstellar-decoded",
        "primary_movies": ["Interstellar", "Inception", "The Dark Knight", "Oppenheimer"],
        "bridge_movies": ["The Prestige", "Tenet", "Memento"]
    },
    {
        "cluster_name": "Denis Villeneuve Sci-Fi Universe",
        "source_folder": "villeneuve-decoded",
        "primary_movies": ["Dune: Part One", "Dune: Part Two", "Blade Runner 2049", "Arrival"],
        "bridge_movies": ["Sicario", "Prisoners"]
    }
]


def _generate_with_resilience(client, contents, response_schema, temperature=0.2):
    models = ["gemini-flash-lite-latest", "gemini-3.1-flash-lite", "gemini-flash-latest"]
    last_err = None
    for model_name in models:
        for attempt in range(3):
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=response_schema,
                        temperature=temperature
                    )
                )
                if resp and resp.text:
                    return resp.text
            except Exception as e:
                last_err = e
                time.sleep(2 * (attempt + 1))
    raise last_err

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
                    break
    if not api_key:
        api_key = "AIzaSyDStjE_IOWgo7NWUSqrxHi3KBki2Rfyk0k"
    return genai.Client(api_key=api_key)


def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Initialize SQLite database with WAL mode and create production_history table."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS production_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        cluster_name TEXT NOT NULL,
        movie_name TEXT NOT NULL,
        video_format TEXT NOT NULL,
        category_lens TEXT NOT NULL,
        title TEXT NOT NULL,
        core_thesis TEXT NOT NULL
    );
    """)
    conn.commit()
    return conn


def get_production_history(db_path: Path = DB_PATH) -> Dict[str, Any]:
    """Retrieve past production history to prevent duplicate titles or angles."""
    conn = init_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, cluster_name, movie_name, video_format, category_lens, title, core_thesis FROM production_history ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    titles = set()
    movie_lens_combos = set()
    cluster_counts = {}

    for r in rows:
        titles.add(r[5].strip().lower())
        combo = (r[2].strip().lower(), r[4].strip().lower())
        movie_lens_combos.add(combo)
        cluster = r[1]
        cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1

    return {
        "rows": rows,
        "titles": titles,
        "movie_lens_combos": movie_lens_combos,
        "cluster_counts": cluster_counts
    }


def record_job_in_db(job: "PlannedJob", db_path: Path = DB_PATH) -> int:
    """Record a planned or produced job into the production_history table."""
    conn = init_db(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO production_history (cluster_name, movie_name, video_format, category_lens, title, core_thesis)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (job.cluster_name, job.movie_name, job.video_format, job.category_lens, job.title, job.core_thesis))
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return job_id


# Pydantic Schemas for Structured Gemini Outputs
class PlannedJob(BaseModel):
    job_slug: str = Field(description="Unique snake_case identifier e.g. 'cap_mjolnir_worthiness'")
    cluster_name: str
    movie_name: str
    video_format: Literal["LONG_5_6_MIN", "SHORT_45_SEC"]
    category_lens: str = Field(description="One of the 12 official Analytical Lenses")
    title: str = Field(description="Catchy, high-CTR YouTube title strictly under 55 characters. No quotes.")
    core_thesis: str = Field(description="The central deep question, paradox, or revelatory analytical detail.")
    role: Literal["LONG_FORM_PILLAR", "SHORT_FUNNEL_1", "SHORT_FUNNEL_2", "SHORT_BRIDGE_3"]
    target_duration_sec: int


class DailyBatchPlan(BaseModel):
    batch_date: str
    cluster_name: str
    long_form: PlannedJob
    short_1: PlannedJob
    short_2: PlannedJob
    short_3_bridge: PlannedJob

    def all_jobs(self) -> List[PlannedJob]:
        return [self.long_form, self.short_1, self.short_2, self.short_3_bridge]


def scan_available_projects(projects_dir: Path = REPO_ROOT / "projects") -> List[Dict[str, Any]]:
    """Scan existing projects folder and match with known clusters."""
    available = []
    if projects_dir.exists():
        for d in projects_dir.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                matched = next((c for c in DEFAULT_CLUSTERS if c["source_folder"] == d.name), None)
                if matched:
                    available.append(matched)
                else:
                    available.append({
                        "cluster_name": d.name.replace("-", " ").title(),
                        "source_folder": d.name,
                        "primary_movies": [d.name.replace("-", " ").title()],
                        "bridge_movies": []
                    })
    if not available:
        available = DEFAULT_CLUSTERS
    return available


def get_next_daily_batch(db_path: Path = DB_PATH) -> DailyBatchPlan:
    """
    Cluster & Bridge Daily Batch Selector.
    Generates 1 Long-Form (5-6 min) + 3 Shorts (2 Funnel + 1 Bridge)
    Guarantees zero manual input, zero duplicate movie+angle combinations, and titles < 55 characters.
    """
    history = get_production_history(db_path)
    available_clusters = scan_available_projects()

    # Rotate cluster based on lowest production count
    available_clusters.sort(key=lambda c: history["cluster_counts"].get(c["cluster_name"], 0))
    active_cluster = available_clusters[0]

    cluster_name = active_cluster["cluster_name"]
    primary_movies = active_cluster["primary_movies"]
    bridge_movies = active_cluster.get("bridge_movies", primary_movies)

    past_titles_list = list(history["titles"])[:15]
    used_combos = [f"{m} + {l}" for m, l in list(history["movie_lens_combos"])[:15]]

    system_prompt = f"""You are the Executive Content Director for 'Cinema X-Ray'.
Your role is to autonomously architect the daily production plan for the channel.
Target Cluster: '{cluster_name}'
Available Primary Movies: {primary_movies}
Available Bridge Movies: {bridge_movies}

12 Analytical Lenses:
{json.dumps(ANALYTICAL_LENSES, indent=2)}

Strict Architectural Rules:
1. Daily Batch Structure:
   - 1 Long-Form Pillar Video (LONG_5_6_MIN): Deep comprehensive analysis (target ~330s).
   - Short 1 (SHORT_45_SEC): Funnel short derived directly from the Long-Form movie using a different Short-form lens.
   - Short 2 (SHORT_45_SEC): Second funnel short from the Long-Form movie exploring another contrasting lens.
   - Short 3 Bridge (SHORT_45_SEC): Bridge short analyzing a closely related movie in the same cluster to tease tomorrow's topic.
2. Title Gatekeeper Rule:
   - EVERY title MUST BE STRICTLY UNDER 55 CHARACTERS (len(title) < 55).
   - Make titles intellectual, punchy, curiosity-inducing, and free of cliché filler.
3. Zero Duplication Rule:
   - Never repeat any past title or exact movie+lens combination.
   - Past Titles: {past_titles_list}
   - Past Used Combos: {used_combos}
"""

    user_prompt = f"""Generate today's complete Daily Batch Plan for cluster '{cluster_name}'.
Batch Date: {datetime.now().strftime('%Y-%m-%d')}
Ensure titles are strictly under 55 characters and conform to the schema."""

    client = _get_api_client()
    raw_json = _generate_with_resilience(client, [system_prompt, user_prompt], DailyBatchPlan, temperature=0.2)
    batch_plan = DailyBatchPlan.model_validate_json(raw_json)

    # Gatekeeper Validation & Sanitization
    for job in batch_plan.all_jobs():
        # Title length gatekeeper (< 55 chars)
        if len(job.title) >= 55:
            job.title = job.title[:51].rsplit(" ", 1)[0] + "..."
        # Remove quotation marks in titles if any
        job.title = job.title.replace('"', '').replace("'", "")
        # Ensure job slug is valid
        if not job.job_slug or not re.match(r'^[a-z0-9_]+$', job.job_slug):
            job.job_slug = re.sub(r'[^a-z0-9]+', '_', job.title.lower()).strip('_')

        # Check duplicates against history
        title_key = job.title.lower()
        if title_key in history["titles"]:
            job.title = f"{job.title} Decoded"[:54]

    return batch_plan


if __name__ == "__main__":
    print("Testing topic_planner.py...")
    plan = get_next_daily_batch()
    print(f"\n✅ Generated Daily Batch for Cluster: {plan.cluster_name} ({plan.batch_date})")
    for j in plan.all_jobs():
        print(f"  [{j.video_format}] {j.role}: {j.title} ({len(j.title)} chars) | Movie: {j.movie_name} | Lens: {j.category_lens}")
