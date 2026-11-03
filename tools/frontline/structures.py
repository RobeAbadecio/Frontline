"""WWII Pacific defence structures, AA guns and AA-upgrade variants (original procedural art).

Every model faces -Y like the other Frontline buildings (Warcraft's default 270 degree
building facing) and is authored at the RTS scale of the existing art (a rifleman is
~72 units tall, a bunker ~130 wide). Geometry comes from a few convex primitives
(lofts, tubes, sandbags, bevelled boxes) coloured from the shared palette atlas plus
the replaceable team colour, and is emitted through rich_mdx with the eight unit
sequences of unit_anim.UNIT_SEQ:
  Attack     muzzle flash on every barrel (several shots for automatic weapons),
             barrel recoil, gun smoke on the heavy guns
  Death      the structure sinks/collapses inside an explosion and smoke column
  Stand...   radar arrays sweep, airfield beacons turn; searchlights light their beam
             in Attack and Work
Names follow the RTS roster (NAMED); EXTRAS are further structures for later use.

AA upgrade: one model, aa_mount (compact sandbagged twin Bofors), origin at the base of
its sandbags, attached by the game at (0, Y, Z) from catalog.AA_MOUNT {model: (Y, Z)}
(mirrored here as AA_MOUNT_CONTRACT). surface() reports the roof height under a spot.
The airfield carries a team-colour flag and roof bands, so a neutral (Player 15) airfield
reads grey and a captured one shows its owner; airfield_neutral is an optional swap.
"""
import math
import random

from tools.frontline import gltf_import as gi
from tools.frontline import rich_mdx as rm
from tools.frontline import ships
from tools.frontline import unit_anim as ua

TEAM=gi.TEAM
# ---------------------------------------------------------------- palette (sRGB)
CONCRETE=(152,148,136);CONCRETE_DK=(116,113,104);CONCRETE_LT=(176,172,160)
SAND=(184,164,120);SAND_DK=(160,140,100);SAND_LT=(198,180,138)
EARTH=(110,94,68);EARTH_DK=(88,74,54);CORAL=(196,186,158)
OD=(88,96,60);OD_DK=(66,72,46)                       # US olive drab
NAVY_GREY=(112,118,120);NAVY_DK=(84,90,92)           # IJN / USN naval guns
IJA=(104,98,64)                                      # Japanese army khaki-green
STEEL=(62,64,66);STEEL_LT=(92,94,96);BLACK=(24,24,22)
WOOD=(116,84,52);WOOD_DK=(86,62,40);LOG=(104,82,58);LOG_END=(150,124,88)
CANVAS=(118,112,78);GLASS=(118,150,162);WHITE=(226,224,214);RED=(150,44,36)
BRASS=(176,140,64);LENS=(250,246,222);SILVER=(168,170,166)
FLASH=(255,214,120);FLASH_CORE=(255,244,190);SMOKE=(160,158,150);BEAM=(255,246,206)

# ---------------------------------------------------------------- primitives
def _orient(tris,centre):
    """Flip faces of a convex part so they point away from its centre."""
    out=[]
    for (a,b,c),col,tag in tris:
        n=gi._cross(gi._sub(b,a),gi._sub(c,a))
        m=gi._sub(((a[0]+b[0]+c[0])/3,(a[1]+b[1]+c[1])/3,(a[2]+b[2]+c[2])/3),centre)
        out.append(((a,c,b) if gi._dot(n,m)<0 else (a,b,c),col,tag))
    return out

def loft(rings,colour,caps=(True,True),skip=()):
    """Convex solid through rings of equal point count (sides i->i+1, fan caps).
    `skip` drops side strips by index (hidden bottoms)."""
    pts=[p for r in rings for p in r];n=len(rings[0])
    centre=tuple(sum(p[i] for p in pts)/len(pts) for i in range(3))
    tris=[]
    for r0,r1 in zip(rings,rings[1:]):
        for i in range(n):
            if i in skip:continue
            j=(i+1)%n
            tris+=[((r0[i],r0[j],r1[j]),colour,'s'),((r0[i],r1[j],r1[i]),colour,'s')]
    for ring,on in ((rings[0],caps[0]),(rings[-1],caps[1])):
        if not on:continue
        c=tuple(sum(p[i] for p in ring)/n for i in range(3))
        tris+=[((c,ring[i],ring[(i+1)%n]),colour,'s') for i in range(n)]
    return _orient(tris,centre)

def _norm(v):
    l=math.sqrt(gi._dot(v,v)) or 1
    return (v[0]/l,v[1]/l,v[2]/l)
def _add(*vs):return tuple(sum(v[i] for v in vs) for i in range(3))
def _mul(v,k):return (v[0]*k,v[1]*k,v[2]*k)

def tube(p0,p1,r,colour,seg=8,r1=None,caps=True,phase=0.0):
    """Cylinder/cone between two points (barrels, struts, logs, pipes)."""
    d=_norm(gi._sub(p1,p0))
    a=(0,0,1) if abs(d[2])<.9 else (1,0,0)
    u=_norm(gi._cross(d,a));v=gi._cross(d,u)
    r1=r if r1 is None else r1
    def ring(p,rr):
        return [_add(p,_mul(u,math.cos(phase+k*math.tau/seg)*rr),_mul(v,math.sin(phase+k*math.tau/seg)*rr)) for k in range(seg)]
    return loft([ring(p0,r),ring(p1,r1)],colour,(caps,caps))

def cyl(x,y,z,r,h,colour,seg=12,r1=None,caps=True):
    return tube((x,y,z),(x,y,z+h),r,colour,seg,r1,caps,phase=math.pi/seg)

def box(x,y,z,w,d,h,colour,bevel=.15):
    """Half-extents w,d; height h from z. Bevelled unless tiny."""
    if bevel and min(w,d,h)>=2.5:return ships.bevel_box(x,y,z,w,d,h,colour,min(w,d,h)*bevel)
    return gi.boxes([(x,y,z,w,d,h,colour)])

def obox(x,y,z,w,d,h,yaw,colour,bevel=.15):
    return gi.transform(box(0,0,0,w,d,h,colour,bevel),1,(x,y,z),yaw)

def frustum(x,y,z,w0,d0,w1,d1,h,colour,dy=0,skip_bottom=True):
    """Rectangular frustum: base half-extents w0,d0, top w1,d1 (top shifted by dy)."""
    b=[(x-w0,y-d0,z),(x+w0,y-d0,z),(x+w0,y+d0,z),(x-w0,y+d0,z)]
    t=[(x-w1,y+dy-d1,z+h),(x+w1,y+dy-d1,z+h),(x+w1,y+dy+d1,z+h),(x-w1,y+dy+d1,z+h)]
    return loft([b,t],colour,(not skip_bottom,True))

def polygon_prism(x,y,z,r0,r1,h,sides,colour,phase=0.0):
    ring=lambda rr,zz:[(x+rr*math.cos(phase+k*math.tau/sides),y+rr*math.sin(phase+k*math.tau/sides),zz) for k in range(sides)]
    return loft([ring(r0,z),ring(r1,z+h)],colour,(False,True))

def bag(x,y,z,yaw,length=11,width=6,height=4.5,colour=SAND):
    """One filled sandbag: rounded section, pinched tied ends (no hidden bottom)."""
    sec=[(-width*.85,0),(width*.85,0),(width,height*.45),(width*.65,height),(-width*.65,height),(-width,height*.45)]
    def ring(s,k):
        return [(s,a*k,height*.45+(b-height*.45)*k) for a,b in sec]
    rings=[ring(-length,.55),ring(-length*.72,1),ring(length*.72,1),ring(length,.55)]
    tris=loft(rings,colour,skip=(0,))
    return gi.transform(tris,1,(x,y,z),yaw)

_BAG_SHADES=(SAND,SAND_DK,SAND_LT,(174,154,112))
def _shade(rng):return rng.choice(_BAG_SHADES)

def bag_ring(cx,cy,z,radius,courses=3,gap=None,bag_len=11,width=6,height=4.5,seed=0):
    """Circular sandbag wall; `gap`=(centre degrees, width degrees) leaves an entrance."""
    rng=random.Random(seed);tris=[]
    n=max(5,int(round(math.tau*radius/(bag_len*2.05))))
    for c in range(courses):
        r=radius-c*1.2
        for k in range(n):
            ang=(k+.5*(c%2))*360/n
            if gap and abs((ang-gap[0]+180)%360-180)<gap[1]/2:continue
            a=math.radians(ang)
            tris+=bag(cx+r*math.cos(a),cy+r*math.sin(a),z+c*height*.92,ang+90,bag_len,width,height,_shade(rng))
    return tris

def bag_wall(x0,y0,x1,y1,z=0,courses=3,bag_len=11,width=6,height=4.5,seed=0):
    rng=random.Random(seed);tris=[]
    length=math.hypot(x1-x0,y1-y0);yaw=math.degrees(math.atan2(y1-y0,x1-x0))
    n=max(1,int(round(length/(bag_len*2.05))))
    for c in range(courses):
        for k in range(n-(c%2)):
            f=(k+.5+.5*(c%2))/n
            tris+=bag(x0+(x1-x0)*f,y0+(y1-y0)*f,z+c*height*.92,yaw,bag_len,width,height,_shade(rng))
    return tris

def flag(x,y,z,height=46,width=18,yaw=0):
    """Pole + team-colour flag: every structure's readable owner marker."""
    pole=cyl(0,0,0,1.1,height,STEEL,6)+cyl(0,0,height,1.8,1.6,BRASS,6)
    cloth=gi.boxes([(width/2+1.2,0,height-14,width/2,.5,13,TEAM)])
    return gi.transform(pole+cloth,1,(x,y,z),yaw)

def crate(x,y,z,w=7,d=5,h=5,yaw=0,colour=WOOD):
    return obox(x,y,z,w,d,h,yaw,colour,.12)+obox(x,y,z+h*.42,w*1.02,d*1.02,h*.16,yaw,WOOD_DK,0)

def drum(x,y,z,colour=OD,r=4.5,h=13,lying=False,yaw=0):
    if lying:
        a=math.radians(yaw);d=(math.cos(a)*h/2,math.sin(a)*h/2,0)
        return tube((x-d[0],y-d[1],z+r),(x+d[0],y+d[1],z+r),r,colour,8)
    return cyl(x,y,z,r,h,colour,8)+cyl(x,y,z+h*.33,r*1.04,.8,STEEL,8,caps=False)+cyl(x,y,z+h*.66,r*1.04,.8,STEEL,8,caps=False)

def disc(x,y,z,r,colour,seg=16):
    c=(x,y,z);ring=[(x+r*math.cos(k*math.tau/seg),y+r*math.sin(k*math.tau/seg),z) for k in range(seg)]
    return [((c,ring[k],ring[(k+1)%seg]),colour,'s') for k in range(seg)]

def wheel(x,y,z,r,w,colour=STEEL):
    return tube((x-w,y,z),(x+w,y,z),r,(40,40,38),10)+tube((x-w*1.05,y,z),(x+w*1.05,y,z),r*.5,colour,8)

def place(tris,x=0,y=0,z=0,yaw=0,scale=1):return gi.transform(tris,scale,(x,y,z),yaw)

# ---------------------------------------------------------------- spec
class Gun:
    """Recoiling barrel group with its muzzles. `shots` are ms offsets within Attack."""
    def __init__(self,tris,direction,recoil,muzzles,shots=(0,),smoke=False):
        self.tris=tris;self.direction=direction;self.recoil=recoil
        self.muzzles=muzzles;self.shots=tuple(shots);self.smoke=smoke

class Spec:
    def __init__(self,body=None):
        self.body=list(body or []);self.guns=[];self.spin=[];self.beam=[]
    def gun(self,g):self.guns.append(g);return self
    def triangles(self):
        return self.body+[t for g in self.guns for t in g.tris]+[t for tris,pivot,_ in self.spin for t in gi.transform(tris,1,pivot)]

def aim(elevation,yaw=0):
    """Unit barrel direction: trained toward -Y (rotated by yaw degrees), elevated."""
    e=math.radians(elevation);a=math.radians(-90+yaw)
    return (math.cos(e)*math.cos(a),math.cos(e)*math.sin(a),math.sin(e))
def up_of(d):
    """Unit vector perpendicular to the barrel in its vertical plane (top of the breech)."""
    h=math.hypot(d[0],d[1]) or 1
    return (-d[0]/h*d[2],-d[1]/h*d[2],h)

# ---------------------------------------------------------------- guns
def bofors_barrel(P,d,s,colour=OD):
    """40 mm L/60: barrel, recoil-spring casing, cone flash hider. Returns tris, tip."""
    tris=tube(_add(P,_mul(d,2*s)),_add(P,_mul(d,22*s)),2.3*s,colour,8)
    tris+=tube(_add(P,_mul(d,-4*s)),_add(P,_mul(d,48*s)),1.4*s,STEEL,7)
    tris+=tube(_add(P,_mul(d,47*s)),_add(P,_mul(d,54*s)),1.6*s,STEEL,8,r1=2.6*s)
    return tris,_add(P,_mul(d,55*s))

def bofors_breech(P,d,s,colour=OD):
    u=up_of(d)
    tris=tube(_add(P,_mul(d,-11*s)),_add(P,_mul(d,5*s)),4.2*s,colour,4,phase=math.pi/4)
    tris+=tube(_add(P,_mul(u,3.5*s),_mul(d,-6*s)),_add(P,_mul(u,12*s),_mul(d,-7*s)),2.6*s,STEEL_LT,4,phase=math.pi/4)  # clip guide
    tris+=tube(_add(P,_mul(u,12*s),_mul(d,-7*s)),_add(P,_mul(u,13.5*s),_mul(d,-7*s)),3.2*s,BRASS,4,phase=math.pi/4)  # 4-round clip
    return tris

def bofors(x,y,z,s=1,twin=False,colour=OD,elevation=38,outriggers=True,shield=False,stagger=0):
    """US 40 mm Bofors: M1 field carriage (single) or Mk 1 twin. Returns static tris, guns."""
    tris=[];T=z+27*s
    if outriggers:
        for a in (45,135,225,315):
            r=math.radians(a)
            tris+=obox(x+math.cos(r)*17*s,y+math.sin(r)*17*s,z+2*s,15*s,2.2*s,2.6*s,a,colour)
            tris+=cyl(x+math.cos(r)*32*s,y+math.sin(r)*32*s,z,3.4*s,2.2*s,STEEL,8)
        tris+=box(x,y,z+1*s,11*s,7*s,4*s,colour)                                   # carriage chassis
    tris+=cyl(x,y,z+4*s,12*s,3.5*s,colour,14)                                       # platform
    tris+=cyl(x,y,z+7.5*s,8*s,5*s,STEEL_LT,12)                                      # traversing ring
    half=(9 if twin else 6)*s
    tris+=box(x,y+2*s,z+12.5*s,half+3*s,8*s,8*s,colour)                             # upper carriage
    for side in (-1,1):
        tris+=box(x+side*(half+1.5*s),y,z+18*s,1.3*s,7*s,11*s,colour,.1)           # trunnion plates
        tris+=box(x+side*(half+7*s),y+5*s,z+17*s,3.5*s,3*s,1.2*s,STEEL,0)          # layer seats
        tris+=tube((x+side*(half+4*s),y-2*s,T-2*s),(x+side*(half+8*s),y-2*s,T-2*s),3*s,STEEL,8)  # handwheels
        tris+=box(x+side*(half+6*s),y-6*s,T+2*s,1.6*s,1.6*s,6*s,STEEL,0)           # reflector sights
    if shield:tris+=obox(x,y-11*s,z+16*s,half+9*s,.9*s,12*s,0,colour,0)
    d=aim(elevation);guns=[]
    barrels=(-7*s,7*s) if twin else (0,)
    for i,bx in enumerate(barrels):
        P=(x+bx,y,T)
        tris+=bofors_breech(P,d,s,colour)
        bt,tip=bofors_barrel(P,d,s,colour)
        shots=(0,500) if not twin else ((0,500) if i==0 else (250,750))
        guns.append(Gun(bt,d,5*s,[(tip,d,5.5*s)],tuple(t+stagger for t in shots)))
    return tris,guns

def oerlikon(x,y,z,s=1,colour=NAVY_GREY,elevation=32):
    """20 mm Oerlikon on a pedestal: shield, drum magazine, shoulder rests."""
    tris=[]
    for a in (90,210,330):
        r=math.radians(a)
        tris+=tube((x,y,z+10*s),(x+math.cos(r)*13*s,y+math.sin(r)*13*s,z),1.4*s,colour,5)
    tris+=cyl(x,y,z,4*s,24*s,colour,10)+cyl(x,y,z+22*s,5*s,3*s,STEEL_LT,10)
    P=(x,y,z+28*s);d=aim(elevation);u=up_of(d)
    tris+=obox(x,y-6*s,z+20*s,10*s,.7*s,12*s,0,colour,0)                         # shield
    tris+=obox(x,y-6.4*s,z+29*s,4*s,.7*s,3*s,0,colour,0)                          # shield top notch
    tris+=tube(_add(P,_mul(d,-9*s)),_add(P,_mul(d,6*s)),2.4*s,colour,6)          # receiver
    tris+=tube(_add(P,_mul(u,2*s)),_add(P,_mul(u,5.5*s)),6*s,STEEL,12)            # 60-round drum
    for side in (-1,1):
        p0=_add(P,(side*2.5*s,0,0),_mul(d,-7*s));p1=_add(p0,(side*4*s,0,0),_mul(d,-6*s),_mul(u,-7*s))
        tris+=tube(p0,p1,.9*s,STEEL,4)+box(p1[0],p1[1],p1[2]-1.5*s,2.4*s,1.4*s,3*s,STEEL,0)
    gun=tube(_add(P,_mul(d,2*s)),_add(P,_mul(d,13*s)),2*s,colour,7)
    gun+=tube(_add(P,_mul(d,6*s)),_add(P,_mul(d,38*s)),1*s,STEEL,6)
    gun+=tube(_add(P,_mul(d,37*s)),_add(P,_mul(d,42*s)),1.3*s,STEEL,6,r1=1.9*s)
    return tris,[Gun(gun,d,2*s,[(_add(P,_mul(d,43*s)),d,4*s)],(0,130,260,390,520,650,780))]

def type96(x,y,z,s=1,colour=NAVY_GREY,elevation=40,stagger=0):
    """IJN Type 96 25 mm triple: three barrels with big conical flash suppressors, box magazines."""
    tris=cyl(x,y,z,13*s,3*s,colour,14)+cyl(x,y,z+3*s,6.5*s,12*s,colour,12,r1=5*s)
    tris+=box(x,y+1*s,z+14*s,13*s,8*s,7*s,colour)                                # carriage
    for side in (-1,1):
        tris+=box(x+side*14.5*s,y,z+17*s,1.4*s,7*s,10*s,colour,.1)               # cradle side plates
        tris+=tube((x+side*15*s,y+6*s,z+16*s),(x+side*24*s,y+8*s,z+14*s),1*s,STEEL,4)  # seat arms
        tris+=box(x+side*25*s,y+8*s,z+12*s,3.5*s,3*s,1.2*s,STEEL,0)              # layer / trainer seats
        tris+=tube((x+side*20*s,y+1*s,z+21*s),(x+side*22*s,y+1*s,z+21*s),3.2*s,STEEL,8)  # handwheels
    tris+=box(x+16*s,y-5*s,z+28*s,1.2*s,1.2*s,4*s,STEEL,0)                         # ring sight post
    tris+=tube((x+16*s,y-5*s,z+33*s),(x+16*s,y-5.6*s,z+33*s),3*s,STEEL,10,caps=False)
    P0=(x,y,z+25*s);d=aim(elevation);u=up_of(d);guns=[]
    for i,bx in enumerate((-8*s,0,8*s)):
        P=_add(P0,(bx,0,0))
        tris+=tube(_add(P,_mul(d,-12*s)),_add(P,_mul(d,6*s)),3*s,colour,4,phase=math.pi/4)   # receiver
        tris+=tube(_add(P,_mul(u,2.5*s),_mul(d,-1*s)),_add(P,_mul(u,9*s),_mul(d,1*s)),2.2*s,STEEL_LT,4,phase=math.pi/4)  # 15-round magazine
        gun=tube(_add(P,_mul(d,4*s)),_add(P,_mul(d,40*s)),1.1*s,STEEL,6)
        gun+=tube(_add(P,_mul(d,36*s)),_add(P,_mul(d,44*s)),1.2*s,STEEL,8,r1=3.1*s)  # conical flash suppressor
        guns.append(Gun(gun,d,2.5*s,[(_add(P,_mul(d,45*s)),d,4.5*s)],tuple(t+stagger+i*70 for t in (0,220,440,660))))
    return tris,guns

def heavy_aa(x,y,z,s=1,colour=OD,legs=4,elevation=45,barrel=78,japanese=False):
    """US 90 mm M1 (cruciform, four legs) / Japanese Type 88 75 mm (five-legged pedestal)."""
    tris=[]
    for k in range(legs):
        a=(90 if legs==4 else -90)+k*360/legs+(45 if legs==4 else 0)
        r=math.radians(a);L=(46 if legs==4 else 40)*s
        tris+=obox(x+math.cos(r)*L/2,y+math.sin(r)*L/2,z+1.5*s,L/2,2.8*s,3.4*s,a,colour)
        tris+=cyl(x+math.cos(r)*L,y+math.sin(r)*L,z,4.5*s,2.5*s,STEEL,8)+cyl(x+math.cos(r)*L,y+math.sin(r)*L,z+2.5*s,1.3*s,5*s,STEEL,6)
    if japanese:tris+=cyl(x,y,z,11*s,22*s,colour,10,r1=6*s)                       # Type 88 pedestal
    else:
        tris+=cyl(x,y,z,16*s,6*s,colour,14)                                         # M1A1 mount platform
        tris+=box(x,y,z+6*s,13*s,15*s,6*s,colour)
        for side in (-1,1):tris+=wheel(x+side*17*s,y+14*s,z+7*s,7*s,2.4*s,colour)   # bogie wheels (raised)
    T=z+(31 if japanese else 30)*s
    tris+=box(x,y+3*s,T-12*s,11*s,11*s,9*s,colour)                                  # carriage / cradle base
    for side in (-1,1):
        tris+=box(x+side*10*s,y,T-8*s,1.6*s,9*s,13*s,colour,.1)                    # trunnion brackets
        tris+=box(x+side*16*s,y+7*s,T-9*s,3.5*s,3*s,1.2*s,STEEL,0)                 # layer seats
        tris+=tube((x+side*11*s,y-1*s,T-3*s),(x+side*15*s,y-1*s,T-3*s),3.4*s,STEEL,8)
    if not japanese:tris+=box(x-16*s,y-4*s,z+6*s,4*s,5*s,9*s,OD_DK)                  # fuze setter
    else:tris+=box(x+13*s,y-6*s,T-1*s,3*s,2*s,4*s,STEEL)+tube((x+13*s,y-6*s,T+4*s),(x+13*s,y-8*s,T+6*s),1.5*s,STEEL,6)
    d=aim(elevation);u=up_of(d);P=(x,y,T)
    tris+=tube(_add(P,_mul(d,-22*s)),_add(P,_mul(d,14*s)),6*s,colour,4,phase=math.pi/4)        # cradle / breech ring
    gun=tube(_add(P,_mul(d,6*s)),_add(P,_mul(d,barrel*s)),2.5*s,colour,8,r1=2.1*s)
    gun+=tube(_add(P,_mul(d,(barrel-4)*s)),_add(P,_mul(d,(barrel+1)*s)),2.8*s,STEEL,8)
    for side in ((-1,1) if not japanese else (0,)):
        off=_add(_mul(u,(-5 if not japanese else 5.5)*s),(side*2.6*s,0,0))
        gun+=tube(_add(P,off,_mul(d,-12*s)),_add(P,off,_mul(d,24*s)),2*s if not japanese else 2.6*s,colour,8)  # recuperator / recoil cylinders
    return tris,[Gun(gun,d,13*s,[(_add(P,_mul(d,(barrel+2)*s)),d,10*s)],(0,),smoke=True)]

def mg(x,y,z,s=1,colour=STEEL,elevation=3,yaw=0,japanese=False):
    """Browning M1919 (US) / Type 92 heavy MG (IJN, finned barrel) on a tripod."""
    tris=[];P=(x,y,z+11*s);d=aim(elevation,yaw)
    for a in (-90+yaw+150,-90+yaw-150,-90+yaw):
        r=math.radians(a);L=14*s if a!=-90+yaw else 11*s
        tris+=tube(P,(x+math.cos(r)*L,y+math.sin(r)*L,z),.8*s,colour,4)
    tris+=tube(_add(P,_mul(d,-9*s)),_add(P,_mul(d,4*s)),2.4*s,colour,4,phase=math.pi/4)
    tris+=box(x+3.5*s*math.cos(math.radians(yaw)),y+3.5*s*math.sin(math.radians(yaw)),z+9*s,2.5*s,2.5*s,3*s,OD_DK if not japanese else IJA,0)  # ammo box
    if japanese:
        gun=tube(_add(P,_mul(d,3*s)),_add(P,_mul(d,16*s)),2.2*s,colour,8)        # cooling fins
        for k in range(4):gun+=tube(_add(P,_mul(d,(4+k*3)*s)),_add(P,_mul(d,(4.8+k*3)*s)),2.9*s,colour,8,caps=False)
        gun+=tube(_add(P,_mul(d,15*s)),_add(P,_mul(d,26*s)),.8*s,BLACK,5)
        tip=_add(P,_mul(d,27*s))
    else:
        gun=tube(_add(P,_mul(d,3*s)),_add(P,_mul(d,19*s)),1.5*s,colour,7)        # perforated jacket
        gun+=tube(_add(P,_mul(d,18*s)),_add(P,_mul(d,23*s)),.7*s,BLACK,5)
        tip=_add(P,_mul(d,24*s))
    return tris,[Gun(gun,d,.8*s,[(tip,d,3.2*s)],(0,90,180,270,360,450,540,630,720,810))]

# ---------------------------------------------------------------- structures
def _pit(radius,courses=3,gap=(90,50),floor=EARTH,seed=0):
    return disc(0,0,.3,radius+6,floor,18)+bag_ring(0,0,.5,radius,courses,gap,seed=seed)

def _ammo_clips(x,y,n=3,colour=OD_DK,yaw=0):
    return sum((crate(x+(k-(n-1)/2)*9*math.cos(math.radians(yaw)),y+(k-(n-1)/2)*9*math.sin(math.radians(yaw)),.5,4,3,3.5,yaw,colour) for k in range(n)),[])

def aa_bofors():
    tris,guns=bofors(0,-2,1,1.0,False,OD)
    s=Spec(_pit(54,3,(90,46))+tris+_ammo_clips(-30,26,3,yaw=30)+_ammo_clips(30,26,2,yaw=-30)+flag(42,40,0))
    for g in guns:s.gun(g)
    return s

def aa_oerlikon():
    tris,guns=oerlikon(0,0,1,1.0,NAVY_GREY)
    s=Spec(_pit(32,3,(90,50),EARTH,2)+tris+_ammo_clips(-18,18,2,NAVY_DK,30)+flag(26,22,0,40,14))
    for g in guns:s.gun(g)
    return s

def aa_m1_90mm():
    tris,guns=heavy_aa(0,0,1,1.0,OD,4,45,78)
    rack=sum((tube((x,30,4+k*4.2),(x,40,4+k*4.2),1.8,BRASS,6) for x in (-44,-38,-32) for k in range(2)),[])
    body=_pit(62,3,(90,40),EARTH,3)+tris+box(-38,35,.5,10,8,3,WOOD,0)+rack+crate(38,34,.5,8,6,6,20)+crate(40,20,.5,6,5,5,-10)+flag(52,-30,0)
    s=Spec(body)
    for g in guns:s.gun(g)
    return s

def aa_type96():
    tris,guns=type96(0,0,1,1.0,NAVY_GREY)
    ring=polygon_prism(0,0,0,44,38,9,20,CONCRETE)                                  # concrete parapet...
    body=disc(0,0,.4,48,CORAL,18)+ring+bag_ring(0,0,9,50,2,(90,46),seed=4)
    body+=tris+_ammo_clips(-26,22,3,NAVY_DK,30)+flag(38,34,9)
    s=Spec(body)
    for g in guns:s.gun(g)
    return s

def aa_type88():
    tris,guns=heavy_aa(0,0,1,1.0,IJA,5,45,64,japanese=True)
    body=_pit(58,3,(90,44),EARTH,5)+tris+crate(-34,30,.5,8,5,5,30,WOOD)+crate(-36,30,10.5,7,4,4,32,WOOD)+crate(34,30,.5,8,5,5,-30,WOOD)+flag(46,-32,0)
    s=Spec(body)
    for g in guns:s.gun(g)
    return s

def searchlight():
    d=aim(28);P=(0,0,36);u=up_of(d)
    body=_pit(40,2,(90,60),EARTH,6)
    body+=box(0,4,6,16,22,5,OD)+sum((wheel(side*18,y,7,6.5,2.5) for side in (-1,1) for y in (-12,18)),[])
    body+=cyl(0,0,11,12,3,OD,14)
    for side in (-1,1):body+=box(side*14.5,0,13,1.8,4,24,OD,.1)                    # yoke arms
    body+=tube((-16,0,36),(16,0,36),2,STEEL,8)                                       # trunnion
    body+=tube(_add(P,_mul(d,-13)),_add(P,_mul(d,9)),13,OD,14,r1=13.5)              # 60-inch drum
    body+=tube(_add(P,_mul(d,-17)),_add(P,_mul(d,-13)),9,OD_DK,12)                  # lamp housing / vents
    body+=tube(_add(P,_mul(d,9)),_add(P,_mul(d,10)),12.2,LENS,14,caps=True)          # front glass
    body+=tube(_add(P,_mul(u,13)),_add(P,_mul(u,18)),3,OD_DK,6)                     # ventilator
    body+=box(32,-22,.5,9,7,10,OD_DK)+tube((24,-20,5),(10,-6,11),.8,BLACK,4)         # power unit + cable
    body+=flag(-34,26,0,40,14)
    s=Spec(body)
    a=_add(P,_mul(d,10));b=_add(P,_mul(d,520))
    s.beam=[t for t in tube(a,b,11.5,BEAM,14,r1=70,caps=False)]
    return s

def _lattice(x,y,z0,z1,half0,half1,colour,levels=4):
    tris=[];corner=lambda z,h:[(x-h,y-h,z),(x+h,y-h,z),(x+h,y+h,z),(x-h,y+h,z)]
    lo,hi=corner(z0,half0),corner(z1,half1)
    for a,b in zip(lo,hi):tris+=tube(a,b,1.1,colour,4)
    for k in range(1,levels+1):
        f=k/levels;z=z0+(z1-z0)*f;h=half0+(half1-half0)*f;c=corner(z,h)
        for i in range(4):tris+=tube(c[i],c[(i+1)%4],.6,colour,3)
        if k<levels:
            f2=(k+1)/levels;c2=corner(z0+(z1-z0)*f2,half0+(half1-half0)*f2)
            for i in range(4):tris+=tube(c[i],c2[(i+1)%4],.45,colour,3)
    return tris

def radar_usn():
    pad=box(0,0,0,70,58,6,EARTH_DK,0)                                                  # raised gravel platform
    body=[]
    # K-30 operations van and K-31 power trailer.
    body+=box(-38,24,9,14,24,20,OD)+box(-38,24,29,14.6,24.6,1.6,OD_DK,0)+box(-52.5,16,12,.6,6,6,GLASS,0)
    body+=box(-38,24,5,12,22,4,STEEL,0)+sum((wheel(side*13-38,y,6,5.5,2) for side in (-1,1) for y in (6,38)),[])
    body+=box(-38,-2,9,4,2.5,9,STEEL,0)+box(46,-32,7,10,12,12,OD)+sum((wheel(side*11+46,-32,5,4.5,1.8) for side in (-1,1)),[])
    body+=tube((36,-30,10),(30,10,1),.7,BLACK,4)+tube((-24,20,12),(10,20,1),.7,BLACK,4)
    body+=_lattice(22,24,0,72,14,6,STEEL_LT,4)+cyl(22,24,72,8,3,STEEL,12)          # antenna tower + turntable
    body+=flag(-38,40,30,26,12)
    # Rotating 'bedspring' dipole array on its own bone.
    body=pad+place(body,0,0,4.5)
    ax,ay,az=22,24,79.5
    arr=tube((0,0,0),(0,0,8),1.5,STEEL,6)+tube((0,0,8),(0,0,52),1,STEEL,4)
    for k in range(5):arr+=tube((-34,-3,10+k*10),(34,-3,10+k*10),.7,STEEL_LT,3)
    for k in range(9):arr+=tube((-32+k*8,-3,8),(-32+k*8,-3,52),.6,STEEL_LT,3)
    for k in range(8):
        for r in range(4):
            cx,cz=-28+k*8,15+r*10
            arr+=tube((cx-3.2,-6,cz),(cx+3.2,-6,cz),.5,WHITE,3,caps=False)              # dipoles
    arr+=tube((0,-3,52),(0,-3,58),.6,STEEL,3)
    s=Spec(body);s.spin.append((arr,(ax,ay,az),'sweep'))
    return s

def coastal_usn():
    """US 6-inch M1903 on a shielded barbette mount in a concrete emplacement."""
    body=cyl(0,0,0,62,8,CONCRETE,18)
    body+=disc(0,0,8.1,40,CONCRETE_LT,18)
    for k in range(9):                                                               # front parapet
        a=math.radians(-90+(k-4)*16)
        body+=obox(math.cos(a)*55,math.sin(a)*55,8,9,4,9,math.degrees(a)+90,CONCRETE_DK)
    body+=cyl(0,0,8,16,4,STEEL,14)+box(0,6,12,12,14,9,NAVY_GREY)
    shield=loft([[(-22,-14,12),(22,-14,12),(22,20,12),(-22,20,12)],[(-20,-4,36),(20,-4,36),(20,18,36),(-20,18,36)]],NAVY_GREY,(False,True))
    body+=shield+box(0,-14.5,24,4,.8,6,BLACK,0)
    d=aim(7);P=(0,-8,26)
    body+=tube(_add(P,_mul(d,-10)),_add(P,_mul(d,4)),5,NAVY_DK,8)
    gun=tube(_add(P,_mul(d,2)),_add(P,_mul(d,30)),4,NAVY_GREY,10,r1=3.4)+tube(_add(P,_mul(d,30)),_add(P,_mul(d,92)),3.4,NAVY_GREY,10,r1=2.8)
    gun+=tube(_add(P,_mul(d,90)),_add(P,_mul(d,94)),3.4,STEEL,10)
    body+=box(44,38,0,16,12,15,CONCRETE)+box(44,38,15,17,13,2.5,CONCRETE_DK,0)+box(44,25.4,2,6,1,10,BLACK,0)   # magazine
    body+=box(-44,36,0,14,14,4,EARTH_DK,0)+frustum(-44,36,4,14,14,9,9,12,EARTH)         # earth-covered shelter
    body+=sum((tube((x,26,3),(x,34,3),2.6,BRASS,6) for x in (-24,-18,-12)),[])+flag(56,-40,8)
    s=Spec(body)
    s.gun(Gun(gun,d,10,[(_add(P,_mul(d,96)),d,13)],(0,),smoke=True))
    return s

def coastal_ijn():
    """Vickers 8-inch twin turret on a concrete barbette (the Betio coast defence guns)."""
    body=cyl(0,0,0,60,12,CONCRETE,18)+disc(0,0,12.1,44,CONCRETE_LT,18)
    for k in range(10):                                                              # coconut-log revetment
        a=math.radians(30+k*12)
        body+=tube((math.cos(a)*64,math.sin(a)*64-6,4),(math.cos(a+.2)*64,math.sin(a+.2)*64-6,4),3.6,LOG,6)
    body+=cyl(0,0,12,30,5,NAVY_DK,16)
    oct_=lambda w,d,z,dy=0:[(x*w,y*d+dy,z) for x,y in ((-.6,-1),(.6,-1),(1,-.5),(1,.8),(.7,1),(-.7,1),(-1,.8),(-1,-.5))]
    body+=loft([oct_(30,30,17),oct_(28,30,32),oct_(22,22,40,6)],NAVY_GREY,(False,True))       # turret
    for side in (-1,1):body+=tube((side*28,8,33),(side*36,8,33),3.2,NAVY_DK,8)                # rangefinder ears
    body+=box(0,22,40,6,4,3,NAVY_DK,0)+box(-14,-29.5,24,3,.8,4,BLACK,0)+box(14,-29.5,24,3,.8,4,BLACK,0)
    d=aim(6);guns=[]
    for i,side in enumerate((-1,1)):
        P=(side*12,-26,26)
        body+=tube(_add(P,_mul(d,-2)),_add(P,_mul(d,6)),5,(70,66,58),8)                       # blast bags
        g=tube(_add(P,_mul(d,4)),_add(P,_mul(d,40)),3.6,NAVY_GREY,10,r1=3)+tube(_add(P,_mul(d,40)),_add(P,_mul(d,98)),3,NAVY_GREY,10,r1=2.6)
        g+=tube(_add(P,_mul(d,96)),_add(P,_mul(d,100)),3.1,STEEL,10)
        guns.append(Gun(g,d,10,[(_add(P,_mul(d,102)),d,13)],(i*180,),smoke=True))
    body+=box(-46,30,0,12,10,13,CONCRETE)+box(-46,30,13,13,11,2,CONCRETE_DK,0)+box(-46,19.4,2,5,1,9,BLACK,0)
    body+=flag(44,34,12)
    s=Spec(body)
    for g in guns:s.gun(g)
    return s

def pillbox_usn():
    body=disc(0,0,.3,44,EARTH,16)+polygon_prism(0,0,0,34,31,22,6,CONCRETE,math.pi/6)
    body+=polygon_prism(0,0,22,37,36,5,6,CONCRETE_DK,math.pi/6)
    for k,a in enumerate((-90,-150,-30)):                                              # embrasures
        r=math.radians(a);rr=31.5
        body+=obox(math.cos(r)*rr,math.sin(r)*rr,12,8 if k==0 else 6,1.4,4,a+90,BLACK,0)
    body+=box(0,33,0,10,4,18,CONCRETE)+box(0,29.8,2,5,1,14,(60,58,52),0)                  # rear entrance blast wall
    for k in range(3):body+=bag((k-1)*13,-31,27,0,7,4,3.5)                             # roof-edge sandbags
    body+=flag(26,20,27,30,14)
    tris,guns=mg(0,-24,8,1.0)
    s=Spec(body+tris)
    for g in guns:s.gun(g)
    return s

def pillbox_ijn():
    """Coconut-log and coral pillbox: log walls, log roof, heaped coral sand."""
    body=frustum(0,4,0,50,46,36,32,14,CORAL)+disc(0,0,.2,54,SAND_DK,16)
    logs=[]
    for k in range(4):
        z=14+k*5.2
        logs+=tube((-30,-26,z),(30,-26,z),2.8,LOG,6) if k!=1 else tube((-30,-26,z),(-9,-26,z),2.8,LOG,6)+tube((9,-26,z),(30,-26,z),2.8,LOG,6)
        logs+=tube((-30,24,z),(30,24,z),2.8,LOG,6)
        for side in (-1,1):logs+=tube((side*30,-28,z+2.6),(side*30,26,z+2.6),2.8,LOG,6)
    for k in range(9):logs+=tube((-33+k*8.2,-30,37),(-33+k*8.2,28,37),3.2,LOG,6)
    body+=logs+box(0,-26.5,17,8,1,4,BLACK,0)+frustum(0,2,39,30,24,16,12,8,SAND)
    body+=flag(-26,14,47,28,12)
    tris,guns=mg(0,-22,10,1.0,japanese=True)
    s=Spec(body+tris)
    for g in guns:s.gun(g)
    return s

def bunker_usn():
    body=disc(0,0,.2,70,EARTH,18)+frustum(0,6,0,64,54,46,40,22,EARTH)                  # earth berm
    body+=box(0,4,18,48,40,8,CONCRETE)+box(0,4,26,50,42,4,CONCRETE_DK)                 # concrete roof slabs
    body+=box(0,-37,10,30,4,10,CONCRETE)+box(0,-41.2,13,24,.8,4,BLACK,0)               # firing slit
    body+=frustum(0,-48,0,32,10,30,5,12,EARTH)
    body+=box(32,44,0,9,14,16,CONCRETE)+box(32,30.4,2,5,1,12,(60,62,56),0)              # stair entrance
    for x in (-24,20):body+=cyl(x,20,30,2.4,12,STEEL,8)+cyl(x,20,42,4,2,STEEL,8)       # ventilators
    body+=cyl(-34,-14,30,.6,40,STEEL,4)                                                 # radio whip
    for k in range(6):body+=bag(-36+k*14,-30,30,0,9,5,4)
    body+=flag(-30,24,30,32,16)
    tris,guns=mg(0,-40,8,1.1)
    s=Spec(body+tris)
    for g in guns:s.gun(g)
    return s

def bunker_ijn():
    """Betio-style blockhouse: sloped reinforced concrete under coral sand, log-revetted entrance."""
    body=disc(0,0,.2,74,SAND_DK,18)+frustum(0,4,0,70,58,52,42,20,CORAL)                  # coral sand cover
    body+=loft([[(-50,-40,14),(50,-40,14),(50,40,14),(-50,40,14)],[(-40,-30,40),(40,-30,40),(40,32,40),(-40,32,40)]],CONCRETE,(False,True))
    for x in (-22,22):body+=obox(x,-35.6,24,9,1.6,3.2,0,BLACK,0)                         # sloped-face slits
    body+=obox(-45.5,0,24,1.6,7,3,0,BLACK,0)+obox(45.5,0,24,1.6,7,3,0,BLACK,0)
    body+=cyl(10,6,40,7,4,CONCRETE_DK,10)+cyl(10,6,44,5,2,STEEL,10)                      # roof cupola
    for k in range(5):body+=tube((-60,44,4+k*5.2),(-30,44,4+k*5.2),2.8,LOG,6)  # entrance revetment
    body+=box(-44,44,0,9,6,14,CONCRETE_DK)+box(-44,37.6,1,5,1,11,BLACK,0)
    body+=frustum(0,10,40,30,22,18,12,6,SAND)+flag(26,22,40,30,14)
    tris,guns=mg(-22,-36,14,1.0,japanese=True)
    s=Spec(body+tris)
    for g in guns:s.gun(g)
    return s

def _helix(x0,x1,y,z,r,pitch,colour,wire=.45):
    tris=[];n=int((x1-x0)/pitch*9);prev=None
    for k in range(n+1):
        t=k/9*math.tau;x=x0+(x1-x0)*k/n
        p=(x,y+math.cos(t)*r,z+r+math.sin(t)*r)
        if prev:tris+=tube(prev,p,wire,colour,3,caps=False)
        prev=p
    return tris

def wire_concertina():
    wire=(84,82,76)
    body=_helix(-52,52,-9,0,9,9,wire)+_helix(-52,52,9,0,9,9,wire)+_helix(-50,50,0,15.5,9,10,wire)
    for x in (-50,-25,0,25,50):
        for y in (-18,18):body+=tube((x,y,0),(x,y,30),1,STEEL,3)
    for y in (-18,18):body+=tube((-50,y,29),(50,y,29),.35,wire,3,caps=False)
    body+=box(25,-19.5,18,5,.4,4,TEAM,0)+box(25,-20,24,1,.3,1.4,WHITE,0)                   # warning plate
    return Spec(body)

def _hedgehog(x,y,yaw,colour=STEEL):
    # Three beams crossing at the centre, rotated so it stands on three ends.
    tris=[];L=20
    q=[(1,0,0),(0,1,0),(0,0,1)]
    # rotate so (1,1,1) is vertical: rotate about z by 45, then tilt by asin(1/sqrt3)
    a=math.radians(45);b=math.atan(math.sqrt(2))
    def rot(v):
        x1,y1,z1=v[0]*math.cos(a)-v[1]*math.sin(a),v[0]*math.sin(a)+v[1]*math.cos(a),v[2]
        return (x1*math.cos(b)-z1*math.sin(b),y1,x1*math.sin(b)+z1*math.cos(b))
    dirs=[rot(v) for v in q]
    lift=max(-d[2] for d in dirs)*L
    for d in dirs:
        c=(0,0,lift)
        tris+=tube(_add(c,_mul(d,-L)),_add(c,_mul(d,L)),2.4,colour,4,phase=math.pi/4)
    return place(tris,x,y,0,yaw)

def at_obstacles():
    body=box(0,10,0,62,9,3,CONCRETE_DK,0)
    for k in range(6):                                                               # dragon's teeth
        x=-52+k*20.8;body+=frustum(x,10,3,8.5,8.5,3,3,19,CONCRETE)
    for k,(x,y,yaw) in enumerate(((-38,-24,10),(0,-28,40),(38,-22,-15))):body+=_hedgehog(x,y,yaw)
    body+=flag(58,26,3,32,12)
    return Spec(body)

def mg_nest():
    body=_pit(30,3,(90,110),EARTH,7)+bag(-10,22,.5,0,9,5,4)
    tris,guns=mg(0,-8,1,1.1)
    body+=tris+crate(14,8,.5,4,3,3,20,OD_DK)+crate(-14,10,.5,4,3,3,-10,OD_DK)+flag(22,18,0,34,12)
    s=Spec(body)
    for g in guns:s.gun(g)
    return s

def airfield_tower():
    body=box(0,0,0,40,34,2,CONCRETE_DK,0)+box(0,4,2,30,26,30,CONCRETE)+box(0,4,32,31,27,2,CONCRETE_DK,0)
    for x in (-20,0,20):body+=box(x,-22.4,12,5,.6,8,GLASS,0)                            # ground-floor windows
    body+=box(-12,-22.4,2,5,.6,18,(70,62,48),0)
    body+=box(2,6,34,22,18,20,CONCRETE_LT)+box(2,6,54,30,26,2,CONCRETE_DK,0)            # second storey + catwalk
    for x in (-27,31):body+=box(x,6,56,.5,26,6,STEEL,0)
    body+=box(2,-19.5,56,29.5,.5,6,STEEL,0)+box(2,31.5,56,29.5,.5,6,STEEL,0)
    body+=box(2,6,56,18,15,18,GLASS,0)                                                  # glass cab
    for x in (-16,-5,9,20):body+=box(x,-9.5,56,1,.8,18,STEEL,0)
    for y in (-4,16):body+=box(-16.5,y,56,.8,1,18,STEEL,0)+box(20.5,y,56,.8,1,18,STEEL,0)
    body+=box(2,6,74,21,18,3,CONCRETE_DK,0)
    for k in range(8):body+=box(-36,-14+k*5,2+k*4,4,2.5,1.2,STEEL_LT,0)                   # outside stair
    body+=cyl(10,10,77,3,5,STEEL,8)
    body+=cyl(-12,14,77,.7,30,STEEL,4)+box(-12,14,96,6,.5,.5,STEEL,0)                   # antenna
    body+=cyl(34,28,2,.8,38,STEEL,4)+tube((34,28,40),(34,12,36),3,(232,110,40),8,r1=1.4)  # windsock
    body+=flag(-6,-2,77,26,14)
    beacon=cyl(0,0,0,2.8,3,(250,200,90),8)+box(2.8,0,1,.6,1.6,1,LENS,0)
    s=Spec(body);s.spin.append((beacon,(10,10,82),'spin'))
    return s

def fuel_depot():
    body=box(0,0,0,72,58,1.5,EARTH,0)
    for x in (-30,30):
        body+=cyl(x,10,1.5,22,34,SILVER,16)+cyl(x,10,35.5,22,5,SILVER,16,r1=8)+cyl(x,10,40.5,3,2,STEEL,8)
        body+=box(x+22.5,10,1.5,1,2.5,38,STEEL,0)+cyl(x,10,14,22.4,1.2,STEEL,16,caps=False)
        body+=box(x,-6,22,4,.4,5,TEAM if x<0 else WHITE,0)
    for side in (-1,1):body+=frustum(0,10+side*36,1.5,64,4,60,1.5,9,EARTH_DK)               # berm walls
    body+=frustum(-64+0,10,1.5,4,36,1.5,32,9,EARTH_DK)+frustum(64,10,1.5,4,36,1.5,32,9,EARTH_DK)
    body+=tube((-30,-12,6),(30,-12,6),1.6,STEEL,6)+box(0,-24,1.5,8,6,10,OD)+tube((0,-12,6),(0,-18,6),1.6,STEEL,6)
    colours=(OD,RED,NAVY_GREY,OD)
    for k in range(4):body+=drum(-50+k*9.5,-42,1.5,colours[k])
    for k in range(3):body+=drum(-45.5+k*9.5,-42,14.5,colours[(k+1)%4])
    for k in range(3):body+=drum(16,-36-k*9.4,1.5,OD,lying=True,yaw=0)
    body+=flag(58,-44,1.5)
    return Spec(body)

def _shell_stack(x,y,z,rows=3,per=4,r=2.6,length=16):
    tris=[]
    for row in range(rows):
        for k in range(per-row):
            sx=x+(k-(per-row-1)/2)*r*2.1;sz=z+r+row*r*1.8
            tris+=tube((sx,y-length/2,sz),(sx,y+length*.25,sz),r,BRASS,6)+tube((sx,y+length*.25,sz),(sx,y+length/2,sz),r,STEEL_LT,6,r1=.6)
    return tris

def ammo_dump():
    body=box(0,0,0,74,60,1.5,EARTH,0)
    for k,x in enumerate((-40,0,40)):                                                 # three revetted bays
        body+=bag_wall(x-17,-14,x-17,44,1.5,3,seed=k)+bag_wall(x+17,-14,x+17,44,1.5,3,seed=k+5)+bag_wall(x-15,46,x+15,46,1.5,3,seed=k+9)
    body+=crate(-40,10,1.5,9,6,7)+crate(-40,10,8.5,8,5,6,6)+crate(-40,28,1.5,9,6,7,0,OD_DK)
    body+=_shell_stack(0,16,1.5)+_shell_stack(0,34,1.5,2,3)
    body+=frustum(40,18,1.5,13,22,6,14,16,CANVAS)+frustum(40,18,17.5,6,14,2,10,3,CANVAS)     # tarp-covered pile
    body+=crate(6,-40,1.5,7,5,5,20)+crate(16,-46,1.5,7,5,5,-10,OD_DK)
    body+=box(30,-42,1.5,1,1,22,WOOD,0)+box(30,-42.5,16,8,.6,6,RED,0)+box(30,-43.2,18,5,.3,1.5,WHITE,0)    # warning sign
    body+=flag(62,-44,1.5)
    return Spec(body)

# ---------------------------------------------------------------- airfield (neutral)
def type98(x,y,z,s=1,colour=IJA,elevation=35):
    """Japanese Type 98 20 mm: wheeled carriage set down on three outrigger legs, top box magazine."""
    tris=[]
    for a,L in ((-90+40,22),(-90-40,22),(90,26)):
        r=math.radians(a)
        tris+=tube((x,y,z+7*s),(x+math.cos(r)*L*s,y+math.sin(r)*L*s,z),1.6*s,colour,5)
        tris+=cyl(x+math.cos(r)*L*s,y+math.sin(r)*L*s,z,2.6*s,1.4*s,STEEL,6)
    tris+=box(x,y+2*s,z+5*s,7*s,9*s,5*s,colour)                                       # carriage
    for side in (-1,1):tris+=wheel(x+side*10*s,y+8*s,z+9*s,6*s,1.8*s,colour)            # travel wheels, raised
    tris+=cyl(x,y,z+10*s,4*s,8*s,colour,10)+box(x,y,z+17*s,5*s,6*s,4*s,colour)          # pedestal + cradle
    tris+=box(x-8*s,y+7*s,z+13*s,3*s,2.5*s,1*s,STEEL,0)+tube((x-5*s,y+4*s,z+15*s),(x-8*s,y+7*s,z+13*s),.6*s,STEEL,4)  # gunner's seat
    P=(x,y,z+22*s);d=aim(elevation);u=up_of(d)
    tris+=tube(_add(P,_mul(d,-9*s)),_add(P,_mul(d,6*s)),2.4*s,colour,4,phase=math.pi/4)      # receiver
    tris+=tube(_add(P,_mul(u,2.4*s),_mul(d,-3*s)),_add(P,_mul(u,9*s),_mul(d,-2*s)),2*s,STEEL_LT,4,phase=math.pi/4)  # 20-round box magazine
    tris+=box(x+5*s,y-3*s,z+24*s,1*s,1*s,4*s,STEEL,0)                                  # sight post
    gun=tube(_add(P,_mul(d,4*s)),_add(P,_mul(d,40*s)),1*s,STEEL,6)
    gun+=tube(_add(P,_mul(d,38*s)),_add(P,_mul(d,43*s)),1.2*s,STEEL,6,r1=1.8*s)
    return tris,[Gun(gun,d,2*s,[(_add(P,_mul(d,44*s)),d,4*s)],(0,150,300,450,600,750))]

def aa_type98():
    tris,guns=type98(0,0,1,1.0)
    s=Spec(_pit(34,3,(90,50),EARTH,8)+tris+_ammo_clips(-18,20,2,IJA,30)+flag(26,22,0,40,14))
    for g in guns:s.gun(g)
    return s

def radar_ijn():
    """IJN Type 13-style early-warning radar: ladder array on a mast beside a wooden operations hut."""
    pad=box(0,0,0,66,56,6,EARTH_DK,0)
    body=box(-34,20,0,18,22,18,WOOD)+frustum(-34,20,18,20,24,4,24,9,WOOD_DK)                      # hut + gable-ish roof
    body+=box(-52.4,14,4,.6,5,6,GLASS,0)+box(-34,-2.4,0,5,.6,13,(60,48,34),0)
    body+=box(40,30,0,11,8,10,IJA)+tube((29,30,4),(-16,20,3),.7,BLACK,4)                          # generator
    body+=_lattice(18,24,0,64,9,4,WOOD_DK,3)+cyl(18,24,64,6,3,STEEL,10)                         # timber mast
    body+=flag(-46,40,27,24,11)
    body=pad+place(body,0,0,4.5)
    arr=tube((0,0,0),(0,0,6),1.3,STEEL,6)
    for side in (-1,1):
        arr+=tube((side*4,-2,6),(side*4,-2,58),.8,STEEL_LT,4)+tube((side*4,3,6),(side*4,3,58),.6,STEEL,4)   # driven + reflector rails
    for k in range(11):
        z=9+k*4.8
        arr+=tube((-11,-3,z),(11,-3,z),.45,WHITE,3,caps=False)+tube((-9,3,z),(9,3,z),.4,STEEL,3,caps=False)
    s=Spec(body);s.spin.append((arr,(18,24,71.5),'sweep'))
    return s

def _desaturate(colour,amount=.75,dim=.86):
    g=sum(colour)/3
    return tuple(int(min(255,(c+(g-c)*amount)*dim)) for c in colour)

def _airfield_marks():
    """Team colour that reads from the RTS camera: a tall flag and roof bands on the hangar."""
    from tools.frontline import imported
    tris=imported.triangles('airfield')
    marks=flag(100,-104,3,112,44)
    for x in (-40,40):
        z=_height_at(tris,x,2)
        marks+=gi.boxes([(x,2,z+.15,4,30,.8,TEAM)])
    return tris,marks

def airfield():
    """Capturable airfield: every team-colour part (flag, roof bands, tower marker) follows the
    owner, so neutral Player(15) shows grey (Emberfield TeamColor15) with no model swap."""
    tris,marks=_airfield_marks()
    return Spec(tris+marks)

def airfield_neutral():
    """Optional swap model: weathered grey, flagless, no team colour at all."""
    tris,marks=_airfield_marks()
    pole=[t for t in marks if t[1]!=TEAM]
    return Spec([(p,(128,128,124) if c==TEAM else _desaturate(c),tag) for p,c,tag in tris+pole])

# ---------------------------------------------------------------- AA upgrade mount
MOUNT_RADIUS=26
def aa_mount():
    """The AA upgrade: compact sandbagged twin Bofors. Origin at the base of the sandbags
    (z=0), front -Y, up +Z; attached at (0, Y, Z) per catalog.AA_MOUNT."""
    ring=disc(0,0,.2,MOUNT_RADIUS+2,EARTH,14)+bag_ring(0,0,0,MOUNT_RADIUS,2,(90,60),9,5,4,seed=11)
    tris,guns=bofors(0,0,.5,.6,True,OD,outriggers=False,shield=True,stagger=40)
    s=Spec(ring+tris+flag(MOUNT_RADIUS-3,MOUNT_RADIUS-6,0,24,10))
    for g in guns:s.gun(g)
    return s

# Mirror of catalog.AA_MOUNT {model: (Y, Z)} (RTS thread; catalog.py is theirs, so the
# tests prefer catalog.AA_MOUNT when it exists). The mount sits at (0, Y, Z).
AA_MOUNT_CONTRACT={'headquarters':(0,112),'barracks':(0,65),'depot':(0,49),'factory':(0,93),
    'airfield':(0,75),'shipyard':(0,69),'bunker':(0,47),'coastalgun':(0,48),'watchtower':(0,139),
    'pillbox_usn':(0,41),'pillbox_ijn':(0,46),'coastal_usn':(0,38),'coastal_ijn':(0,48),
    'radar_usn':(-22,6),'radar_ijn':(-20,6)}
def aa_mount_table():
    try:
        from tools.frontline import catalog
        return dict(getattr(catalog,'AA_MOUNT',None) or AA_MOUNT_CONTRACT)
    except ImportError:
        return dict(AA_MOUNT_CONTRACT)

# Final names (RTS thread) first, then extras.
NAMED=('pillbox_usn','pillbox_ijn','aa_oerlikon','aa_type98','aa_bofors','aa_type96','aa_m1_90mm','aa_type88',
       'coastal_usn','coastal_ijn','radar_usn','radar_ijn','aa_mount')
EXTRAS=('bunker_usn','bunker_ijn','mg_nest','searchlight','wire_concertina','at_obstacles','airfield_tower','fuel_depot','ammo_dump')
STRUCTURES=NAMED+EXTRAS
GUNS=('pillbox_usn','pillbox_ijn','aa_oerlikon','aa_type98','aa_bofors','aa_type96','aa_m1_90mm','aa_type88',
      'coastal_usn','coastal_ijn','aa_mount','bunker_usn','bunker_ijn','mg_nest')

_base_cache={}
def base_triangles(name):
    """Static triangles of any building: these structures or the imported catalog art."""
    if name not in _base_cache:
        if name in BUILDERS:_base_cache[name]=BUILDERS[name]().triangles()
        else:
            from tools.frontline import imported
            _base_cache[name]=imported.triangles(name)
    return _base_cache[name]

def _height_at(tris,x,y):
    """Highest surface straight above/below (x, y): a downward ray against every face."""
    best=0.0
    for (a,b,c),_,_ in tris:
        d=(b[0]-a[0])*(c[1]-a[1])-(c[0]-a[0])*(b[1]-a[1])
        if abs(d)<1e-6:continue
        u=((x-a[0])*(c[1]-a[1])-(c[0]-a[0])*(y-a[1]))/d
        v=((b[0]-a[0])*(y-a[1])-(x-a[0])*(b[1]-a[1]))/d
        if u<-1e-6 or v<-1e-6 or u+v>1+1e-6:continue
        best=max(best,a[2]+u*(b[2]-a[2])+v*(c[2]-a[2]))
    return best

def surface(name,y,r=MOUNT_RADIUS*.5):
    """Roof (or ground) the mount rests on at (0, y): highest surface over its central disc."""
    tris=base_triangles(name)
    pts=[(0,y)]+[(r*math.cos(k*math.tau/8),y+r*math.sin(k*math.tau/8)) for k in range(8)]
    return round(max(_height_at(tris,px,py) for px,py in pts),1)

def suggested_mounts(tolerance=1.5):
    """{model: (Y, Z)} where this art's roof under (0, Y) differs from the contract Z."""
    return {n:(y,surface(n,y)) for n,(y,z) in aa_mount_table().items() if abs(surface(n,y)-z)>tolerance}

def mounted(name,y=None,z=None):
    """Static triangles of a structure with the AA mount attached per the contract."""
    if y is None:y,z=aa_mount_table()[name]
    return base_triangles(name)+place(triangles('aa_mount'),0,y,z)

BUILDERS={n:globals()[n] for n in STRUCTURES if n!='aa_mount'}
BUILDERS['aa_mount']=aa_mount
BUILDERS['airfield']=airfield
BUILDERS['airfield_neutral']=airfield_neutral
MODELS=tuple(BUILDERS)

def spec(name):
    return BUILDERS[name]()

_tri_cache={}
def triangles(name):
    """Static model-space triangles (guns at rest, arrays at rest): previews, icons, tests."""
    if name not in _tri_cache:_tri_cache[name]=spec(name).triangles()
    return _tri_cache[name]

ICON_YAW=-100
def icon_triangles(name):
    """generate.icon turns imported art by 180 degrees; this pre-turn gives a front three-quarter view."""
    return gi.transform(triangles(name),yaw=ICON_YAW-180)

def preview(name,size=256,tris=None):
    """Front three-quarter render for contact sheets (same view as the build icon)."""
    return gi.preview(gi.transform(tris or triangles(name),yaw=ICON_YAW),size)

def geometry(existing):
    """models.GEOMETRY boxes (footprint from the ground parts + a team cell). The airfield
    keeps its existing boxes, so its footprint and selection never change."""
    out={}
    for name in BUILDERS:
        if name=='airfield':continue
        if name=='airfield_neutral':out[name]=list(existing['airfield']);continue
        if name=='aa_mount':
            out[name]=[(0,0,0,MOUNT_RADIUS,MOUNT_RADIUS,30,0),(0,0,30,2,2,2,8)];continue
        tris=triangles(name)
        pts=[p for t in tris for p in t[0] if p[2]<24]
        lo=[min(p[i] for p in pts) for i in range(2)];hi=[max(p[i] for p in pts) for i in range(2)]
        top=max(p[2] for t in tris for p in t[0])
        out[name]=[((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,0,(hi[0]-lo[0])/2,(hi[1]-lo[1])/2,top,0),(0,0,top,2,2,2,8)]
    return out

# ---------------------------------------------------------------- MDX
ATTACK,DEATH,DECAY,END=ua.ATTACK,ua.DEATH,ua.DECAY,ua.END
LOOPS=(ua.STAND,ua.WALK,ua.ATTACK,ua.WORK,ua.STANDWORK,ua.BIRTH)

def _flash(bones,tip,d,size,shots,parent=0):
    a,b=ATTACK
    bones.append(rm.Bone('Flash',parent,tip));fid=len(bones)-1
    alpha=[(0,0.0)];scale=[(a,.4,.4,.4)]
    for t in shots:
        alpha+=[(a+t-1,0.0),(a+t,1.0),(a+t+55,1.0),(a+t+56,0.0)]
        scale+=[(a+t,.5,.5,.5),(a+t+22,1.5,1.5,1.5),(a+t+55,.35,.35,.35)]
    alpha.append((END,0.0));scale.append((b,.4,.4,.4))
    bones[fid].scale+=sorted({k[0]:k for k in scale}.values())
    tris=ua.puff(d[0]*size*.8,d[1]*size*.8,d[2]*size*.8,size,FLASH)+ua.puff(d[0]*size*1.9,d[1]*size*1.9,d[2]*size*1.9,size*.6,FLASH_CORE)
    return rm.Layer(tris,rm.ADD,fid,sorted({k[0]:k for k in alpha}.values()))

def _smoke(bones,tip,d,size,t0):
    a,b=ATTACK
    bones.append(rm.Bone('GunSmoke',0,tip));sid=len(bones)-1
    bones[sid].translation+=[(a+t0,0,0,0),(a+t0+80,d[0]*size*1.5,d[1]*size*1.5,d[2]*size+size*.3),(b,d[0]*size*4,d[1]*size*4,size*2.5)]
    bones[sid].scale+=[(a+t0,.3,.3,.3),(a+t0+80,1,1,1),(b,2.8,2.8,2.8)]
    return rm.Layer(ua.puff(0,0,0,size*1.1,SMOKE),rm.BLEND,sid,[(0,0.0),(a+t0+59,0.0),(a+t0+60,.6),(b,0.0),(END,0.0)])

def mdx(name):
    s=spec(name);rng=random.Random(name)
    tris=s.triangles();lo,hi=gi.bounds(tris);h=max(10.0,hi[2]-lo[2]);w=max(hi[0]-lo[0],hi[1]-lo[1])
    bones=[rm.Bone('Root')];root=bones[0]
    a,b=DEATH;c,e=DECAY
    sink=-h*.75
    root.translation+=[(a,0,0,0),(a+250,0,0,h*.04),(a+600,0,0,sink*.35),(b,0,0,sink*.6),(c,0,0,sink*.6),(e,0,0,sink)]
    root.rotation+=[(a,*rm.euler(0,0,0)),(a+600,*rm.euler(2.5,-2,0)),(b,*rm.euler(3,-3,0)),(e,*rm.euler(3,-3,0))]
    fade=[(0,1.0),(END-400,1.0),(END,0.0)]
    layers=ua.split_team(s.body,0,fade)
    for i,g in enumerate(s.guns):
        bones.append(rm.Bone(f'Recoil{i}',0,(0,0,0)));bid=len(bones)-1
        keys=[(ATTACK[0],0,0,0)];shots=sorted(g.shots)
        for k,t in enumerate(shots):
            nxt=shots[k+1] if k+1<len(shots) else 1000
            back=_mul(g.direction,-g.recoil)
            keys+=[(ATTACK[0]+t,0,0,0),(ATTACK[0]+t+30,*back),(ATTACK[0]+t+min(260,int((nxt-t)*.85)),0,0,0)]
        keys.append((ATTACK[1],0,0,0))
        bones[bid].translation+=sorted({k[0]:k for k in keys}.values())
        layers+=ua.split_team(g.tris,bid,fade)
        for tip,d,size in g.muzzles:
            layers.append(_flash(bones,tip,d,size,shots))
            if g.smoke:layers.append(_smoke(bones,tip,d,size,shots[0]))
    for k,(part,pivot,mode) in enumerate(s.spin):
        bones.append(rm.Bone(f'Spin{k}',0,pivot));sid=len(bones)-1
        for s0,e0 in LOOPS:
            if mode=='spin':
                for j in range(5):bones[sid].rotation.append((s0+(e0-s0)*j//4,*rm.euler(0,0,90*j)))
            else:   # radar: slow sweep out and back inside each loop
                for j,yaw in enumerate((0,35,0,-35,0)):bones[sid].rotation.append((s0+(e0-s0)*j//4,*rm.euler(0,0,yaw)))
        layers.append(rm.Layer(gi.transform(part,1,(0,0,0)),rm.OPAQUE,sid,fade))
    if s.beam:
        on=[]
        for w0,w1 in (ATTACK,ua.WORK,ua.STANDWORK):on+=[(w0-1,0.0),(w0,.32),(w1,.32),(w1+1,0.0)]
        layers.append(rm.Layer(s.beam,rm.ADD,0,[(0,0.0)]+on+[(END,0.0)]))
    layers+=ua.explosion(bones,(0,0,h*.4),max(14.0,w*.16),DEATH[0]+60,rng,debris_colour=CONCRETE_DK,smoke_until=DECAY[1]-400)
    return rm.emit(name,layers,bones,ua.UNIT_SEQ)

def triangle_count(data):
    """Total triangles in an emitted MDX (every geoset, effects included)."""
    import struct
    pos=4;total=0
    while pos<len(data):
        tag=data[pos:pos+4];size=struct.unpack_from('<I',data,pos+4)[0]
        if tag==b'GEOS':
            o=pos+8;end=o+size
            while o<end:
                gsize=struct.unpack_from('<I',data,o)[0];chunk=data[o:o+gsize]
                i=chunk.find(b'PCNT');total+=struct.unpack_from('<I',chunk,i+8)[0];o+=gsize
        pos+=8+size
    return total
