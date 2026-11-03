"""MDX with several bones, rotation tracks, per-layer materials and geoset alpha.

gltf_import.mdx emits one Root bone and opaque palette geosets. Animated
presentation (ship condition, sinking, turret recoil, propellers, falls) needs
child bones with their own translation/rotation/scale keys and translucent
smoke/fire/steam layers. Everything here still draws from the shared palette
atlas (gltf_import.palette_uv) plus the replaceable team colour.
"""
import math

from tools.frontline import gltf_import as gi

P=gi.P;S=gi.S;CH=gi.CH
TEAM=gi.TEAM
# Materials: 0 lit palette, 1 team colour, 2 alpha-blended palette (smoke, steam, oil),
# 3 additive palette (fire, muzzle flash).
OPAQUE,TEAMCOL,BLEND,ADD=0,1,2,3
MATERIALS=[(0,0x10,0),(0,0x10,1),(2,0x10|0x1,0),(3,0x10|0x1,0)]   # (filter mode, shading flags, texture)

def quat_axis(axis,degrees):
    """Quaternion (x,y,z,w) for a rotation about 'x', 'y' or 'z'."""
    h=math.radians(degrees)/2;s=math.sin(h)
    return {'x':(s,0,0,math.cos(h)),'y':(0,s,0,math.cos(h)),'z':(0,0,s,math.cos(h))}[axis]

def quat_mul(a,b):
    ax,ay,az,aw=a;bx,by,bz,bw=b
    return (aw*bx+ax*bw+ay*bz-az*by,aw*by-ax*bz+ay*bw+az*bx,aw*bz+ax*by-ay*bx+az*bw,aw*bw-ax*bx-ay*by-az*bz)

def euler(roll=0,pitch=0,yaw=0):
    """Roll about +X (bow axis), pitch about +Y (positive lowers the bow), yaw about +Z."""
    return quat_mul(quat_axis('z',yaw),quat_mul(quat_axis('y',pitch),quat_axis('x',roll)))

class Bone:
    def __init__(self,name,parent=-1,pivot=(0,0,0)):
        self.name=name;self.parent=parent;self.pivot=pivot
        self.translation=[];self.rotation=[];self.scale=[]

class Layer:
    def __init__(self,tris,material=OPAQUE,bone=0,alpha=None):
        self.tris=tris;self.material=material;self.bone=bone;self.alpha=alpha

def _sample(keys,t):
    """Piecewise-linear value of sorted keys [(time, *values)] at time t (clamped)."""
    if t<=keys[0][0]:return keys[0][1:]
    if t>=keys[-1][0]:return keys[-1][1:]
    for k0,k1 in zip(keys,keys[1:]):
        if k0[0]<=t<=k1[0]:
            f=(t-k0[0])/max(1,k1[0]-k0[0])
            return tuple(a+(b-a)*f for a,b in zip(k0[1:],k1[1:]))

def densify(keys,windows):
    """WC3 evaluates a track only inside the playing sequence and falls back to the static
    value when that sequence has no keys, so pin every track at each sequence's ends: with the
    value the global key list implies there when the sequence has keys, else the rest pose."""
    if not keys:return keys
    keys=sorted({k[0]:k for k in keys}.values())
    out={k[0]:k for k in keys}
    rest=keys[0][1:]
    for a,b in windows:
        # A sequence with no keys of its own holds the rest pose (the first key). Interpolating
        # across it from its neighbours slid yards and structures toward their Death/Decay sink
        # while they were being built or working.
        keyed=any(a<=k[0]<=b for k in keys)
        for t in (a,b):
            if t not in out:out[t]=(t,*(_sample(keys,t) if keyed else rest))
    out=sorted(out.values())
    if len(out[0])==5:   # quaternion: renormalise interpolated keys
        out=[(k[0],*(v/max(1e-9,math.sqrt(sum(c*c for c in k[1:]))) for v in k[1:])) for k in out]
    return out

def _track(tag,keys,width):
    if not keys:return b''
    keys=sorted(keys,key=lambda k:k[0])
    return tag+P('3I',len(keys),1,0xffffffff)+b''.join(P('I'+str(width)+'f',k[0],*k[1:]) for k in keys)

def _geoset(name,tris,material,bone,bnd,smooth):
    limit=math.cos(math.radians(smooth))
    fn=[gi._normal(*t[0]) for t in tris]
    acc={}
    for (pts,colour,_),n in zip(tris,fn):
        for p in pts:acc.setdefault((tuple(round(c,3) for c in p),colour),[]).append(n)
    verts=[];normals=[];uv=[];indices=[];table={}
    for (pts,colour,_),n in zip(tris,fn):
        coords=(.5,.5) if colour==TEAM else gi.palette_uv(colour)
        for p in pts:
            k=(tuple(round(c,3) for c in p),colour)
            sm=[x for x in acc[k] if gi._dot(x,n)>=limit]
            s=[sum(x[i] for x in sm) for i in range(3)];l=math.sqrt(gi._dot(s,s)) or 1
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
    geo+=sub('GNDX',n,bytes(n))+sub('MTGC',1,P('I',1))+sub('UVAS',1,b'')+sub('MATS',1,P('4I',bone,material,0,0)+bnd+P('I',0))
    return P('I',len(geo)+4)+geo

def emit(name,layers,bones,sequences,smooth=35,camera_scale=2.8):
    """sequences: [(name, start, end, move_speed, non_looping)]. Bone 0 is the root;
    every vertex binds to its layer's bone, and a layer's geometry is given relative
    to that bone's pivot. Empty layers are skipped."""
    # A detailed hull can exceed uint16 vertex addressing. Split geometry while
    # retaining each layer's material, bone and alpha across every sequence.
    layers=[Layer(l.tris[i:i+9000],l.material,l.bone,l.alpha)
            for l in layers for i in range(0,len(l.tris),9000)]
    # Layers are authored relative to their bone's pivot; MDX vertices live in model space.
    for l in layers:
        px,py,pz=bones[l.bone].pivot
        if (px,py,pz)!=(0,0,0):l.tris=gi.transform(l.tris,1,(px,py,pz))
    lo,hi=gi.bounds([t for l in layers for t in l.tris])
    extent=max(abs(v) for v in lo+hi);top=hi[2]
    radius=math.sqrt(sum(max(abs(a),abs(b))**2 for a,b in zip(lo,hi)))
    bnd=P('7f',radius,*lo,*hi)
    seq=b''.join(S(n,80)+P('2IfIfI',a,b,speed,int(once),0,0)+bnd for n,a,b,speed,once in sequences)
    spans=[(a,b) for n,a,b,speed,once in sequences]
    textures=P('I',0)+S(gi.PALETTE_TEXTURE,260)+P('I',0)+P('I',1)+S('',260)+P('I',0)
    materials=b''
    for filt,shading,texture in MATERIALS:
        m=P('2I',0,0)+b'LAYS'+P('I',1)+P('I5If',28,filt,shading,texture,0xffffffff,0,1)
        materials+=P('I',len(m)+4)+m
    geosets=b'';alphas=b''
    for gid,layer in enumerate(layers):
        geosets+=_geoset(name,layer.tris,layer.material,layer.bone,bnd,smooth)
        if layer.alpha:
            keys=densify([tuple(k) for k in layer.alpha],spans)
            kg=b'KGAO'+P('3I',len(keys),1,0xffffffff)+b''.join(P('If',*k) for k in keys)
            alphas+=P('IfI3fI',28+len(kg),1,0,1,1,1,gid)+kg
    nodes=b''
    for oid,bone in enumerate(bones):
        tracks=(_track(b'KGTR',densify(bone.translation,spans),3)+_track(b'KGRT',densify(bone.rotation,spans),4)+
                _track(b'KGSC',densify(bone.scale,spans),3))
        nodes+=P('I',96+len(tracks))+S(bone.name,80)+P('3I',oid,bone.parent&0xffffffff,256)+tracks+P('2I',0,0xffffffff)
    pivots=b''.join(P('3f',*b.pivot) for b in bones)
    distance=max(160,extent*camera_scale)
    camera=P('I',120)+S('Portrait',80)+P('3f3f3f',distance,-distance,extent*.9,.55,4000,1,0,0,top*.45)
    return (b'MDLX'+CH('VERS',P('I',800))+CH('MODL',S('Frontline '+name,80)+S('',260)+bnd+P('I',100))+CH('SEQS',seq)+
            CH('TEXS',textures)+CH('MTLS',materials)+CH('GEOS',geosets)+CH('BONE',nodes)+CH('PIVT',pivots)+CH('CAMS',camera)+
            (CH('GEOA',alphas) if alphas else b''))

def visible_in(windows,total_end,on=1.0,fade=0):
    """Geoset alpha keys: `on` inside each (start, end) window, 0 elsewhere (optional fade-in ms)."""
    keys={0:0.0,total_end:0.0}
    for a,b in windows:
        if a>0:keys[a-1]=keys.get(a-1,0.0)
        keys[a]=0.0 if fade else on
        if fade:keys[a+fade]=on
        keys[b]=on
        keys[b+1]=0.0
    return sorted(keys.items())
