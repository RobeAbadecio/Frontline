import unittest
from pathlib import Path

from tools.frontline import status_icons

REPO=Path(__file__).resolve().parents[2]


class StatusIcons(unittest.TestCase):
    def test_one_32px_icon_per_hud_status_path(self):
        icons=status_icons.all_icons()
        hud=(REPO/'games/warcraft-3/game/hud/hud_infopanel.c').read_text()
        for name,im in icons.items():
            self.assertEqual(im.size,(32,32));self.assertEqual(im.mode,'RGBA')
            self.assertIn(f'Emberfield\\\\Icons\\\\status_{name}.blp',hud)          # the panel draws this file
        self.assertEqual(set(icons),{'burning','flooding','turret','listing','dead','critical','docked'})

    def test_icons_are_distinct(self):
        icons=[im.tobytes() for im in status_icons.all_icons().values()]
        self.assertEqual(len(set(icons)),len(icons))

if __name__=='__main__':unittest.main()
