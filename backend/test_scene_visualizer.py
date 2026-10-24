import os
import unittest
from backend.scene_visualizer import render_ken_burns_clip, create_color_gradient_fallback

class TestSceneVisualizer(unittest.TestCase):
    def test_gradient_fallback_and_ken_burns(self):
        img_temp = "/tmp/test_bg_ken.jpg"
        clip_temp = "/tmp/test_ken_burns_clip.mp4"

        # 1. Create vertical canvas
        create_color_gradient_fallback(img_temp, "#312e81")
        self.assertTrue(os.path.exists(img_temp))

        # 2. Render 2-second vertical Ken Burns clip
        render_ken_burns_clip(img_temp, 2.0, clip_temp, fps=24)
        self.assertTrue(os.path.exists(clip_temp))
        self.assertGreater(os.path.getsize(clip_temp), 1000)

        # Cleanup
        if os.path.exists(img_temp):
            os.remove(img_temp)
        if os.path.exists(clip_temp):
            os.remove(clip_temp)

if __name__ == "__main__":
    unittest.main()
