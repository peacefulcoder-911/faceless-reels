"""
Tests for configuration validation, environment variable handling, and credential safety.
"""

import os
from unittest.mock import patch

import pytest

from pipeline.audio_generator import _get_api_client as get_audio_api_client
from pipeline.script_generator import _get_api_client as get_script_api_client


def test_missing_gemini_key_raises_informative_error():
    """Verify that omitting GEMINI_API_KEY raises a descriptive ValueError rather than crashing silently."""
    with patch.dict(os.environ, {}, clear=True):
        # Ensure GEMINI_API_KEY is not in environment
        os.environ.pop("GEMINI_API_KEY", None)
        with pytest.raises(ValueError) as excinfo:
            get_audio_api_client()
        assert "GEMINI_API_KEY" in str(excinfo.value)


def test_missing_script_gemini_key_raises_informative_error():
    """Verify script generator fails gracefully when GEMINI_API_KEY is unset."""
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("GEMINI_API_KEY", None)
        with pytest.raises(ValueError) as excinfo:
            get_script_api_client()
        assert "GEMINI_API_KEY" in str(excinfo.value)


def test_client_secrets_example_exists_and_is_valid():
    """Ensure the client_secrets example template is present and contains required fields."""
    import json
    from pathlib import Path

    example_path = Path("config/client_secrets.json.example")
    assert example_path.exists(), "config/client_secrets.json.example must be committed as safe template"

    data = json.loads(example_path.read_text(encoding="utf-8"))
    assert "installed" in data
    assert "client_id" in data["installed"]
    assert "token_uri" in data["installed"]
    # Verify no real credentials are leaked in example template
    assert "YOUR_CLIENT_ID" in data["installed"]["client_id"]
