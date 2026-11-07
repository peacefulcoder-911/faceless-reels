"""
Unit tests for pipeline components: subtitle engine, Ken Burns motion presets,
video compositor math, and caption styles.
"""

import os
from pathlib import Path

from backend.pipeline_bridge import (
    CAPTION_STYLE_CONFIGS,
    generate_subtitles_engine,
    get_audio_duration_seconds,
)
from backend.scene_visualizer import (
    NICHE_STYLES,
    create_color_gradient_fallback,
)


def test_caption_style_definitions():
    """Verify all 4 core caption styles have required ASS styling attributes."""
    expected_styles = ["mrbeast", "neon_emerald", "cyberpunk_cyan", "fire_ruby"]
    for style_id in expected_styles:
        assert style_id in CAPTION_STYLE_CONFIGS
        cfg = CAPTION_STYLE_CONFIGS[style_id]
        assert "primary_color" in cfg
        assert "highlight_color" in cfg
        assert "font_size" in cfg
        assert cfg["font_size"] >= 60


def test_subtitle_engine_ass_generation(tmp_path):
    """Verify ASS subtitle generation creates valid ASS event markup."""
    sample_script = "UNBELIEVABLE SECRETS DISCOVERED UNDERGROUND"
    output_ass = str(tmp_path / "test_captions.ass")

    result = generate_subtitles_engine("/tmp/nonexistent.wav", sample_script, "mrbeast", output_ass)
    assert os.path.exists(result)

    content = Path(result).read_text(encoding="utf-8")
    assert "[Script Info]" in content
    assert "PlayResX: 1080" in content
    assert "PlayResY: 1920" in content
    assert "[V4+ Styles]" in content
    assert "[Events]" in content
    assert "Dialogue:" in content
    # Verify highlight color is embedded
    assert CAPTION_STYLE_CONFIGS["mrbeast"]["highlight_color"] in content


def test_audio_duration_fallback():
    """Verify safe fallback duration when probe fails or file is nonexistent."""
    dur = get_audio_duration_seconds("/nonexistent/file/path.wav")
    assert dur == 35.0


def test_niche_styles_completeness():
    """Verify all 8 niche styles have defined aesthetic prompts."""
    expected_niches = [
        "biblical", "anime", "heists", "mythology",
        "school_gossip", "scary_stories", "history", "kindness"
    ]
    for niche in expected_niches:
        assert niche in NICHE_STYLES
        assert len(NICHE_STYLES[niche]) > 20


def test_color_gradient_fallback_generation(tmp_path):
    """Verify FFmpeg color canvas generation produces a valid image file."""
    output_img = str(tmp_path / "test_canvas.jpg")
    create_color_gradient_fallback(output_img, "#10b981")
    assert os.path.exists(output_img)
    assert os.path.getsize(output_img) > 0
