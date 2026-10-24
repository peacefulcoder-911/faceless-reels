import unittest
from fastapi.testclient import TestClient
from backend.main import app

class TestFacelessReelsAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")

    def test_niches(self):
        res = self.client.get("/api/niches")
        self.assertEqual(res.status_code, 200)
        niches = res.json()["niches"]
        self.assertGreater(len(niches), 5)
        # Verify specific niches from FacelessReels
        ids = [n["id"] for n in niches]
        self.assertIn("biblical", ids)
        self.assertIn("anime", ids)
        self.assertIn("heists", ids)
        self.assertIn("mythology", ids)
        self.assertIn("school_gossip", ids)

    def test_options(self):
        res = self.client.get("/api/options")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("voices", data)
        self.assertIn("captionStyles", data)
        self.assertIn("bgmMoods", data)

    def test_generate_script(self):
        payload = {
            "niche": "biblical",
            "topic": "The 3 days of darkness in Egypt",
            "targetDuration": 45
        }
        res = self.client.post("/api/generate-script", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("hook", data)
        self.assertIn("scenes", data)
        self.assertGreater(len(data["scenes"]), 0)

    def test_list_videos(self):
        res = self.client.get("/api/videos")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("videos", data)

if __name__ == "__main__":
    unittest.main()
