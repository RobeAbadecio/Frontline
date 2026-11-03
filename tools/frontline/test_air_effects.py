"""Flak bursts, aircraft crash effects and the aircraft crit/evade sequences."""
from pathlib import Path
import re
import struct
import unittest

from tools.frontline import imported
from tools.frontline import rich_mdx as rm
from tools.frontline import unit_anim as ua

REPO=Path(__file__).resolve().parents[2]
AIR_C=(REPO/'games/warcraft-3/game/skills/s_air_effects.c').read_text()

def sequences(data):
    """(name, start, end) of every SEQS entry in an MDX blob."""
    at=data.index(b'SEQS');size=struct.unpack_from('<I',data,at+4)[0];body=data[at+8:at+8+size]
    out=[]
    for k in range(0,len(body),132):
        name=body[k:k+80].split(b'\0')[0].decode();a,b=struct.unpack_from('<2I',body,k+80)
        out.append((name,a,b))
    return out

def alpha_at(layer,t):return rm._sample(sorted(layer.alpha),t)[0]

class Flak(unittest.TestCase):
    def test_flak_models_use_the_effect_sequences(self):
        for heavy in (True,False):
            data=ua.flak_mdx(heavy)
            self.assertEqual(data[:4],b'MDLX')
            self.assertEqual(sequences(data),[(n,a,b) for n,a,b,_,_ in ua.EFFECT_SEQ])

    def test_heavy_bursts_are_bigger_and_blacker_than_light_puffs(self):
        sizes={};shades={}
        for heavy in (True,False):
            layers,bones=ua.flak_layers(heavy)
            smoke=[l for l in layers if l.material==rm.BLEND]
            self.assertTrue(smoke)
            pts=[p for l in smoke for t in l.tris for p in t[0]]
            sizes[heavy]=max(abs(c) for p in pts for c in p)
            shades[heavy]=max(sum(t[1])/3 for l in smoke for t in l.tris)
        self.assertGreater(sizes[True],sizes[False]*1.5)
        self.assertLess(shades[True],60)            # near-black 5"/38, 90 mm, Type 88, 12.7 cm bursts
        self.assertGreater(shades[False],90)        # grey 40/25/20 mm puffs

    def test_orange_flash_then_lingering_drifting_fade(self):
        a,b=ua.EFFECT_SEQ[1][1:3]
        for heavy in (True,False):
            layers,bones=ua.flak_layers(heavy)
            flash=[l for l in layers if l.material==rm.ADD]
            self.assertEqual(len(flash),1)
            self.assertGreater(alpha_at(flash[0],a+30),.5)
            self.assertEqual(alpha_at(flash[0],a+400),0)    # the flash is brief
            r,g,bl=flash[0].tris[0][1];self.assertGreater(r,200);self.assertLess(bl,120)
            for l in layers:
                if l.material!=rm.BLEND:continue
                self.assertGreater(alpha_at(l,a+2500),.3)    # still hanging in the sky
                self.assertEqual(alpha_at(l,b),0)            # gone by the end of Death
                drift=rm._sample(sorted(bones[l.bone].translation),b)
                self.assertGreater(drift[0],10)              # carried downwind (+x)
            self.assertEqual(alpha_at(flash[0],0),0)         # nothing shows in Stand

    def test_crash_effects_hold_until_the_dive_reaches_the_surface(self):
        delay=int(re.search(r'AIRCRAFT_CRASH_DELAY_MS (\d+)u',AIR_C)[1])
        a=ua.EFFECT_SEQ[1][1]
        self.assertEqual(delay,ua.CRASH_AT-a)
        for water in (True,False):
            layers,bones=ua.crash_layers(water)
            self.assertTrue(all(alpha_at(l,ua.CRASH_AT-20)==0 for l in layers if l.alpha))
            self.assertTrue(any(alpha_at(l,ua.CRASH_AT+200)>.5 for l in layers if l.alpha))
            self.assertEqual(sequences(ua.crash_mdx(water)),[(n,a,b) for n,a,b,_,_ in ua.EFFECT_SEQ])

    def test_server_model_names_are_generated(self):
        gen=(REPO/'tools/frontline/generate.py').read_text()
        for name in ('flak_heavy','flak_light','crash_sea','crash_land'):
            self.assertIn(f'Emberfield/Models/{name}.mdx',AIR_C)
            self.assertIn(name,gen)

class AircraftSequences(unittest.TestCase):
    def setUp(self):
        self.data=ua.aircraft_mdx('wildcat',imported.triangles('wildcat'))
        self.seqs=sequences(self.data)

    def test_original_sequences_keep_their_names_and_windows(self):
        self.assertEqual(self.seqs[:len(ua.UNIT_SEQ)],[(n,a,b) for n,a,b,_,_ in ua.UNIT_SEQ])

    def test_fire_spin_and_jink_variants(self):
        names=[s[0] for s in self.seqs]
        for tag in ('Fire','Wobble','Spin','Vapour','Jink'):
            for primary in ('Stand','Walk','Attack'):self.assertIn(f'{primary} {tag}',names)
        self.assertIn('Death Spin',names);self.assertIn('Death Wobble',names)
        self.assertEqual(len(names),len(set(names)))
        for x,y in zip(self.seqs,self.seqs[1:]):self.assertLess(x[2],y[1])   # no overlapping windows
        # The tag words the server publishes (s_air_effects.c) select these sequences.
        for tag in ('fire','wobble','spin','vapour','jink'):self.assertIn(f'"{tag}"',AIR_C)

    def test_dive_length_matches_the_server_crash_delay(self):
        for name in ('Death Spin','Death Wobble'):
            dive=next(s for s in self.seqs if s[0]==name)
            self.assertEqual(dive[2]-dive[1],ua.DEATH[1]-ua.DEATH[0])

    def test_trails_show_only_in_their_sequences(self):
        bones=[rm.Bone('Root')]
        smoke=ua.smoke_trail(bones,(0,0,0),30,ua.FIRE_WINDOWS)
        vapour=ua.smoke_trail(bones,(0,0,0),30,ua.VAPOUR_WINDOWS,colour=(238,240,242),fire=False,name='Vapour')
        self.assertEqual(sum(l.material==rm.ADD for l in vapour),0)        # no flame on a fuel leak
        self.assertEqual(sum(l.material==rm.ADD for l in smoke),1)
        self.assertLess(max(smoke[1].tris[0][1]),40);self.assertGreater(min(vapour[0].tris[0][1]),220)
        for layers,windows in ((smoke,ua.FIRE_WINDOWS),(vapour,ua.VAPOUR_WINDOWS)):
            for l in layers:
                self.assertTrue(any(alpha_at(l,a+300)>0 for a,b in windows))
                for n,a,b,_,_ in ua.AIR_SEQ:
                    if (a,b) not in windows:self.assertEqual(alpha_at(l,(a+b)//2),0,n)

if __name__=='__main__':
    unittest.main()
