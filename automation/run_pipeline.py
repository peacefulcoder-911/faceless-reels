import os
import sys
import argparse

# Ensure the pipeline module can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pipeline.topic_generator import generate_topic_and_script
from pipeline.audio_generator import generate_audio
from pipeline.metadata_generator import generate_metadata

def main():
    parser = argparse.ArgumentParser(description="Run the Cinema Decoded Automation Pipeline")
    parser.add_argument("--category", type=str, default=None, help="Force the AI to pick a topic from this specific category (e.g. 'Sci-Fi', 'Game Theory')")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(base_dir, "output", "script.txt")
    audio_output_dir = os.path.join(base_dir, "output", "audio")
    audio_path = os.path.join(audio_output_dir, "generated_audio.wav")
    metadata_csv = os.path.join(base_dir, "output", "metadata", "metadata.csv")
    
    print("=== STAGE 1: Generating Topic & Script ===")
    if args.category:
        print(f"Target Category: {args.category}")
    
    # Remove existing script to ensure we only proceed if a new one is successfully created
    if os.path.exists(script_path):
        os.remove(script_path)
        
    try:
        generate_topic_and_script(category=args.category)
    except Exception as e:
        print(f"ERROR: Script generation failed with exception: {e}")
        sys.exit(1)
        
    print("\n=== STAGE 2: Verifying Script ===")
    if not os.path.exists(script_path):
        print(f"ERROR: Script generation failed. File not found at {script_path}")
        sys.exit(1)
        
    with open(script_path, "r", encoding="utf-8") as f:
        script_text = f.read().strip()
        
    if not script_text:
        print(f"ERROR: Script file is empty ({script_path})")
        sys.exit(1)
        
    print("Script verification passed.")
    
    print("\n=== STAGE 3: Generating YouTube Metadata ===")
    try:
        generate_metadata()
        print("✓ metadata.csv created")
    except Exception as e:
        print(f"ERROR: Metadata generation failed: {e}")
        sys.exit(1)
    
    print("\n=== STAGE 4: Generating Audio ===")
    try:
        generate_audio(script_text, audio_path)
    except Exception as e:
        print(f"ERROR: Audio generation failed: {e}")
        sys.exit(1)
        
    print("\n=== PIPELINE COMPLETE ===")
    print(f"Final script available at: {script_path}")
    print(f"Final metadata available at: {metadata_csv}")
    print(f"Final audio available at: {audio_path}")

if __name__ == "__main__":
    main()
