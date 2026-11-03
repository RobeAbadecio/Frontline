#!/usr/bin/env python3
"""Export the assembled 1:1 metre-scale Yamato GLB and dimensioned review views.

python3 tools/frontline/yamato_asset.py --out build/yamato
No Blender installation or third-party mesh is required.
"""
from pathlib import Path
import argparse
import json
import math
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from PIL import Image, ImageDraw, ImageFont
from tools.frontline import yamato as y
from tools.frontline import gltf_import as gi


def glb(path):
    """glTF is Y-up; one unit = one metre. Editable named components/turrets."""
    document={'asset':{'version':'2.0','generator':'Frontline original Yamato reconstruction'},
              'scene':0,'scenes':[{'nodes':[0]}],
              'nodes':[{'name':'Yamato — April 1945 (metres)','children':[],
                        'extras':{'length_m':y.LENGTH,'beam_m':y.BEAM,'draft_m':y.DRAFT,
                                  'accuracy':'dimensioned reconstruction; fitting stations estimated',
                                  'light_aa_reconstruction':'50 triple 25mm + 6 single 25mm'}}],
              'meshes':[],'materials':[],'bufferViews':[],'accessors':[],'buffers':[]}
    blob=bytearray();materials={}

    def access(values,kind,fmt,component,minimum=None,maximum=None,target=34962):
        while len(blob)%4:blob.append(0)
        start=len(blob)
        for value in values:blob.extend(struct.pack('<'+fmt,*value))
        view=len(document['bufferViews'])
        document['bufferViews'].append({'buffer':0,'byteOffset':start,'byteLength':len(blob)-start,'target':target})
        obj={'bufferView':view,'componentType':component,'count':len(values),'type':kind}
        if minimum is not None:obj.update(min=minimum,max=maximum)
        document['accessors'].append(obj)
        return len(document['accessors'])-1

    def add_mesh(name,tris):
        groups={}
        for pts,colour,tag in tris:groups.setdefault(colour,[]).append(pts)
        primitives=[]
        for colour,faces in groups.items():
            if colour not in materials:
                # glTF baseColorFactor stores linear RGB.
                rgb=[v/255 for v in colour]
                rgb=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
                materials[colour]=len(document['materials'])
                document['materials'].append({'name':'RGB '+str(colour),'pbrMetallicRoughness':{
                    'baseColorFactor':rgb+[1],'metallicFactor':.15,'roughnessFactor':.78}})
            vertices=[];normals=[];indices=[];table={}
            for pts in faces:
                pts=tuple((a,c,-b) for a,b,c in pts)
                normal=gi._normal(*pts)
                for p in pts:
                    key=(p,normal)
                    if key not in table:
                        table[key]=len(vertices);vertices.append(p);normals.append(normal)
                    indices.append((table[key],))
            lo=[min(v[i] for v in vertices) for i in range(3)]
            hi=[max(v[i] for v in vertices) for i in range(3)]
            primitives.append({'attributes':{'POSITION':access(vertices,'VEC3','3f',5126,lo,hi),
                                             'NORMAL':access(normals,'VEC3','3f',5126)},
                               'indices':access(indices,'SCALAR','I',5125,target=34963),
                               'material':materials[colour]})
        index=len(document['meshes']);document['meshes'].append({'name':name,'primitives':primitives})
        return index

    for name,tris in y.body_parts().items():
        node={'name':name,'mesh':add_mesh(name,tris)}
        document['nodes'][0]['children'].append(len(document['nodes']));document['nodes'].append(node)
    turrets=[add_mesh('46cm triple gun turret',y.turret_m()),
             add_mesh('46cm turret with roof AA',y.turret_m(True))]
    for i,(x,yy,z) in enumerate(y.BATTERIES_M):
        node={'name':'Main turret '+('I','II','III')[i],'mesh':turrets[int(i>0)],'translation':[x,z,-yy]}
        if i==2:node['rotation']=[0,1,0,0]
        document['nodes'][0]['children'].append(len(document['nodes']));document['nodes'].append(node)
    document['buffers']=[{'byteLength':len(blob)}]
    data=json.dumps(document,separators=(',',':'),ensure_ascii=True).encode()
    data+=b' '*((-len(data))%4);blob+=b'\0'*((-len(blob))%4)
    path.write_bytes(struct.pack('<4sII',b'glTF',2,12+8+len(data)+8+len(blob))+
                     struct.pack('<I4s',len(data),b'JSON')+data+struct.pack('<I4s',len(blob),b'BIN\0')+blob)


def render(tris,width,height,azimuth=225,elevation=27):
    az,el=math.radians(azimuth),math.radians(elevation)
    view=(math.cos(az)*math.cos(el),math.sin(az)*math.cos(el),math.sin(el))
    right=(-math.sin(az),math.cos(az),0)
    up=gi._cross(view,right)
    project=lambda p:(gi._dot(p,right),-gi._dot(p,up))
    light=(.3,-.5,.81);faces=[]
    for pts,col,tag in tris:
        n=gi._normal(*pts)
        if gi._dot(n,view)<-.005:continue
        faces.append((sum(gi._dot(p,view) for p in pts)/3,[project(p) for p in pts],col,n))
    xs=[p[0] for _,ps,_,_ in faces for p in ps];ys=[p[1] for _,ps,_,_ in faces for p in ps]
    factor=min((width-80)/(max(xs)-min(xs)),(height-70)/(max(ys)-min(ys)))
    cx,cy=(max(xs)+min(xs))/2,(max(ys)+min(ys))/2
    # A depth buffer is essential: sorting whole triangles by their centers
    # made deck plates paint over small fittings and look like holes/stray fins.
    import numpy as np
    pixels=np.empty((height*2,width*2,3),dtype=np.uint8);pixels[:]=(20,32,43)
    depth_buffer=np.full((height*2,width*2),-np.inf,dtype=np.float32)
    for (pts,colour,tag) in tris:
        n=gi._normal(*pts)
        if gi._dot(n,view)<-.005:continue
        screen=[((project(p)[0]-cx)*factor*2+width,
                 (project(p)[1]-cy)*factor*2+height,gi._dot(p,view)) for p in pts]
        (ax,ay,az),(bx,by,bz),(cx_,cy_,cz)=screen
        xmin=max(0,int(math.floor(min(ax,bx,cx_))));xmax=min(width*2-1,int(math.ceil(max(ax,bx,cx_))))
        ymin=max(0,int(math.floor(min(ay,by,cy_))));ymax=min(height*2-1,int(math.ceil(max(ay,by,cy_))))
        if xmin>xmax or ymin>ymax:continue
        denominator=(by-cy_)*(ax-cx_)+(cx_-bx)*(ay-cy_)
        if abs(denominator)<1e-8:continue
        xx=np.arange(xmin,xmax+1,dtype=np.float32)[None,:]+.5
        yy=np.arange(ymin,ymax+1,dtype=np.float32)[:,None]+.5
        a=((by-cy_)*(xx-cx_)+(cx_-bx)*(yy-cy_))/denominator
        b=((cy_-ay)*(xx-cx_)+(ax-cx_)*(yy-cy_))/denominator
        c=1-a-b
        z=a*az+b*bz+c*cz
        target=depth_buffer[ymin:ymax+1,xmin:xmax+1]
        mask=(a>=-1e-5)&(b>=-1e-5)&(c>=-1e-5)&(z>target)
        if not mask.any():continue
        target[mask]=z[mask]
        shade=.65+.4*max(0,gi._dot(n,light))
        pixels[ymin:ymax+1,xmin:xmax+1][mask]=[min(255,int(v*shade)) for v in colour]
    return Image.fromarray(pixels).resize((width,height),Image.Resampling.LANCZOS)


def preview(path):
    tris=y.triangles(full=True,metres=True)
    im=Image.new('RGB',(2400,1800),(20,32,43));draw=ImageDraw.Draw(im)
    def font(size):
        try:return ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',size)
        except OSError:return ImageFont.load_default(size=size)
    draw.text((70,42),'YAMATO',font=font(58),fill=(235,228,211))
    draw.text((73,112),'APRIL 1945  /  ORIGINAL GAME MODEL',font=font(22),fill=(169,183,192))
    im.paste(render(tris,2400,1030,azimuth=55,elevation=24),(0,180))
    im.paste(render(tris,1500,300,azimuth=90,elevation=0),(40,1200))
    im.paste(render(tris,1500,260,azimuth=90,elevation=90),(40,1500))
    draw=ImageDraw.Draw(im)
    for yy in (1180,1488):draw.line((70,yy,1530,yy),fill=(66,84,97),width=1)
    for i,(title,value) in enumerate((('HULL LENGTH','263.0 m'),('HULL BEAM','38.9 m'),('MAIN BATTERY','9 × 460 mm'),
                                     ('FULL MODEL',f'{len(tris):,} triangles'),('SOURCE SCALE','1 unit = 1 metre'))):
        yy=1220+i*90
        draw.text((1670,yy),title,font=font(17),fill=(147,165,178))
        draw.text((1670,yy+26),value,font=font(29),fill=(235,228,211))
    draw.text((1670,1690),'Reference-based reconstruction',font=font(18),fill=(147,165,178))
    draw.text((1670,1722),'Fitting positions are estimated.',font=font(18),fill=(147,165,178))
    im.save(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=Path('build/yamato'))
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    glb(args.out/'Yamato-1945-metres.glb')
    preview(args.out/'Yamato-1945-review.png')
    render(y.triangles(full=True,metres=True),1800,1200,55,24).save(args.out/'Yamato-1945-hero.png')
    report={'hull_length_m':y.LENGTH,'hull_beam_m':y.BEAM,'draft_m':y.DRAFT,
            'source_unit':'metre','game_world_units_per_metre':y.WORLD_SCALE,
            'triangles_by_part':{k:len(v) for k,v in y.body_parts().items()},
            'full_model_triangles':len(y.triangles(True,True)),
            'turret_attachment_metres':y.BATTERIES_M,'turret_muzzle_metres':y.MUZZLE_M}
    (args.out/'dimensions.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
