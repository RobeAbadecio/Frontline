"""Third-party glTF (GLB) meshes -> compact Frontline MDX.

Pure Python + PIL, no runtime I/O: generate.py reads the CC0 sources in
third_party/, bakes each face's colour (material factor x texture x vertex
colour) into one shared palette atlas, decimates with quadric edge collapse
to a triangle budget, fits the result to the existing unit footprint and
emits MDX with the same sequences/bone tracks as the procedural boxes.
"""
from pathlib import Path
import heapq
import io
import json
import math
import struct

from PIL import Image

from tools.emberfield import models as base

P=base.P;S=base.S;CH=base.CH
SOURCE=Path(__file__).resolve().parents[2]/'third_party'/'source'
PALETTE_TEXTURE='Emberfield\\Textures\\imported.blp'
TEAM=-1                      # face colour sentinel: drawn with the replaceable team colour

# ---------------------------------------------------------------- GLB reading
COMPONENTS={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
FORMATS={5120:'b',5121:'B',5122:'h',5123:'H',5125:'I',5126:'f'}
def _mat_mul(a,b):
    return [sum(a[r+4*k]*b[k+4*c] for k in range(4)) for c in range(4) for r in range(4)]
def _trs(node):
    if 'matrix' in node:return list(node['matrix'])
    tx,ty,tz=node.get('translation',(0,0,0));x,y,z,w=node.get('rotation',(0,0,0,1));sx,sy,sz=node.get('scale',(1,1,1))
    r=[1-2*(y*y+z*z),2*(x*y+z*w),2*(x*z-y*w),2*(x*y-z*w),1-2*(x*x+z*z),2*(y*z+x*w),2*(x*z+y*w),2*(y*z-x*w),1-2*(x*x+y*y)]
    return [r[0]*sx,r[1]*sx,r[2]*sx,0,r[3]*sy,r[4]*sy,r[5]*sy,0,r[6]*sz,r[7]*sz,r[8]*sz,0,tx,ty,tz,1]
def _apply(m,v,w=1):
    return tuple(m[r]*v[0]+m[r+4]*v[1]+m[r+8]*v[2]+m[r+12]*w for r in range(3))

def read_glb(path,include=None,exclude=(),pose=None,pose_time=0.0,bones=None,mirror=()):
    """Triangles as [(p0,p1,p2),(r,g,b),material_name] in glTF space (Y up).
    include/exclude filter mesh nodes by name (bones may share names). `pose`
    names an animation sampled at `pose_time` seconds (skinned meshes follow);
    `bones`, if a dict, receives each node's world origin by name."""
    data=Path(path).read_bytes()
    assert data[:4]==b'glTF',path
    offset=12;gltf=None;binary=b''
    while offset<len(data):
        size,kind=struct.unpack_from('<I4s',data,offset)
        chunk=data[offset+8:offset+8+size]
        if kind==b'JSON':gltf=json.loads(chunk)
        elif kind==b'BIN\0':binary=chunk
        offset+=8+size
    def view(index):
        v=gltf['bufferViews'][index];start=v.get('byteOffset',0)
        return binary[start:start+v['byteLength']],v.get('byteStride')
    def accessor(index):
        a=gltf['accessors'][index];raw,stride=view(a['bufferView'])
        fmt=FORMATS[a['componentType']];n=COMPONENTS[a['type']];size=struct.calcsize(fmt)
        stride=stride or size*n;start=a.get('byteOffset',0);out=[]
        for i in range(a['count']):
            v=struct.unpack_from('<'+fmt*n,raw,start+i*stride)
            if a.get('normalized'):v=tuple(x/{'B':255,'H':65535,'b':127,'h':32767}[fmt] for x in v)
            out.append(v if n>1 else v[0])
        return out
    images={}
    def image(index):
        if index not in images:
            src=gltf['images'][index]
            raw,_=view(src['bufferView'])
            images[index]=Image.open(io.BytesIO(raw)).convert('RGBA')
        return images[index]
    def material(index):
        if index is None:return (1,1,1,1),None,'default'
        m=gltf['materials'][index];pbr=m.get('pbrMetallicRoughness',{})
        tex=pbr.get('baseColorTexture')
        img=image(gltf['textures'][tex['index']]['source']) if tex else None
        return tuple(pbr.get('baseColorFactor',(1,1,1,1))),img,m.get('name',f'm{index}')
    tris=[];identity=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
    def walk(node_index,parent,on):
        node=gltf['nodes'][node_index];world=_mat_mul(parent,_trs(node))
        name=node.get('name','')
        on='mesh' in node and name not in exclude and (include is None or name in include)
        if 'mesh' in node and on:
            for prim in gltf['meshes'][node['mesh']]['primitives']:
                if prim.get('mode',4)!=4:continue
                at=prim['attributes'];pos=accessor(at['POSITION'])
                uv=accessor(at['TEXCOORD_0']) if 'TEXCOORD_0' in at else None
                col=accessor(at['COLOR_0']) if 'COLOR_0' in at else None
                idx=accessor(prim['indices']) if 'indices' in prim else list(range(len(pos)))
                factor,img,name=material(prim.get('material'))
                if 'skin' in node and 'JOINTS_0' in at:
                    # Rest pose: blend joint world x inverse bind (a skinned node's own transform is ignored).
                    skin=gltf['skins'][node['skin']]
                    inverse=accessor(skin['inverseBindMatrices']) if 'inverseBindMatrices' in skin else [identity]*len(skin['joints'])
                    joint=[_mat_mul(worlds[j],list(m)) for j,m in zip(skin['joints'],inverse)]
                    pts=[]
                    for p,js,ws in zip(pos,accessor(at['JOINTS_0']),accessor(at['WEIGHTS_0'])):
                        total=sum(ws) or 1
                        moved=[_apply(joint[j],p) for j,w in zip(js,ws) if w>0]
                        weights=[w/total for w in ws if w>0]
                        pts.append(tuple(sum(m[i]*w for m,w in zip(moved,weights)) for i in range(3)))
                else:pts=[_apply(world,p) for p in pos]
                for t in range(0,len(idx)-2,3):
                    a,b,c=idx[t],idx[t+1],idx[t+2]
                    rgb=list(factor[:3])
                    if img is not None and uv:
                        u=(uv[a][0]+uv[b][0]+uv[c][0])/3;v=(uv[a][1]+uv[b][1]+uv[c][1])/3
                        px=img.getpixel((int(u%1*img.width)%img.width,int(v%1*img.height)%img.height))
                        rgb=[rgb[i]*px[i]/255 for i in range(3)]
                    if col:rgb=[rgb[i]*(col[a][i]+col[b][i]+col[c][i])/3 for i in range(3)]
                    # glTF colour factors are linear; the atlas is sRGB.
                    srgb=tuple(int(round(255*(1.055*max(0,x)**(1/2.4)-.055 if x>.0031308 else 12.92*x))) for x in rgb)
                    tris.append(((pts[a],pts[b],pts[c]),tuple(max(0,min(255,x)) for x in srgb),name))
        for child in node.get('children',()):walk(child,world,on)
    if pose:
        anim=next(a for a in gltf['animations'] if a['name']==pose)
        for channel in anim['channels']:
            sampler=anim['samplers'][channel['sampler']]
            times=accessor(sampler['input']);values=accessor(sampler['output'])
            if sampler.get('interpolation')=='CUBICSPLINE':values=values[1::3]
            k=max([i for i,t in enumerate(times) if t<=pose_time+1e-6] or [0])
            node=gltf['nodes'][channel['target']['node']];node.pop('matrix',None)
            node[channel['target']['path']]=list(values[k])
    # `mirror` copies .R bone rotations onto their .L twins (Blender-mirrored rig):
    # a one-handed pointing pose becomes a two-handed long-gun hold.
    by_name={nd.get('name'):nd for nd in gltf['nodes']}
    for bone in mirror:
        src,dst=by_name[bone+'.R'],by_name[bone+'.L']
        x,y,z,w=src.get('rotation',(0,0,0,1));dst['rotation']=[x,-y,-z,w]
    scene=gltf['scenes'][gltf.get('scene',0)]
    worlds={}
    def world_of(i,parent):
        worlds[i]=_mat_mul(parent,_trs(gltf['nodes'][i]))
        for c in gltf['nodes'][i].get('children',()):world_of(c,worlds[i])
    for root in scene['nodes']:world_of(root,identity)
    for root in scene['nodes']:walk(root,identity,False)
    if bones is not None:
        for i,m in worlds.items():bones[gltf['nodes'][i].get('name',str(i))]=(m[12],m[13],m[14])
    return tris

# ---------------------------------------------------------------- geometry ops
def to_engine(tris,yaw=0):
    """glTF Y-up/+Z-forward -> engine Z-up/+X-forward, then an extra yaw in degrees."""
    c,s=math.cos(math.radians(yaw)),math.sin(math.radians(yaw))
    out=[]
    for pts,colour,name in tris:
        conv=[]
        for x,y,z in pts:
            ex,ey=z,x
            conv.append((ex*c-ey*s,ex*s+ey*c,y))
        out.append((tuple(conv),colour,name))
    return out

def bounds(tris):
    pts=[p for t in tris for p in t[0]]
    return [min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]

def transform(tris,scale=1,offset=(0,0,0),yaw=0):
    c,s=math.cos(math.radians(yaw)),math.sin(math.radians(yaw))
    sx,sy,sz=scale if isinstance(scale,tuple) else (scale,)*3
    return [(tuple(((x*c-y*s)*sx+offset[0],(x*s+y*c)*sy+offset[1],z*sz+offset[2]) for x,y,z in pts),colour,name) for pts,colour,name in tris]

def fit(tris,size,axis='xy',ground=True):
    """Uniform scale so the horizontal extent matches `size` (largest of x/y,
    or the given axis), centred on the origin, base resting at z=0."""
    lo,hi=bounds(tris)
    extent={'x':hi[0]-lo[0],'y':hi[1]-lo[1],'z':hi[2]-lo[2],'xy':max(hi[0]-lo[0],hi[1]-lo[1])}[axis]
    k=size/max(extent,1e-6)
    cx,cy=(lo[0]+hi[0])/2,(lo[1]+hi[1])/2
    return transform(tris,k,(-cx*k,-cy*k,-lo[2]*k if ground else 0))

def recolour(tris,mapping):
    """mapping: material name or (r,g,b) -> (r,g,b) or TEAM."""
    out=[]
    for pts,colour,name in tris:
        new=mapping.get(name,mapping.get(colour,colour))
        out.append((pts,new,name))
    return out

def boxes(items):
    """Procedural (x,y,z,hx,hy,h,colour) boxes as triangles; colour may be TEAM."""
    out=[]
    for x,y,z,w,d,h,colour in items:
        c=[(x-w,y-d,z),(x+w,y-d,z),(x+w,y+d,z),(x-w,y+d,z),(x-w,y-d,z+h),(x+w,y-d,z+h),(x+w,y+d,z+h),(x-w,y+d,z+h)]
        for f in ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)):
            out.append(((c[f[0]],c[f[1]],c[f[2]]),colour,'box'))
            out.append(((c[f[0]],c[f[2]],c[f[3]]),colour,'box'))
    return out

def _sub(a,b):return (a[0]-b[0],a[1]-b[1],a[2]-b[2])
def _cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def _dot(a,b):return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def _normal(p0,p1,p2):
    n=_cross(_sub(p1,p0),_sub(p2,p0));l=math.sqrt(_dot(n,n))
    return (n[0]/l,n[1]/l,n[2]/l) if l>1e-12 else (0,0,1)

def decimate(tris,target):
    """Quadric edge collapse (Garland-Heckbert) to at most `target` triangles.
    Colour borders and open edges get strong boundary planes so silhouettes
    and paint regions survive; collapses that flip a face are rejected."""
    if len(tris)<=target:return tris
    key=lambda p:(round(p[0],5),round(p[1],5),round(p[2],5))
    index={};verts=[];faces=[]
    for pts,colour,name in tris:
        ids=[]
        for p in pts:
            k=key(p)
            if k not in index:index[k]=len(verts);verts.append(list(p))
            ids.append(index[k])
        if len(set(ids))==3:faces.append([ids[0],ids[1],ids[2],colour,name])
    Q=[[0.0]*10 for _ in verts]
    def plane_q(n,d,w):
        a,b,c=n
        return [w*a*a,w*a*b,w*a*c,w*a*d,w*b*b,w*b*c,w*b*d,w*c*c,w*c*d,w*d*d]
    def add(q,r):
        for i in range(10):q[i]+=r[i]
    def cost(q,v):
        x,y,z=v
        return (q[0]*x*x+2*q[1]*x*y+2*q[2]*x*z+2*q[3]*x+q[4]*y*y+2*q[5]*y*z+2*q[6]*y+q[7]*z*z+2*q[8]*z+q[9])
    edges={}
    for fi,(a,b,c,colour,_) in enumerate(faces):
        p0,p1,p2=verts[a],verts[b],verts[c]
        n=_cross(_sub(p1,p0),_sub(p2,p0));area=math.sqrt(_dot(n,n))
        if area<1e-12:continue
        n=(n[0]/area,n[1]/area,n[2]/area);q=plane_q(n,-_dot(n,p0),area)
        for v in (a,b,c):add(Q[v],q)
        for u,v in ((a,b),(b,c),(c,a)):
            edges.setdefault((min(u,v),max(u,v)),[]).append((fi,n,colour))
    for (u,v),adj in edges.items():
        if len(adj)==1 or len({x[2] for x in adj})>1:
            e=_sub(verts[v],verts[u])
            for _,n,_ in adj:
                m=_cross(e,n);l=math.sqrt(_dot(m,m))
                if l<1e-12:continue
                m=(m[0]/l,m[1]/l,m[2]/l);q=plane_q(m,-_dot(m,verts[u]),_dot(e,e)*50)
                add(Q[u],q);add(Q[v],q)
    vfaces=[set() for _ in verts]
    for fi,f in enumerate(faces):
        for v in f[:3]:vfaces[v].add(fi)
    alive=[True]*len(faces);live=sum(1 for _ in faces);version=[0]*len(verts)
    def best(u,v):
        q=[Q[u][i]+Q[v][i] for i in range(10)]
        mid=[(verts[u][i]+verts[v][i])/2 for i in range(3)]
        return min((cost(q,p),p) for p in (verts[u],verts[v],mid))
    heap=[]
    for u,v in edges:
        c,p=best(u,v);heap.append((c,u,v,0,0))
    heapq.heapify(heap)
    while live>target and heap:
        c,u,v,vu,vv=heapq.heappop(heap)
        if vu!=version[u] or vv!=version[v] or u==v:continue
        _,p=best(u,v)
        # Reject collapses that flip any surviving neighbour face.
        flip=False
        for fi in (vfaces[u]|vfaces[v]):
            f=faces[fi]
            if u in f[:3] and v in f[:3]:continue
            pts=[verts[x] for x in f[:3]];newpts=[p if x in (u,v) else verts[x] for x in f[:3]]
            n0=_normal(*pts);n1=_normal(*newpts)
            if _dot(n0,n1)<.2:flip=True;break
        if flip:
            version[u]+=1;version[v]+=1
            continue
        verts[u]=list(p);add(Q[u],Q[v])
        for fi in list(vfaces[v]):
            f=faces[fi]
            if u in f[:3]:
                alive[fi]=False;live-=1
                for x in f[:3]:vfaces[x].discard(fi)
            else:
                f[f.index(v)]=u;vfaces[u].add(fi)
        vfaces[v]=set();version[u]+=1;version[v]+=1
        neigh={x for fi in vfaces[u] for x in faces[fi][:3]}-{u}
        for w in neigh:
            c,_=best(u,w);a,b=min(u,w),max(u,w)
            heapq.heappush(heap,(c,a,b,version[a],version[b]))
    return [((tuple(verts[f[0]]),tuple(verts[f[1]]),tuple(verts[f[2]])),f[3],f[4]) for i,f in enumerate(faces) if alive[i]]

# ---------------------------------------------------------------- palette atlas
CELL=16;GRID=32                # 512x512 atlas, 1024 colours
_palette={}
def palette_uv(colour):
    """Centre of the atlas cell holding this sRGB colour (merged to 4-bit steps)."""
    colour=tuple(min(255,(c//4)*4+2) for c in colour)
    if colour not in _palette:
        if len(_palette)>=GRID*GRID:
            colour=min(_palette,key=lambda p:sum((a-b)**2 for a,b in zip(p,colour)))
        else:_palette[colour]=len(_palette)
    i=_palette[colour]
    return ((i%GRID+.5)/GRID,(i//GRID+.5)/GRID)

def palette_image():
    im=Image.new('RGBA',(CELL*GRID,CELL*GRID),(255,0,255,255))
    for colour,i in _palette.items():
        im.paste((*colour,255),(i%GRID*CELL,i//GRID*CELL,(i%GRID+1)*CELL,(i//GRID+1)*CELL))
    return im

# ---------------------------------------------------------------- MDX emission
DEATH_ONLY=[(0,0.),(2999,0.),(3000,1.),(3999,1.),(4000,0.),(7999,0.)]
NOT_DEATH=[(0,1.),(2999,1.),(3000,0.),(3999,0.),(4000,1.),(7999,1.)]
WALK_ONLY=[(0,0.),(999,0.),(1000,.6),(1999,.6),(2000,0.),(7999,0.)]
def mdx(name,tris,translation=None,scale=None,smooth=35,burst=None,layers=(),body_alpha=None):
    """Two materials like base.mesh: 0 = palette atlas, 1 = team colour.
    Vertices sharing a position and colour average normals within `smooth` degrees.
    `layers` are extra palette geosets with their own alpha keys (ship wake foam:
    WALK_ONLY); `body_alpha` keys the main geosets. `burst` is shorthand for a
    projectile's impact fireball: shown only in Death while the body is hidden."""
    layers=list(layers)
    if burst:layers.append((burst,DEATH_ONLY));body_alpha=NOT_DEATH
    lo,hi=bounds(tris+[t for extra,_ in layers for t in extra])
    extent=max(abs(v) for v in lo+hi);top=hi[2]
    radius=math.sqrt(sum(max(abs(a),abs(b))**2 for a,b in zip(lo,hi)))
    bnd=P('7f',radius,*lo,*hi)
    seq=b''.join(S(n,80)+P('2IfIfI',i*1000,(i+1)*1000-1,270 if n=='Walk' else 0,int(n in ['Death','Birth','Decay']),0,0)+bnd for i,n in enumerate(['Stand','Walk','Attack','Death','Birth','Work','Stand Work','Decay']))
    textures=P('I',0)+S(PALETTE_TEXTURE,260)+P('I',0)+P('I',1)+S('',260)+P('I',0)
    materials=b'';geosets=b''
    limit=math.cos(math.radians(smooth))
    for mat in range(2):
        layer=P('I5If',28,0,0x10,mat,0xffffffff,0,1)
        m=P('2I',0,0)+b'LAYS'+P('I',1)+layer
        materials+=P('I',len(m)+4)+m
    parts=[(mat,[t for t in tris if (t[1]==TEAM)==(mat==1)],body_alpha) for mat in range(2)]
    parts+=[(0,extra,keys) for extra,keys in layers]
    alphas=b'';geoset_id=0
    for mat,group,keys in parts:
        if not group:continue
        fn=[_normal(*t[0]) for t in group]
        acc={}
        for (pts,colour,_),n in zip(group,fn):
            for p in pts:acc.setdefault((tuple(round(c,3) for c in p),colour),[]).append(n)
        verts=[];normals=[];uv=[];indices=[];table={}
        for (pts,colour,_),n in zip(group,fn):
            coords=(.5,.5) if colour==TEAM else palette_uv(colour)
            for p in pts:
                k=(tuple(round(c,3) for c in p),colour)
                sm=[x for x in acc[k] if _dot(x,n)>=limit]
                s=[sum(x[i] for x in sm) for i in range(3)];l=math.sqrt(_dot(s,s)) or 1
                nn=(round(s[0]/l,3),round(s[1]/l,3),round(s[2]/l,3))
                vk=(k,nn)
                if vk not in table:
                    table[vk]=len(verts);verts.append(p);normals.append(nn);uv.append(coords)
                indices.append(table[vk])
        assert len(verts)<65536,name
        sub=lambda t,c,b:t.encode()+P('I',c)+b
        n=len(verts)
        geo=sub('VRTX',n,b''.join(P('3f',*v) for v in verts))+sub('NRMS',n,b''.join(P('3f',*v) for v in normals))+sub('UVBS',n,b''.join(P('2f',*v) for v in uv))
        geo+=sub('PTYP',1,P('I',4))+sub('PCNT',1,P('I',len(indices)//3))+sub('PVTX',len(indices),P(str(len(indices))+'H',*indices))
        geo+=sub('GNDX',n,bytes(n))+sub('MTGC',1,P('I',1))+sub('UVAS',1,b'')+sub('MATS',1,P('4I',0,mat,0,0)+bnd+P('I',0))
        geosets+=P('I',len(geo)+4)+geo
        if keys:
            kg=b'KGAO'+P('3I',len(keys),0,0xffffffff)+b''.join(P('If',*k) for k in keys)
            alphas+=P('IfI3fI',28+len(kg),1,0,1,1,1,geoset_id)+kg
        geoset_id+=1
    track=b''
    vec=lambda k,pad:(k[0],*(k[1:] if len(k)==4 else (pad,pad,k[1]) if pad==0 else (k[1],)*3))
    if translation:track+=b'KGTR'+P('3I',len(translation),1,0xffffffff)+b''.join(P('I3f',*vec(k,0)) for k in translation)
    if scale:track+=b'KGSC'+P('3I',len(scale),1,0xffffffff)+b''.join(P('I3f',*vec(k,1)) for k in scale)
    bone=P('I',96+len(track))+S('Root',80)+P('3I',0,0xffffffff,256)+track+P('2I',0,0xffffffff)
    distance=max(160,extent*2.8)
    camera=P('I',120)+S('Portrait',80)+P('3f3f3f',distance,-distance,extent*.9,.55,4000,1,0,0,top*.45)
    return b'MDLX'+CH('VERS',P('I',800))+CH('MODL',S('Frontline '+name,80)+S('',260)+bnd+P('I',100))+CH('SEQS',seq)+CH('TEXS',textures)+CH('MTLS',materials)+CH('GEOS',geosets)+CH('BONE',bone)+CH('PIVT',P('3f',0,0,0))+CH('CAMS',camera)+(CH('GEOA',alphas) if alphas else b'')

_cache={}
def load(name,yaw=0,include=None,exclude=(),pose=None,pose_time=0.0,mirror=()):
    """Engine-space triangles of third_party/source/polypizza/<name>.glb (cached)."""
    key=(name,yaw,include and tuple(include),tuple(exclude),pose,pose_time,tuple(mirror))
    if key not in _cache:_cache[key]=to_engine(read_glb(SOURCE/'polypizza'/f'{name}.glb',include,exclude,pose,pose_time,None,mirror),yaw)
    return _cache[key]

def load_bones(name,pose=None,pose_time=0.0,yaw=0,mirror=()):
    """Engine-space world origin of every node (e.g. 'Wrist.R') in the given pose."""
    bones={}
    read_glb(SOURCE/'polypizza'/f'{name}.glb',(),(),pose,pose_time,bones,mirror)
    return {k:to_engine([((v,v,v),(0,0,0),'')],yaw)[0][0][0] for k,v in bones.items()}

def preview(tris,size=256,background=(0,0,0,0),margin=.08):
    """Painter's-algorithm isometric render (icons, contact sheets): front-left view, sun from the upper left."""
    def proj(p):return (p[0]*.70-p[1]*.70,-p[2]*.95-(p[0]*.70+p[1]*.70)*.42)
    light=(-.45,-.35,.82);l=math.sqrt(_dot(light,light));light=tuple(x/l for x in light)
    view=(-.55,-.55,.62)
    faces=[]
    for pts,colour,_ in tris:
        n=_normal(*pts)
        if _dot(n,view)<-.05:continue          # back faces (closed meshes)
        depth=sum(p[0]+p[1]-p[2]*.3 for p in pts)/3
        faces.append((depth,[proj(p) for p in pts],colour,n))
    if not faces:return Image.new('RGBA',(size,size),background)
    xs=[q[0] for f in faces for q in f[1]];ys=[q[1] for f in faces for q in f[1]]
    k=size*(1-2*margin)/max(max(xs)-min(xs),max(ys)-min(ys),1e-6)
    cx,cy=(max(xs)+min(xs))/2,(max(ys)+min(ys))/2
    scale=2;big=Image.new('RGBA',(size*scale,size*scale),background)
    from PIL import ImageDraw
    d=ImageDraw.Draw(big)
    for depth,pts,colour,n in sorted(faces,key=lambda f:-f[0]):
        base_c=(87,152,186) if colour==TEAM else colour
        shade=.55+.55*max(0,_dot(n,light))
        c=tuple(min(255,int(v*shade)) for v in base_c)
        d.polygon([((x-cx)*k*scale+size*scale/2,(y-cy)*k*scale+size*scale/2) for x,y in pts],fill=(*c,255))
    return big.resize((size,size),Image.Resampling.LANCZOS)
