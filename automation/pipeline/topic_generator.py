import os
import json
import logging
from pydantic import BaseModel
from google import genai
from google.genai import types

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Set paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT_FILE = os.path.join(BASE_DIR, "prompts", "script_generator_prompt.txt")
CONFIG_FILE = os.path.join(BASE_DIR, "config", "config.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

class TopicAndScript(BaseModel):
    movie_or_source: str
    source_type: str
    specific_scene_or_moment: str
    concept: str
    category: str
    concept_definition: str
    core_question: str
    hidden_insight: str
    why_this_is_interesting: str
    working_title: str
    hook: str
    script: str

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def load_prompt():
    with open(PROMPT_FILE, 'r') as f:
        return f.read()

def validate_script(content: TopicAndScript):
    word_count = len(content.script.split())
    if not (110 <= word_count <= 150):
        logging.warning(f"Word count is {word_count}, which is outside the target 120-130 range.")
    
    if "\n\n" in content.script.strip() or "\n" in content.script.strip():
        logging.warning("Script contains multiple paragraphs. It should be one continuous paragraph.")

    if not content.concept or not content.movie_or_source or not content.specific_scene_or_moment:
        raise ValueError("Missing required fields (concept, movie, or scene).")
        
    return word_count

def generate_topic_and_script(category=None):
    config = load_config()
    
    # Also check if prompt file is populated, as requested by step 2
    prompt_text = load_prompt()
    if not prompt_text.strip() or prompt_text.strip() == "You are an expert scriptwriter...":
        logging.error("Prompt file is empty or placeholder. Please populate prompts/script_generator_prompt.txt with the Master Script Engine.")
        return
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set. Please export GEMINI_API_KEY=your_key")
        
    client = genai.Client(api_key=api_key)
    
    # Instruction for the model
    system_instruction = prompt_text
    
    # Ask the AI to select ONE topic and then generate the script
    user_prompt = """
    Please randomly select ONE high-potential Cinema Decoded topic following the 'RANDOM' mode criteria.
    Then, generate the final YouTube Shorts script based on the Master Script Engine guidelines provided in the system instructions.
    The response must strictly follow the required JSON structure. 
    Ensure the script is exactly ONE continuous paragraph of approximately 120-130 words.
    Do not force a theory onto a scene. Novelty is important.
    """
    
    if category:
        user_prompt += f"\n\nIMPORTANT CONSTRAINT: You MUST select a topic specifically from this category/domain: {category}"
    
    logging.info("Calling Gemini API (this may take a few seconds)...")
    response = client.models.generate_content(
        model=config.get('model_name', 'gemini-2.5-flash'),
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=TopicAndScript,
            temperature=0.8,
        ),
    )
    
    try:
        result = response.parsed
    except Exception as e:
        logging.error(f"Failed to parse response: {e}")
        logging.error(f"Raw response: {response.text}")
        return
        
    word_count = validate_script(result)
    
    # 7. Save the three output files
    
    # topic.json
    topic_data = {
        "movie_or_source": result.movie_or_source,
        "source_type": result.source_type,
        "specific_scene_or_moment": result.specific_scene_or_moment,
        "concept": result.concept,
        "category": result.category,
        "concept_definition": result.concept_definition,
        "core_question": result.core_question,
        "hidden_insight": result.hidden_insight,
        "why_this_is_interesting": result.why_this_is_interesting,
        "working_title": result.working_title,
        "hook": result.hook
    }
    
    topic_path = os.path.join(OUTPUT_DIR, "topic.json")
    with open(topic_path, "w") as f:
        json.dump(topic_data, f, indent=2)
        
    # script.txt
    script_path = os.path.join(OUTPUT_DIR, "script.txt")
    with open(script_path, "w") as f:
        f.write(result.script.strip())
        
    # content.json
    content_data = topic_data.copy()
    content_data["script"] = result.script.strip()
    content_data["word_count"] = word_count
    
    content_path = os.path.join(OUTPUT_DIR, "content.json")
    with open(content_path, "w") as f:
        json.dump(content_data, f, indent=2)
        
    # 8. Print a concise pipeline result
    print("\n--- TOPIC GENERATED ---")
    print(f"Movie: {result.movie_or_source}")
    print(f"Scene: {result.specific_scene_or_moment}")
    print(f"Concept: {result.concept}")
    print(f"Title: {result.working_title}")
    print(f"Word Count: {word_count}")
    print(f"Output: Success. Files saved to output/ directory.")

if __name__ == "__main__":
    generate_topic_and_script()
