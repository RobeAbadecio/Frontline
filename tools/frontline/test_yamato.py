"""Physical scale, attachment and emitted-asset contracts for the detailed ship."""
import json
import math
from pathlib import Path
import re
import struct
import tempfile
import unittest

from tools.frontline import catalog, models, ships, ship_states, yamato as y
from tools.frontline import gltf_import as gi
from tools.frontline.yamato_asset import glb


class YamatoAsset(unittest.TestCase):
    def test_real_hull_dimensions_are_preserved_uniformly(self):
        tris=[t for t in y.body_parts()['hull'] if t[2]=='hull']
        lo,hi=gi.bounds(tris)
        self.assertAlmostEqual(hi[0]-lo[0],263,places=5)
        self.assertAlmostEqual(hi[1]-lo[1],38.9,places=5)
        self.assertAlmostEqual(lo[2],-10.4,places=5)
        wlo,whi=gi.bounds(y.world(tris))
        for i in range(3):
            self.assertAlmostEqual(whi[i]-wlo[i],(hi[i]-lo[i])*y.WORLD_SCALE,places=5)
        self.assertAlmostEqual(whi[0]-wlo[0],344,places=5)

    def test_art_barbettes_and_runtime_batteries_have_one_source(self):
        spell=next(s for s in catalog.SPELLS if s['alias']=='Gyam')
        self.assertEqual(spell['DataA1'],3)
        self.assertEqual(spell['DataB1'],3)
        for i,(x,yy,z) in enumerate(models.BATTERIES['yamato']):
            self.assertAlmostEqual(spell[f'Data{chr(67+i)}1'],x)
            self.assertAlmostEqual(spell[f'Data{chr(71+i)}1'],z)
            barbette=[t for t in y.body_parts()['deck'] if t[2]=='barbette_'+str(i)]
            lo,hi=gi.bounds(y.world(barbette))
            self.assertAlmostEqual((lo[0]+hi[0])/2,x)
            self.assertAlmostEqual((lo[1]+hi[1])/2,yy)
            self.assertLess(lo[2],z);self.assertGreater(hi[2],z)

    def test_1945_armament_has_distinct_counted_mounts(self):
        tags={t[2] for t in y.body_parts()['armament']}
        for prefix,count in (('127mm_twin_',12),('25mm_triple_',46),('25mm_single_',6)):
            self.assertEqual(len([t for t in tags if re.fullmatch(prefix+r'\d+',t)]),count)
        self.assertEqual(ships.battery_model('yamato'),'yamato_turret')
        roof_tags={t[2] for t in y.turret_m(True) if re.fullmatch(r'25mm_triple_\d+',t[2])}
        self.assertEqual(len(roof_tags),2)
        self.assertEqual([ships.battery_model('yamato',i) for i in range(3)],
                         ['yamato_turret','yamato_turret_aa','yamato_turret_aa'])
        # Source geometry of three bored guns is reused, not the Iowa proxy.
        bore=[t for t in y.turret_m() if t[2]=='460mm_bore']
        lo,hi=gi.bounds(bore)
        self.assertAlmostEqual(hi[0],25.42,delta=.006)
        self.assertAlmostEqual(hi[1]-lo[1],6.96,places=4)
        for code in ('jyam','jmus'):
            self.assertAlmostEqual(catalog.UNITS[code]['launchx'],25.4*y.WORLD_SCALE)
            self.assertAlmostEqual(catalog.UNITS[code]['launchz'],4.25*y.WORLD_SCALE)

    def test_weather_deck_closes_the_hull_edge(self):
        # Ray-test the actual deck triangles just inside each hull station edge.
        # The old plank clipping dropped tapering wedges whenever one end vanished.
        deck=[pts for pts,_,tag in y.body_parts()['deck'] if tag in ('deck_plank','deck_surface')]
        def covers(pts,x,yy):
            a,b,c=pts
            cross=lambda p,q,r:(q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
            signed=[cross(a,b,(x,yy)),cross(b,c,(x,yy)),cross(c,a,(x,yy))]
            return min(signed)>=-1e-7 or max(signed)<=1e-7
        for i in range(1,33):
            a=-y.LENGTH/2+y.LENGTH*i/160;b=a+y.LENGTH/160
            x=(a+b)/2;edge=(y.width(a)+y.width(b))/2
            for sign in (-1,1):
                self.assertTrue(any(covers(p,x,sign*(edge-.01)) for p in deck),(i,sign))

    def test_geometry_is_finite_and_has_no_collapsed_faces(self):
        for pts,colour,tag in y.triangles(full=True,metres=True):
            self.assertTrue(all(math.isfinite(v) for p in pts for v in p),tag)
            n=gi._cross(gi._sub(pts[1],pts[0]),gi._sub(pts[2],pts[0]))
            self.assertGreater(gi._dot(n,n),1e-18,tag)

    def test_native_geosets_fit_uint16_and_preserve_wake(self):
        data=models.mesh('yamato');offset=4;geos=[];alpha=None;sequences=None
        while offset<len(data):
            tag,size=struct.unpack_from('<4sI',data,offset);payload=data[offset+8:offset+8+size]
            if tag==b'GEOS':
                at=0
                while at<len(payload):
                    length=struct.unpack_from('<I',payload,at)[0]
                    geo=payload[at+4:at+length];geos.append(geo);at+=length
                self.assertEqual(at,len(payload))
            if tag==b'GEOA':alpha=payload
            if tag==b'SEQS':sequences=payload
            offset+=size+8
        self.assertGreater(len(geos),6)
        total=0
        for geo in geos:
            vertices=struct.unpack_from('<I',geo,geo.index(b'VRTX')+4)[0]
            self.assertLess(vertices,65536)
            p=geo.index(b'PVTX');count=struct.unpack_from('<I',geo,p+4)[0]
            indices=struct.unpack_from('<'+str(count)+'H',geo,p+8)
            self.assertEqual(count%3,0);self.assertLess(max(indices),vertices);total+=count//3
        self.assertGreater(total,90000)
        self.assertIn(b'KGAO',alpha)
        self.assertIn(struct.pack('<If',ship_states.seq('Walk')[1],.6),alpha)
        self.assertIn(struct.pack('<I3f',ship_states.seq('Death')[2],0,0,-130),data)
        names=[sequences[i:i+80].split(b'\0')[0].decode() for i in range(0,len(sequences),132)]
        self.assertEqual(names,[s[0] for s in ship_states.SEQUENCES])
        for name in ('yamato_turret','yamato_turret_aa'):
            turret=models.mesh(name);at=turret.index(b'SEQS')
            size=struct.unpack_from('<I',turret,at+4)[0]
            # Attachments copy the hull frame: every condition must share times.
            ts=turret[at+8:at+8+size]
            self.assertEqual([ts[i:i+100] for i in range(0,size,132)],
                             [sequences[i:i+100] for i in range(0,len(sequences),132)])
        # Every split opaque hull section follows the same fade on Death/Decay.
        records=[];at=0
        while at<len(alpha):
            size=struct.unpack_from('<I',alpha,at)[0]
            records.append(alpha[at+28:at+size]);at+=size
        chunks=math.ceil(len(y.triangles())/9000)
        self.assertGreater(chunks,1)
        self.assertTrue(all(r==records[0] for r in records[:chunks]))

    def test_glb_is_an_assembled_editable_metre_scale_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'yamato.glb';glb(path);data=path.read_bytes()
            magic,version,length=struct.unpack_from('<4sII',data)
            self.assertEqual((magic,version,length),(b'glTF',2,len(data)))
            n=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+n])
            self.assertEqual(doc['nodes'][0]['extras']['length_m'],263)
            mounts=[node for node in doc['nodes'] if node['name'].startswith('Main turret ')]
            self.assertEqual(len(mounts),3)
            self.assertEqual(mounts[2]['rotation'],[0,1,0,0])
            self.assertNotEqual(mounts[0]['mesh'],mounts[1]['mesh'])
            self.assertEqual(mounts[1]['mesh'],mounts[2]['mesh'])
            self.assertEqual(mounts[0]['translation'],[50.5,8.9,0])
            self.assertTrue(all('scale' not in node for node in doc['nodes']))
            # The actual binary vertex positions, not only metadata, span metres.
            positions=[doc['accessors'][p['attributes']['POSITION']] for mesh in doc['meshes'] for p in mesh['primitives']]
            self.assertAlmostEqual(max(a['max'][0] for a in positions)-min(a['min'][0] for a in positions),263)


if __name__=='__main__':unittest.main()
