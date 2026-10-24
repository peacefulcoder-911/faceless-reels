import streamlit as st
import os
import json
import sys
from pipeline.topic_generator import generate_topic_and_script
from pipeline.audio_generator import generate_audio
from pipeline.metadata_generator import generate_metadata

# Ensure module path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set page config
st.set_page_config(page_title="Cinema Decoded Generator", page_icon="🎬", layout="centered")

st.title("🎬 Cinema Decoded Generator")
st.markdown("Generate your next viral Cinema Decoded YouTube Short script and audio instantly.")

# Paths
base_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(base_dir, "output")
script_path = os.path.join(output_dir, "script.txt")
topic_path = os.path.join(output_dir, "topic.json")
audio_path = os.path.join(output_dir, "audio", "generated_audio.wav")
metadata_path = os.path.join(output_dir, "metadata", "metadata.csv")

# Function to run pipeline
def run_pipeline(category=None):
    with st.spinner(f"Generating {'Topic: '+category if category else 'Random Topic'} & Script..."):
        # Remove old files to prevent reading stale data
        if os.path.exists(script_path):
            os.remove(script_path)
        if os.path.exists(topic_path):
            os.remove(topic_path)
        if os.path.exists(audio_path):
            os.remove(audio_path)
        if os.path.exists(metadata_path):
            os.remove(metadata_path)
            
        try:
            generate_topic_and_script(category=category)
        except Exception as e:
            st.error(f"Script generation failed: {e}")
            return False

    if not os.path.exists(script_path):
        st.error("Pipeline failed: Script was not generated.")
        return False

    with open(script_path, "r", encoding="utf-8") as f:
        script_text = f.read().strip()
        
    if not script_text:
        st.error("Pipeline failed: Generated script is empty.")
        return False
        
    with st.spinner("Generating YouTube Metadata..."):
        try:
            generate_metadata()
        except Exception as e:
            st.error(f"Metadata generation failed: {e}")
            return False
        
    with st.spinner("Writing the script into audio..."):
        try:
            generate_audio(script_text, audio_path)
        except Exception as e:
            st.error(f"Audio generation failed: {e}")
            return False
            
    return True

# UI Layout
st.subheader("1. Setup")
category_input = st.text_input("Topic, Movie, or Category (leave blank for random):", placeholder="e.g. Inception, Game Theory, or The Matrix")

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 Generate Based on Input", use_container_width=True):
        if not category_input:
            st.warning("Please enter a category/topic or click 'Generate Random' instead.")
        else:
            success = run_pipeline(category_input)
            if success:
                st.success("Generation Complete!")
with col2:
    if st.button("🎲 Generate Random", use_container_width=True):
        success = run_pipeline(None)
        if success:
            st.success("Generation Complete!")

st.divider()

# Display Results
if os.path.exists(topic_path) and os.path.exists(script_path):
    st.subheader("2. Results")
    try:
        with open(topic_path, 'r') as f:
            topic_data = json.load(f)
        
        st.markdown(f"**Movie/Scene:** {topic_data.get('movie_or_source', '')} - {topic_data.get('specific_scene_or_moment', '')}")
        st.markdown(f"**Concept:** {topic_data.get('concept', '')}")
        st.markdown(f"**Title:** {topic_data.get('working_title', '')}")
        
        with open(script_path, 'r') as f:
            script_text = f.read()
            
        st.text_area("Final Script:", script_text, height=200)
        
        if os.path.exists(audio_path):
            st.audio(audio_path, format="audio/wav")
            
        if os.path.exists(metadata_path):
            import csv
            with open(metadata_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                try:
                    row = next(reader)
                    st.subheader("3. YouTube Metadata")
                    st.markdown(f"**Title:** {row.get('title', '')}")
                    st.markdown(f"**Tags:** {row.get('tags', '')}")
                    st.text_area("Description:", row.get('description', ''), height=150)
                except StopIteration:
                    pass
    except Exception as e:
        st.error(f"Could not load results: {e}")
