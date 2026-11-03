"""Torpedo and armour-hit effect models (naval_fx.py): load in mdxtool, sizes, budgets, tubes."""
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

from tools.frontline import naval_fx, unit_anim, historical_models as hm
from tools.frontline import gltf_import as gi

REPO=Path(__file__).resolve().parents[2]
MDXTOOL=REPO/'build/bin/mdxtool';MPQTOOL=REPO/'build/bin/mpqtool'

def bounds(data):
    i=data.find(b'MODL')
    return struct.unpack('<7f',data[i+8+340:i+8+368])   # radius, min xyz, max xyz

def triangles(data):
    total=0;i=0
    while (i:=data.find(b'PCNT',i))>=0:
        total+=struct.unpack('<I',data[i+8:i+12])[0];i+=4
    return total

class NavalEffects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data={name:naval_fx.mdx(name) for name in naval_fx.MODELS}

    @unittest.skipUnless(MDXTOOL.exists() and MPQTOOL.exists(),'make mdxtool mpqtool')
    def test_models_load_in_mdxtool_with_expected_sequences(self):
        from tools.emberfield import generate as base
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'content';args=[str(MPQTOOL),'-mpq',str(Path(tmp)/'fx.mpq'),'pack']
            for name,data in self.data.items():base.write(root,f'Emberfield/Models/{name}.mdx',data)
            base.write(root,gi.PALETTE_TEXTURE.replace('\\','/'),base.art.blp_bytes(gi.palette_image(),True))
            for p in sorted(root.rglob('*')):
                if p.is_file():args+=[str(p),str(p.relative_to(root))]
            subprocess.run(args,check=True,stdout=subprocess.DEVNULL)
            for name in naval_fx.MODELS:
                with self.subTest(name):
                    r=subprocess.run([str(MDXTOOL),'-mpq',str(Path(tmp)/'fx.mpq'),'-model',f'Emberfield/Models/{name}.mdx','--info'],
                                     capture_output=True,text=True,check=True)
                    seqs=unit_anim.UNIT_SEQ if name=='torpedo' else unit_anim.EFFECT_SEQ
                    self.assertIn(f'SEQS: count={len(seqs)}',r.stderr)
                    for seq in seqs:self.assertIn(seq[0],r.stdout+r.stderr)

    def test_torpedo_hit_column_dwarfs_the_near_miss_splash(self):
        # The splash column swells to 1.2x its static height (unit_anim.splash_mdx keys).
        splash=bounds(unit_anim.splash_mdx())[6]*1.2
        self.assertGreaterEqual(bounds(self.data['torpedo_hit'])[6],3*splash)

    def test_torpedo_runs_at_the_surface_bow_forward(self):
        r,x0,y0,z0,x1,y1,z1=bounds(self.data['torpedo'])
        self.assertLess(z1,4);self.assertGreater(z0,-4)          # body and wake hug the waterline
        self.assertLess(x0,-60)                                   # the wake trails well astern
        self.assertLess(abs(y0),20);self.assertLess(abs(y1),20)

    def test_triangle_budgets(self):
        budget={'torpedo':400,'torpedo_hit':2500,'torpedo_launch':800,'armor_spark':800,'launch_wake':1200}
        for name,data in self.data.items():
            with self.subTest(name):self.assertLessEqual(triangles(data),budget[name])

    def test_effect_lifetimes(self):
        spans={'torpedo_hit':(4000,6000),'torpedo_launch':(1200,1800),'armor_spark':(800,1300),'launch_wake':(4500,6000)}
        for name,(lo,hi) in spans.items():
            # Every geoset fades to zero by the end of its lifetime.
            data=self.data[name];ends=[];j=data.find(b'GEOA')
            while (j:=data.find(b'KGAO',j))>=0:
                n=struct.unpack('<I',data[j+4:j+8])[0]
                keys=[struct.unpack('<If',data[j+16+8*k:j+24+8*k]) for k in range(n)]
                last=max(t for t,v in keys if v>0)
                ends.append(min(t for t,v in keys if t>last)-naval_fx.D0);j+=4
            with self.subTest(name):
                self.assertGreaterEqual(max(ends),lo);self.assertLessEqual(max(ends),hi)

    def test_tubes_follow_the_drawn_mounts(self):
        expected={'fletcher':2,'sumner':2,'atlanta':2,'fubuki':3,'kagero':2,'akizuki':1,'mogami':4,'takao':4,'myoko':4,'destroyer':2}
        self.assertEqual({k:len(v) for k,v in naval_fx.TUBES.items()},expected)
        from tools.frontline import ships
        for name,mounts in naval_fx.TUBES.items():
            if name=='destroyer':continue
            lo,hi=gi.bounds(ships.triangles(name))
            for x,y,z in mounts:
                with self.subTest(name):
                    self.assertTrue(lo[0]<x<hi[0] and lo[1]<y<hi[1]);self.assertTrue(10<z<20)

if __name__=='__main__':unittest.main()
