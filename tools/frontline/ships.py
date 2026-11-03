"""Smooth-shaded warships from the historical box layouts (historical_models.py).

The stacked-box hull is replaced by a lofted surface through the same station
curve (hull_width, sheer, deck height) with flared, raked bow, bilge and keel,
boot topping and a planked deck. Parts tagged with shape codes become
cylinders (funnels, barbettes, masts, AA tubs), barrels, or chamfered houses;
every other box gets bevelled edges. Original MIT geometry, no downloaded mesh.
"""
import math
import random

from tools.frontline import gltf_import as gi
from tools.frontline import historical_models as hm

TEAM=gi.TEAM

def cell_rgb(cell):
    from tools.frontline.generate import NAVAL_CELLS
    cell%=100
    return TEAM if cell==hm.TEAM else NAVAL_CELLS[cell][:3]

def quad(a,b,c,d,colour,tag='s'):
    return [((a,b,c),colour,tag),((a,c,d),colour,tag)]

def bevel_box(x,y,z,w,d,h,colour,r):
    """Box with its four vertical edges and top edges chamfered by r."""
    r=min(r,w*.45,d*.45,h*.45)
    if r<=.05:return gi.boxes([(x,y,z,w,d,h,colour)])
    # Octagonal footprint, chamfered top ring.
    def ring(zz,inset):
        ww,dd=w-inset,d-inset;c=r
        return [(x+ww-c,y-dd,zz),(x+ww,y-dd+c,zz),(x+ww,y+dd-c,zz),(x+ww-c,y+dd,zz),
                (x-ww+c,y+dd,zz),(x-ww,y+dd-c,zz),(x-ww,y-dd+c,zz),(x-ww+c,y-dd,zz)]
    bottom,mid,top=ring(z,0),ring(z+h-r,0),ring(z+h,r)
    tris=[]
    for lower,upper in ((bottom,mid),(mid,top)):
        for i in range(8):
            j=(i+1)%8
            tris+=quad(lower[i],lower[j],upper[j],upper[i],colour)
    cz=(x,y,z+h)
    tris+=[((cz,top[i],top[(i+1)%8]),colour,'s') for i in range(8)]
    cb=(x,y,z)
    tris+=[((cb,bottom[(i+1)%8],bottom[i]),colour,'s') for i in range(8)]
    return tris

def cylinder(x,y,z,rx,ry,h,colour,segments=12,taper=1.0,axis='z'):
    """Elliptic cylinder: vertical (x,y footprint radii) or along the y axis (barrel)."""
    tris=[]
    pts=[(math.cos(i*math.tau/segments),math.sin(i*math.tau/segments)) for i in range(segments)]
    if axis=='z':
        lo=[(x+rx*c,y+ry*s,z) for c,s in pts];hi=[(x+rx*taper*c,y+ry*taper*s,z+h) for c,s in pts]
        top=(x,y,z+h);base=(x,y,z)
    else:  # along y from y-ry to y+ry, radius rx, centred at height z
        lo=[(x+rx*c,y+ry,z+rx*s) for c,s in pts];hi=[(x+rx*taper*c,y-ry,z+rx*taper*s) for c,s in pts]
        top=(x,y-ry,z);base=(x,y+ry,z)
    for i in range(segments):
        j=(i+1)%segments
        tris+=quad(lo[i],lo[j],hi[j],hi[i],colour)
        tris.append(((top,hi[i],hi[j]),colour,'s'))
        tris.append(((base,lo[j],lo[i]),colour,'s'))
    return tris

def part(box):
    x,y,z,w,d,h,code=box
    shape,colour=code//100*100,cell_rgb(code)
    if shape==hm.CYL:
        if max(w,d)<1:return gi.boxes([(x,y,z,w,d,h,colour)])
        return cylinder(x,y,z,w,d,h,colour,5 if max(w,d)<3.2 else 14)
    if shape==hm.BARREL:
        r=max(.18,min(w,h*.5))
        if r<.5:return gi.boxes([(x,y,z,w,d,h,colour)])
        return cylinder(x,y,z+h*.5,r,d,0,colour,6,taper=.85,axis='y')
    if shape==hm.ROUND and min(w,d,h)>=1:
        return bevel_box(x,y,z,w,d,h,colour,min(w,d,h)*.32)
    if min(w,d,h)<1.5:return gi.boxes([(x,y,z,w,d,h,colour)])   # small fittings stay crisp boxes
    return bevel_box(x,y,z,w,d,h,colour,min(w,d,h)*.18)

def hull(length,beam,pal,sheer,deck,shape,stations=44):
    """Lofted hull: bow at -Y, +X port (authoring frame), waterline at z=0."""
    lower=pal.get('lower',pal['hull'])
    def zd(t):return deck+sheer*max(0,(.4-t)/.4)**1.6
    sections=[]
    for i in range(stations+1):
        t=i/stations
        # Ease the sampling toward the bow and stern where curvature lives.
        t=.5-.5*math.cos(math.pi*t)
        blunt=shape.get('bow',.32)<.2                    # landing craft: square ramp bow, flat bottom
        w=hm.hull_width(t,beam,**shape)*(1 if blunt else min(1,t/.025))
        bow=0 if blunt else max(0,1-t/.09)
        flare=1+.08*max(0,1-t/.25)
        top=zd(t);k=min(1,deck/12)                         # shallow hulls draw less water
        profile=[(w*flare,top),(w*(1+.04*bow),top*.55),(w,0),(w*.97,-2.2*k),(w*.84,-4.6*k),(w*.52,-6.4*k),(0,-7*k)]
        if blunt:profile=[(w,top),(w,top*.5),(w,0),(w*.96,-2.5*k),(w*.8,-4*k),(0,-4.2*k)]
        # Raked stem: upper stations lean forward at the bow; cutaway forefoot below.
        y=-length+2*length*t
        sec=[(px,y-bow*7*(pz+7)/(top+7)+bow*3*max(0,-pz)/7,pz) for px,pz in profile]
        sections.append(sec)
    tris=[]
    def colour(z0,z1):
        zm=(z0+z1)/2
        return cell_rgb(hm.BOOT) if -1.6<zm<1.0 else cell_rgb(pal['hull'] if zm>=1 else lower)
    for a,b in zip(sections,sections[1:]):
        for k in range(len(a)-1):
            # Port side (+X) and mirrored starboard side.
            for side in (1,-1):
                p0=(side*a[k][0],a[k][1],a[k][2]);p1=(side*a[k+1][0],a[k+1][1],a[k+1][2])
                q0=(side*b[k][0],b[k][1],b[k][2]);q1=(side*b[k+1][0],b[k+1][1],b[k+1][2])
                c=colour(a[k][2],a[k+1][2])
                tris+=quad(p0,p1,q1,q0,c) if side>0 else quad(p0,q0,q1,p1,c)
        # Weather deck: six strakes in alternating tones read as planking at RTS zoom.
        dc=cell_rgb(pal['deck']);n=0 if shape.get('bow',.32)<.2 else 6   # open boats: the well box is the floor
        for k in range(n):
            u0,u1=1-2*k/n,1-2*(k+1)/n
            tone=tuple(min(255,int(v*(1.05 if k%2 else .95))) for v in dc)
            tris+=quad((a[0][0]*u0,a[0][1],a[0][2]),(b[0][0]*u0,b[0][1],b[0][2]),(b[0][0]*u1,b[0][1],b[0][2]),(a[0][0]*u1,a[0][1],a[0][2]),tone,'deck')
    # Transom.
    last=sections[-1];c=cell_rgb(pal['hull'])
    ring=[(p[0],p[1],p[2]) for p in last]+[(-p[0],p[1],p[2]) for p in reversed(last[:-1])]
    centre=(0,last[0][1],sum(p[2] for p in last)/len(last))
    tris+=[((centre,ring[i],ring[(i+1)%len(ring)]),c,'s') for i in range(len(ring))]
    return tris

def triangles(name):
    """Engine-space triangles (bow toward +X) of a historical ship or turret."""
    if name in ('yamato','yamato_turret','yamato_turret_aa'):
        from tools.frontline import yamato
        return yamato.triangles() if name=='yamato' else yamato.world(yamato.turret_m(name=='yamato_turret_aa'))
    boxes=hm.GEOMETRY[name]
    tris=[]
    if name in hm.SHIPS:
        index=hm.SHIPS.index(name)
        length,beam,pal,sheer,deck,shape,count=hm.HULL_LOG[index]
        tris+=hull(length,beam,pal,sheer,deck,shape)
        boxes=boxes[count:]
    for box in boxes:tris+=part(box)
    return [(tuple((-y,x,z) for x,y,z in pts),colour,tag) for pts,colour,tag in tris]

TWIN_BATTERIES=('nagato','kongo')   # twin main turrets; every other battleship mounts triples

def battery_model(name,index=0):
    if name=='yamato':return 'yamato_turret_aa' if index else 'yamato_turret'
    return 'naval_twin' if name in TWIN_BATTERIES else 'naval_triple'

def complete(name):
    """Assembled hull and per-mount art, including the aft rest bearing."""
    from tools.frontline import models
    tris=triangles(name)
    for i,offset in enumerate(models.BATTERIES.get(name,())):
        tris+=gi.transform(triangles(battery_model(name,i)),1,offset,yaw=180 if offset[0]<0 else 0)
    return tris

def wake(tris):
    """Walk-only foam: stern wake and bow waves as flat white patches (engine frame)."""
    lo,hi=gi.bounds(tris)
    length=hi[0];beam=max(abs(lo[1]),hi[1])
    white=(232,238,236);rng=random.Random(int(length*10))
    foam=[]
    for i in range(6):
        for s in (-1,1):
            x=lo[0]-10-i*14;y=s*(beam*.45+i*3.5)
            foam+=gi.boxes([(x,y,.4,8+i*1.5,2.4+i*.3,.6,white)])
    for i in range(4):
        for s in (-1,1):
            foam+=gi.boxes([(length-8-i*10,s*(beam*.5+i*3.6),.5,6,1.4,.8,white)])
    return foam

# Generic roster ships (AI-built, both sides) reuse a smooth class at their own size;
# the battleship carries its main turrets in-model since it has no attached batteries.
GENERIC={'battleship':('iowa',True),'destroyer':('fletcher',False),'cruiser':('cleveland',False),
         'carrier':('essex',False),'landingcraft':('lcvp',False),'transport':('lcm',False)}

def generic(name):
    from tools.frontline import models
    source,batteries=GENERIC[name]
    tris=triangles(source)
    if batteries:
        mount=triangles(battery_model(source))
        for sx,sy,sz in models.BATTERIES[source]:tris+=gi.transform(mount,1,(sx,sy,sz))
    box=models.GEOMETRY[name]
    want=max(b[0]+b[3] for b in box)-min(b[0]-b[3] for b in box)
    lo,hi=gi.bounds(tris)
    return gi.transform(tris,want/(hi[0]-lo[0]))
