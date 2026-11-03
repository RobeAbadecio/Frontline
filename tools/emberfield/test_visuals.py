"""Asset contracts for native HUD states; no renderer internals duplicated."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import art

class VisualAssets(unittest.TestCase):
    def test_commands_are_distinct_and_have_legible_disabled_art(self):
        symbols=['move','attack','stop','hold','patrol','build','repair','gather','cancel','upgrade','spell','inventory','group','camera']
        images=[art.icon(s) for s in symbols]
        self.assertEqual(len({im.tobytes() for im in images}),len(symbols))
        for im in images:
            self.assertEqual(im.size,(256,256))
            self.assertGreater(len(set(im.get_flattened_data())),100)
        self.assertNotEqual(art.icon('attack').tobytes(),art.icon('attack',disabled=True).tobytes())
    def test_hud_leaves_runtime_portrait_and_health_visible(self):
        im=art.panel(1600,300,'hud')
        self.assertEqual(im.getpixel((int(1600*.315),150))[3],0)
        self.assertEqual(im.getpixel((int(1600*.315),290))[3],0)
        self.assertEqual(im.getpixel((int(1600*.6),150))[3],255)
    def test_font_is_bundled_with_license(self):
        self.assertTrue((art.ASSETS/'fonts/DejaVuSans.ttf').is_file())
        self.assertIn('Permission is hereby granted',(art.ASSETS/'fonts/LICENSE_DEJAVU').read_text())

if __name__=='__main__':unittest.main()
