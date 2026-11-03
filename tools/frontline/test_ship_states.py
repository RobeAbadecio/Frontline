"""Ship condition sequences and the server's pose tables stay in step."""
from pathlib import Path
import re
import unittest

from tools.frontline import ship_states as ss

REPO=Path(__file__).resolve().parents[2]
NAVAL=(REPO/'games/warcraft-3/game/skills/s_naval.c').read_text()

def c_table(name):
    body=re.search(name+r'\[[^\]]*\](?:\[[^\]]*\])?\s*=\s*\{(.*?)\};',NAVAL,re.S)[1]
    return [tuple(float(v.rstrip('f')) for v in row.split(',')) for row in re.findall(r'\{([^{}]*)\}',body)]

class ShipStates(unittest.TestCase):
    def test_server_pose_tables_match_the_models(self):
        self.assertEqual(c_table('SHIP_POSE'),[tuple(map(float,p)) for p in ss.POSES])
        self.assertEqual(c_table('SHIP_PLUNGE'),[tuple(map(float,p)) for p in ss.PLUNGE])
        self.assertIn(f'SHIP_DEATH_MS {ss.DEATH_MS}u',NAVAL)

    def test_every_condition_has_stand_walk_and_attack(self):
        names={s[0] for s in ss.SEQUENCES}
        for primary in ('Stand','Walk','Attack'):
            for level in range(len(ss.POSES)):
                for fx in ss.EFFECTS:
                    name=' '.join(w for w in (primary,f'List{level}' if level else '',fx.capitalize() if fx else '') if w)
                    self.assertIn(name,names)
        self.assertEqual([s[0] for s in ss.SEQUENCES[-3:]],['Death','Birth','Decay'])
        # Contiguous, non-overlapping windows (turret mounts copy the hull's frame).
        for a,b in zip(ss.SEQUENCES,ss.SEQUENCES[1:]):self.assertEqual(a[2]+1,b[1])

    def test_tags_published_by_the_server_select_these_sequences(self):
        for tag in ('list1','list2','list3','smoke','fire','inferno'):self.assertIn(tag,NAVAL)

if __name__=='__main__':unittest.main()
