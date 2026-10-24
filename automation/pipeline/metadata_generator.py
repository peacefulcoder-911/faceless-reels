import os
import json
import csv
import logging
from pydantic import BaseModel
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TOPIC_FILE = os.path.join(OUTPUT_DIR, "topic.json")
SCRIPT_FILE = os.path.join(OUTPUT_DIR, "script.txt")
METADATA_DIR = os.path.join(OUTPUT_DIR, "metadata")
METADATA_CSV = os.path.join(METADATA_DIR, "metadata.csv")
CONFIG_FILE = os.path.join(BASE_DIR, "config", "config.json")

class YouTubeMetadata(BaseModel):
    title: str
    description: str
    tags: list[str]

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def generate_metadata():
    if not os.path.exists(TOPIC_FILE):
        raise FileNotFoundError(f"Missing {TOPIC_FILE}")
    if not os.path.exists(SCRIPT_FILE):
        raise FileNotFoundError(f"Missing {SCRIPT_FILE}")

    with open(TOPIC_FILE, 'r', encoding='utf-8') as f:
        topic_data = json.load(f)
    
    with open(SCRIPT_FILE, 'r', encoding='utf-8') as f:
        script_text = f.read().strip()
        
    if not script_text:
        raise ValueError("Script text is empty.")

    config = load_config()
    model_name = config.get("model_name", "gemini-2.5-flash")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are an expert YouTube SEO and behavioral psychology strategist.
Based on the following generated topic and script for a Cinema Decoded YouTube Short, generate the final YouTube metadata.

# TOPIC DATA
{json.dumps(topic_data, indent=2)}

# SCRIPT
{script_text}

# INSTRUCTIONS
Generate the following fields:
1. Title: Must create a strong curiosity gap. Do NOT use generic clickbait like "The Psychology of..." or "Amazing Facts...". It should make the viewer ask "Why?". Keep it concise. Example: "Why Getting Better Can Make You Worse".
2. Description: The first 1-2 sentences must immediately communicate the interesting idea. Then naturally explain the movie, concept, and insight. Add 3-5 relevant short hashtags at the end. DO NOT keyword stuff. DO NOT fabricate information. Sound like a human.
3. Tags: An array of relevant tags based on the movie, scene, concept, psychology, and viewer search intent. No duplicates.

Return the result strictly conforming to the requested JSON schema.
"""

    logging.info("Calling Gemini API to generate metadata...")
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=YouTubeMetadata,
            temperature=0.7,
        ),
    )

    metadata = response.parsed
    if not metadata:
        raise ValueError("Failed to parse metadata from Gemini.")

    movie_name = topic_data.get("movie_or_source", "unknown").lower().replace(" ", "_").replace("'", "")
    concept = topic_data.get("concept", "concept").lower().replace(" ", "_").replace("'", "")
    video_file = f"output/videos/{movie_name}_{concept}.mp4"

    os.makedirs(METADATA_DIR, exist_ok=True)

    csv_data = {
        "video_file": video_file,
        "title": metadata.title,
        "description": metadata.description,
        "tags": ",".join(metadata.tags),
        "category": "Education",
        "privacy_status": "private",
        "language": "en"
    }

    with open(METADATA_CSV, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ["video_file", "title", "description", "tags", "category", "privacy_status", "language"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(csv_data)

    logging.info(f"Metadata successfully generated and saved to {METADATA_CSV}")
    return metadata
