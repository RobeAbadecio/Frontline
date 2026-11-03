"""Naval base / repair yard art (tools/frontline/drydock.py) contracts."""
from pathlib import Path
import math
import subprocess
import tempfile
import unittest

from tools.frontline import drydock, gltf_import as gi, models
from tools.frontline.test_imported import geosets

REPO=Path(__file__).resolve().parents[2]
VARIANTS=tuple(drydock.VARIANTS)   # capital and escort yards, USN and IJN

class Drydock(unittest.TestCase):
    def test_both_variants_exist_and_differ(self):
        for name in VARIANTS:
            self.assertIn(name,drydock.MODELS)
            self.assertIn(name,models.GEOMETRY)   # packaged by generate.assets, iconed
        self.assertEqual(set(drydock.MODELS[n] for n in VARIANTS),{(v,s) for v in ('usn','ijn') for s in ('capital','escort')})
        for size in ('capital','escort'):
            usn,ijn=(n for n in VARIANTS if drydock.MODELS[n][1]==size)
            self.assertNotEqual({t[1] for t in drydock.triangles(usn)},{t[1] for t in drydock.triangles(ijn)},size)
        # The escort yard is the smaller one; the existing catalog model name aliases a variant.
        self.assertLess(gi.bounds(drydock.triangles('escortdock_usn'))[1][0],gi.bounds(drydock.triangles('drydock_usn'))[1][0])
        for alias,target in drydock.ALIASES.items():
            self.assertEqual(drydock.MODELS[alias],drydock.MODELS[target])
            self.assertEqual(drydock.BERTHS[alias],drydock.BERTHS[target])

    def test_triangle_budget(self):
        for name in VARIANTS:
            count=len(drydock.triangles(name))+len(drydock.parts(name)['weld'])
            self.assertLessEqual(count,drydock.TRIANGLE_BUDGET,name)
            self.assertGreater(count,2000,name)   # detailed, not a box silhouette

    def test_footprint_unchanged(self):
        # Drawn art only: the solid land body still blocks the existing 5x5-cell shipyard square.
        self.assertEqual(models.footprint_cells('shipyard'),[5,5])
        for name in VARIANTS:self.assertEqual(models.footprint_cells(name),[5,5])

    def test_berths_fit_the_drawn_yard(self):
        self.assertEqual(set(drydock.BERTHS),set(drydock.MODELS))
        for name in drydock.MODELS:
            berths,beams=drydock.BERTHS[name],drydock.BERTH_BEAM[name]
            lo,hi=gi.bounds(drydock.triangles(name))
            self.assertEqual(len(berths),len(beams),name)
            for (x,y,heading,length,radius),beam in zip(berths,beams):
                where=(name,x,y)
                self.assertIn(heading%360,(0,180),where)
                self.assertGreaterEqual(radius,beam/2,where)   # a ship nudged off-centre still repairs
                self.assertLessEqual(radius,length/2+1,where)
                ex,ey=length/2,beam/2   # headings are along x
                # Afloat beyond the quay, never over the solid land footprint.
                self.assertGreater(x-ex,drydock.QUAY_X,where)
                self.assertGreater(x-ex,drydock.LAND_HALF,where)
                # Within the drawn yard's seaward reach (a hull may overhang the gate line by 15);
                # the outboard berth lies in open water past the pier's side.
                self.assertLessEqual(x+ex,hi[0]+15,where)
                self.assertGreaterEqual(y-ey,lo[1]-1,where)
                self.assertGreaterEqual(length,185,where)   # a destroyer fits every berth
            # The dock berth sits between its walls and inside the caisson.
            drydock._use(drydock.MODELS[name][1])
            x,y,_,length,_=berths[0]
            self.assertLessEqual(abs(y-drydock.DOCK_Y)+beams[0]/2,drydock.DOCK_HALF,name)
            self.assertLessEqual(x+length/2,drydock.DOCK_X1,name)
            self.assertGreaterEqual(x-length/2,drydock.DOCK_X0,name)
        # Capital yards take the longest hulls (Iowa 339, Yamato 354 overhangs); escort yards cruisers.
        self.assertGreaterEqual(max(b[3] for b in drydock.BERTHS['drydock_usn']),345)
        self.assertGreaterEqual(max(b[3] for b in drydock.BERTHS['escortdock_usn']),259)

    def test_mdx_materials_and_animation(self):
        for name in VARIANTS+('shipyard',):
            data=models.mesh(name)
            mats={m for m,_ in geosets(data)}
            self.assertEqual(mats,{0,1,3},name)   # palette, team colour, additive welding arcs
            for tag in (b'KGRT',b'KGTR',b'KGAO',b'Stand Work'):self.assertIn(tag,data,name)

    @unittest.skipUnless((REPO/'build/bin/mdxtool').is_file() and (REPO/'build/bin/mpqtool').is_file(),'make mdxtool mpqtool')
    def test_models_load_in_mdxtool(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'content';(root/'Emberfield/Models').mkdir(parents=True)
            args=[str(REPO/'build/bin/mpqtool'),'-mpq',str(Path(tmp)/'test.mpq'),'pack']
            for name in VARIANTS:
                path=root/f'Emberfield/Models/{name}.mdx';path.write_bytes(models.mesh(name))
                args+=[str(path),f'Emberfield/Models/{name}.mdx']
            subprocess.run(args,check=True,stdout=subprocess.DEVNULL)
            for name in VARIANTS:
                result=subprocess.run([str(REPO/'build/bin/mdxtool'),'-mpq',str(Path(tmp)/'test.mpq'),'-model',f'Emberfield/Models/{name}.mdx','--info'],
                                      capture_output=True,text=True,check=True)
                self.assertIn(f'SEQS: count={len(drydock.SEQUENCES)}',result.stderr,name)
                self.assertIn('CAMS: count=1',result.stderr,name)
                self.assertIn('PIVT: count=4',result.stderr,name)   # Root, Crane, Travel, Gate

if __name__=='__main__':unittest.main()


class RepairReach(unittest.TestCase):
    def test_every_berth_lies_inside_the_dock_repair_radius(self):
        # s_veterancy.c CAbilityDockRepair repairs ships within the yard's collision plus Fdck
        # DataB1 (plus the ship's own collision) of the yard centre; BERTHS only places them.
        from tools.frontline import catalog, drydock
        reach=next(s['DataB1'] for s in catalog.SPELLS if s['alias']=='Fdck')
        for code,u in catalog.UNITS.items():
            if u.get('model')!='shipyard' and u.get('model') not in drydock.MODELS:continue
            for x,y,heading,length,radius in drydock.BERTHS[u['model']]:
                with self.subTest(code=code,berth=(x,y)):
                    self.assertLessEqual(math.hypot(x,y)+length/2,u.get('collision',0)+reach)


class LevelWhileWorking(unittest.TestCase):
    def test_yard_stays_level_outside_death_and_decay(self):
        # Robe's playtest: the yard sank while producing. WC3 holds a track's value through a
        # sequence from the global key list, so Work / Stand Work interpolated toward Decay's -60.
        from tools.frontline import rich_mdx as rm
        windows=[(a,b) for n,a,b,_,_ in drydock.SEQUENCES]
        sunk={n for n in ('Death','Decay')}
        keys=rm.densify(drydock.root_track(),windows)
        for name,a,b,_,_ in drydock.SEQUENCES:
            if name in sunk:continue
            for t,x,y,z in keys:
                if a<=t<=b:
                    with self.subTest(sequence=name,t=t):self.assertEqual(z,0)


class Gate(unittest.TestCase):
    def test_caisson_opens_only_in_stand_alternate_and_stays_shut_while_working(self):
        from tools.frontline import rich_mdx as rm
        windows=[(a,b) for n,a,b,_,_ in drydock.SEQUENCES]
        span={n:(a,b) for n,a,b,_,_ in drydock.SEQUENCES}
        for name in drydock.VARIANTS:
            with self.subTest(name=name):
                keys=rm.densify(drydock.gate_track(drydock.parts(name)['gate_slide']),windows)
                for seq,(a,b) in span.items():
                    inside=[k for k in keys if a<=k[0]<=b]
                    if seq=='Stand Alternate':
                        self.assertGreater(abs(inside[-1][2]),2*drydock.DOCK_HALF)   # clear of the entrance
                    else:
                        self.assertTrue(all(k[1:]==(0,0,0) for k in inside),seq)     # closed (Stand Work: docked)
                self.assertTrue(dict((n,o) for n,_,_,_,o in drydock.SEQUENCES)['Stand Alternate'])  # non-looping hold
