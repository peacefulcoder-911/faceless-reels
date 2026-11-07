"""
Tests verifying AI service mocking, error handling, and offline resilient fallbacks.
Guarantees NO real paid/network API calls are made during test execution.
"""

from unittest.mock import patch

from backend.pipeline_bridge import generate_script_engine, synthesize_audio_engine


def test_script_generation_resilient_fallback():
    """
    Verify that when external AI calls fail or time out,
    the pipeline bridge transparently falls back to the deterministic story beat generator.
    """
    with patch("pipeline.script_generator._get_api_client", side_effect=Exception("Simulated API Offline")):
        result = generate_script_engine("history", "The Lost Colony of Roanoke", 45)
        assert result is not None
        assert "hook" in result
        assert "scenes" in result
        assert len(result["scenes"]) == 4
        assert result["niche"] == "history"
        for s in result["scenes"]:
            assert "text" in s
            assert "shotType" in s
            assert "visualPrompt" in s


@patch("pipeline.audio_generator.generate_elevenlabs_audio")
def test_audio_engine_with_mocked_elevenlabs(mock_eleven, tmp_path):
    """Verify audio synthesis bridge invokes ElevenLabs mock cleanly."""
    temp_wav = str(tmp_path / "mocked_audio.wav")
    # Simulate writing output file in mock
    def fake_generate(script_text, out_path, voice_name="brian"):
        with open(out_path, "wb") as f:
            f.write(b"RIFFf\x00\x00\x00WAVEfmt ")

    mock_eleven.side_effect = fake_generate

    out = synthesize_audio_engine("A shocking discovery was made.", "deep_narrator", temp_wav)
    assert out == temp_wav
    mock_eleven.assert_called_once()
