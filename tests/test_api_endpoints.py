"""
Unit tests for FacelessReels FastAPI REST API endpoints.
Uses TestClient with mocked background generation to ensure fast, zero-network execution.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify system health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_niches_endpoint():
    """Verify curated niches catalog returns required viral niches."""
    response = client.get("/api/niches")
    assert response.status_code == 200
    niches = response.json().get("niches", [])
    assert len(niches) >= 8

    niche_ids = [n["id"] for n in niches]
    assert "biblical" in niche_ids
    assert "anime" in niche_ids
    assert "heists" in niche_ids
    assert "mythology" in niche_ids
    assert "school_gossip" in niche_ids
    assert "scary_stories" in niche_ids
    assert "history" in niche_ids
    assert "kindness" in niche_ids


def test_options_endpoint():
    """Verify voices, caption styles, and BGM moods options."""
    response = client.get("/api/options")
    assert response.status_code == 200
    data = response.json()
    assert "niches" in data
    assert "voices" in data
    assert "captionStyles" in data
    assert "bgmMoods" in data

    caption_ids = [c["id"] for c in data["captionStyles"]]
    assert "mrbeast" in caption_ids
    assert "neon_emerald" in caption_ids
    assert "cyberpunk_cyan" in caption_ids
    assert "fire_ruby" in caption_ids


@patch("backend.main.generate_script_engine")
def test_generate_script_endpoint(mock_script_engine):
    """Verify script generation endpoint returns structured scenes."""
    mock_script_engine.return_value = {
        "title": "The Secret of the Pyramids",
        "niche": "history",
        "hook": "What is buried beneath the sands?",
        "fullScript": "Ancient stone reveals secrets that change everything.",
        "estimatedDuration": 45,
        "scenes": [
            {
                "scene": 1,
                "duration": 8,
                "text": "What is buried beneath the sands?",
                "visualPrompt": "Dramatic desert aerial",
                "shotType": "Extreme Closeup"
            }
        ]
    }

    payload = {
        "niche": "history",
        "topic": "The Great Sphinx Hidden Chamber",
        "targetDuration": 45
    }
    response = client.post("/api/generate-script", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "The Secret of the Pyramids"
    assert len(data["scenes"]) == 1
    assert data["scenes"][0]["shotType"] == "Extreme Closeup"


def test_list_videos_endpoint():
    """Verify video library endpoint responds with a list."""
    response = client.get("/api/videos")
    assert response.status_code == 200
    data = response.json()
    assert "videos" in data
    assert isinstance(data["videos"], list)


def test_autopilot_status_endpoint():
    """Verify autonomous scheduler status endpoint."""
    response = client.get("/api/autopilot-status")
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert "channels" in data
    assert len(data["channels"]) >= 3


def test_get_nonexistent_job():
    """Verify 404 response for nonexistent jobs."""
    response = client.get("/api/jobs/nonexistent-id-999")
    assert response.status_code == 404
