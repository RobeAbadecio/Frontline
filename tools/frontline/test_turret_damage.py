import unittest

from tools.frontline import models, ship_states, ships, turret_damage as td
from tools.frontline import gltf_import as gi


class BrokenTurrets(unittest.TestCase):
    def test_every_main_battery_turret_has_a_broken_variant(self):
        # s_naval.c mounts naval_twin / naval_triple, or the ability's TargetArt (Yamato).
        self.assertEqual(set(td.TURRETS),{'naval_triple','naval_twin','yamato_turret','yamato_turret_aa'})
        for name in td.TURRETS:
            self.assertIn(name+'_broken',models.GEOMETRY)
            self.assertEqual(td.broken(name),name+'_broken')

    def test_broken_turret_is_scorched_drooped_and_smoking_but_never_fires(self):
        for name in td.TURRETS:
            with self.subTest(name=name):
                whole=ships.triangles(name);burnt=td.triangles(name)
                lit=lambda tris:sum(sum(c) for _,c,_ in tris if c!=gi.TEAM)/max(1,len(tris))
                self.assertLess(lit(burnt),lit(whole)*.6)                      # scorched
                self.assertLess(gi.bounds(td.barrels(burnt))[0][2],gi.bounds(td.barrels(whole))[0][2])  # drooped
                data=models.mesh(name+'_broken')
                self.assertIn(b'Smoke',data);self.assertNotIn(b'Flash',data)
                self.assertEqual(data.count(b'Stand List0'),data.count(b'Stand List0'))  # same table below
                self.assertIn(b'Death',data)
        self.assertEqual(len(td.SEQUENCES),len(ship_states.SEQUENCES))       # follows the ship's frame

if __name__=='__main__':unittest.main()
