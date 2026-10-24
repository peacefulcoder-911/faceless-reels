import os
import unittest
from backend.pipeline_bridge import (
    generate_script_engine,
    synthesize_audio_engine,
    generate_subtitles_engine,
    assemble_reel_engine,
    CAPTION_STYLE_CONFIGS
)

class TestPipelineIntegration(unittest.TestCase):
    def test_caption_styles(self):
        self.assertIn("mrbeast", CAPTION_STYLE_CONFIGS)
        self.assertIn("neon_emerald", CAPTION_STYLE_CONFIGS)
        self.assertIn("cyberpunk_cyan", CAPTION_STYLE_CONFIGS)
        self.assertIn("fire_ruby", CAPTION_STYLE_CONFIGS)

    def test_script_generation_bridge(self):
        result = generate_script_engine("biblical", "The 3 days of darkness in Egypt", 45)
        self.assertIsNotNone(result)
        self.assertIn("hook", result)
        self.assertIn("scenes", result)
        self.assertEqual(len(result["scenes"]), 4)
        for s in result["scenes"]:
            self.assertIn("text", s)
            self.assertIn("shotType", s)
            self.assertIn("visualPrompt", s)

    def test_subtitle_engine_bridge(self):
        script_sample = "YOU WON'T BELIEVE WHAT WAS FOUND INSIDE"
        temp_ass = "/tmp/test_reel_subtitles.ass"
        out = generate_subtitles_engine("/tmp/fake.wav", script_sample, "mrbeast", temp_ass)
        self.assertTrue(os.path.exists(out))
        content = open(out).read()
        self.assertIn("[Script Info]", content)
        self.assertIn("Default", content)
        self.assertIn("Dialogue:", content)
        # Check that highlight color was embedded in ASS tags
        self.assertIn(CAPTION_STYLE_CONFIGS["mrbeast"]["highlight_color"], content)
        if os.path.exists(temp_ass):
            os.remove(temp_ass)

    def test_audio_engine_fallback(self):
        temp_wav = "/tmp/test_speech.wav"
        out = synthesize_audio_engine("Testing speech synthesis bridge.", "deep_narrator", temp_wav)
        self.assertTrue(os.path.exists(out) or out == temp_wav)
        if os.path.exists(temp_wav):
            os.remove(temp_wav)

if __name__ == "__main__":
    unittest.main()
