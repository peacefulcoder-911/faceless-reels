import os
import wave
from google import genai
from google.genai import types

def generate_audio(script_text, output_filename):
    # 1. Start the Gemini Client
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set. Please set it before running.")
        
    client = genai.Client(api_key=api_key)

    model = "gemini-3.1-flash-tts-preview"
    
    # 2. The Script and Context
    prompt_content = f"""Read the following transcript based on the audio profile and director's note.

# Audio Profile
A young, casual YouTube storyteller. The voice is completely effortless, slightly dry, and relaxed. Zero pressure, no dramatic acting, just a smooth, natural speaking voice.

# Director's note
Style: Flat affect, minimal pitch variation, dry delivery. Pace: Fast, energetic, no dead air. Sentences overlap slightly. Accent: American (General).

## Scene:
A casual bedroom studio. A young guy is calmly explaining a cool history topic to his audience with a relaxed, dry delivery.

## Sample Context:
Smooth, modern YouTube essay style. The delivery is extremely casual, flat, and effortless. The speaker drops all theatrical pressure and just talks normally, like a real person having a calm conversation.

## Transcript:
{script_text}
"""
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt_content)],
        ),
    ]
    
    # 3. Apply the New Voice (Achird - the smooth casual narrator)
    generate_content_config = types.GenerateContentConfig(
        temperature=0.9,
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Achird"
                )
            )
        ),
    )

    print("Connecting to Gemini and generating your casual voiceover...")
    
    # 4. Request the single audio file
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )

    # 5. Save the audio using the 'wave' module exactly where requested
    part = response.candidates[0].content.parts[0]
    if part.inline_data and part.inline_data.data:
        raw_audio = part.inline_data.data
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        
        # Format the sound so it plays instantly on macOS/Windows
        with wave.open(output_filename, "wb") as wav_file:
            wav_file.setnchannels(1)       # Mono sound
            wav_file.setsampwidth(2)       # 16-bit audio depth
            wav_file.setframerate(24000)   # 24kHz studio speed
            wav_file.writeframes(raw_audio)
            
        print(f"\nSuccess! Your audio is saved as: {output_filename}")
        return True
    else:
        raise Exception("No audio data returned from the model.")
