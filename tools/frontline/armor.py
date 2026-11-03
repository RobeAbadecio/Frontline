"""Original procedural WWII tanks: M4 Sherman, M26 Pershing, Type 97 Chi-Ha, Type 3 Chi-Nu.

Hulls and turrets are lofted rounded-rectangle sections (cast/curved armour),
tracks are rounded belts with road wheels, bogies, sprockets and idlers, plus
guns, mantlets, hatches, stowage and markings. Built nose toward +X in
approximate metres, then fitted to the unit's length by imported.fit_to.
"""
import math

from tools.frontline import gltf_import as gi
from tools.frontline import ships

TEAM=gi.TEAM
OD=(84,92,58);OD_DARK=(64,70,46);TRACK=(46,44,40);STEEL=(70,70,68);WHITE=(226,226,214)
IJN_BROWN=(118,92,58);IJN_GREEN=(84,96,58);IJN_KHAKI=(170,150,98);IJN_LINE=(206,190,120)

def section(x,w,z0,z1,r,n=3):
    """Rounded rectangle at station x (in the Y/Z plane), counter-clockwise from +Y side."""
    r=min(r,w*.95,(z1-z0)*.48)
    pts=[]
    for cy,cz,a0 in ((w-r,z1-r,0),(-(w-r),z1-r,90),(-(w-r),z0+r,180),(w-r,z0+r,270)):
        for i in range(n+1):
            a=math.radians(a0+90*i/n)
            pts.append((x,cy+r*math.cos(a),cz+r*math.sin(a)))
    return pts

def loft(stations,colour,cap=True):
    """Surface through rounded sections (x, half-width, z bottom, z top, corner radius)."""
    rings=[section(*s) for s in stations]
    tris=[]
    def outward(pts,cz):
        # Side faces point away from their section's centre line (y=0, z=cz).
        n=gi._normal(*pts);m=(0,sum(p[1] for p in pts)/3,sum(p[2] for p in pts)/3-cz)
        return pts if gi._dot(n,m)>=0 else (pts[0],pts[2],pts[1])
    for a,b,sa,sb in zip(rings,rings[1:],stations,stations[1:]):
        n=len(a);cz=(sa[2]+sa[3]+sb[2]+sb[3])/4
        for i in range(n):
            j=(i+1)%n
            tris+=[(outward((a[i],a[j],b[j]),cz),colour,'s'),(outward((a[i],b[j],b[i]),cz),colour,'s')]
    if cap:
        for ring,sign in ((rings[0],-1),(rings[-1],1)):
            c=(ring[0][0],0,sum(p[2] for p in ring)/len(ring))
            for i in range(len(ring)):
                pts=(c,ring[i],ring[(i+1)%len(ring)])
                if gi._normal(*pts)[0]*sign<0:pts=(pts[0],pts[2],pts[1])
                tris.append((pts,colour,'s'))
    return tris

def solid(stations,colour):
    return loft(stations,colour)

def wheel(x,y,z,r,width,colour=STEEL,segments=10):
    return ships.cylinder(x,y,z,r,width/2,0,colour,segments,axis='y')

def track_run(y,length,height,width,wheels,r_wheel,sprocket_front=True,bogies=None):
    """One side: belt (rounded loop), road wheels, drive sprocket, idler, optional VVSS bogies."""
    half=length/2;rr=height/2
    # Ends taper like a belt wrapped round the sprocket and idler (rounded in X-Z).
    stations=[(-half+rr*(1-k),width/2,height*lo if lo else 0,height*(1-lo) if lo else height,.03) for k,lo in ((1,.42),(.75,.12),(.35,.0))]
    stations+=[(half-rr*(1-k),width/2,height*lo if lo else 0,height*(1-lo) if lo else height,.03) for k,lo in ((.35,.0),(.75,.12),(1,.42))]
    belt=solid(stations,TRACK)
    tris=gi.transform(belt,1,(0,y,0))
    side=1 if y>0 else -1
    span=length-2*r_wheel-height*.4
    for i in range(wheels):
        x=-span/2+span*i/max(1,wheels-1)
        tris+=wheel(x,y+side*(width/2+.02),r_wheel,r_wheel,width*.35,STEEL)
    sx=half-rr if sprocket_front else -half+rr
    tris+=wheel(sx,y+side*(width/2+.03),height*.62,rr*.85,width*.3,OD_DARK)
    tris+=wheel(-sx,y+side*(width/2+.03),height*.62,rr*.7,width*.3,STEEL)
    if bogies:
        for x in bogies:
            tris+=ships.bevel_box(x,y+side*(width/2+.12),r_wheel*.9,r_wheel*1.3,.1,r_wheel*1.1,OD_DARK,.05)
    return tris

def star(x,y,z,r,colour=WHITE,facing='y'):
    pts=[]
    for i in range(10):
        a=math.pi/2+i*math.pi/5;rr=r if i%2==0 else r*.4
        pts.append((x+rr*math.cos(a),y,z+rr*math.sin(a)) if facing=='y' else (x+rr*math.cos(a),y+rr*math.sin(a),z))
    c=(x,y,z)
    # Face outward: +Y sides need clockwise-in-XZ order, top decals counter-clockwise in XY.
    out=[]
    for i in range(10):
        tri=(c,pts[i],pts[(i+1)%10])
        n=gi._normal(*tri)
        want=(0,1 if y>0 else -1,0) if facing=='y' else (0,0,1)
        out.append((tri if gi._dot(n,want)>0 else (c,pts[(i+1)%10],pts[i]),colour,'decal'))
    return out

def barrel(x0,x1,z,r,colour=STEEL,y=0,segments=10):
    from tools.frontline.imported import rod
    return rod(x0,x1,y,z,r,colour,segments)

def subdivide(tris,edge=.62):
    """Split triangles by their longest edge until every edge is shorter than `edge` (camo detail)."""
    out=[];stack=list(tris)
    while stack:
        pts,c,tag=stack.pop()
        lengths=[math.dist(pts[i],pts[(i+1)%3]) for i in range(3)]
        k=max(range(3),key=lambda i:lengths[i])
        if lengths[k]<=edge:out.append((pts,c,tag));continue
        a,b,o=pts[k],pts[(k+1)%3],pts[(k+2)%3];m=tuple((u+v)/2 for u,v in zip(a,b))
        stack+=[((a,m,o),c,tag),((m,b,o),c,tag)]
    return out

def camo(tris,palette,scale=1.3):
    """Japanese three-colour scheme: bands from a smooth world-space pattern, with a yellow line."""
    tris=[t for t in tris if t[1]!=IJN_GREEN]+subdivide([t for t in tris if t[1]==IJN_GREEN])
    out=[]
    for pts,c,tag in tris:
        if c not in (IJN_GREEN,):out.append((pts,c,tag));continue
        x,y,z=(sum(p[i] for p in pts)/3 for i in range(3))
        v=math.sin(x*scale+z*1.7)+.7*math.sin(y*2.1-x*.8+1.3)+.4*math.sin(z*3.1+y)
        colour=palette[0] if v<-.45 else palette[1] if v<.55 else palette[2]
        if abs(v-.55)<.06:colour=IJN_LINE
        out.append((pts,colour,tag))
    return out

def sherman():
    """M4A3 (75): rounded cast hull front, high silhouette, VVSS bogies, cast turret."""
    t=track_run(1.18,5.4,.95,.42,6,.32,True,bogies=(-1.7,0,1.7))+track_run(-1.18,5.4,.95,.42,6,.32,True,bogies=(-1.7,0,1.7))
    hull=solid([(-2.95,1.05,.55,1.85,.15),(-2.6,1.32,.55,2.0,.2),(1.4,1.32,.55,2.0,.2),(2.5,1.22,.55,1.55,.35),(2.95,1.0,.45,.95,.4)],OD)
    turret=solid([(-1.35,.85,2.0,2.62,.5),(-.9,1.05,2.0,2.8,.55),(.3,1.0,2.0,2.85,.5),(.9,.8,2.05,2.7,.4)],OD)
    t+=hull+gi.transform(turret,1,(-.2,0,0))
    t+=ships.bevel_box(.95,0,2.05,.18,.55,.5,OD_DARK,.08)+barrel(.9,3.6,2.32,.075)                 # mantlet + 75 mm M3
    t+=ships.cylinder(-.6,.4,2.82,.32,.32,.12,OD_DARK,10)+ships.cylinder(-.7,-.4,2.82,.28,.28,.1,OD_DARK,10)  # hatches
    t+=ships.cylinder(-.75,.4,2.94,.04,.04,.4,STEEL,6)+barrel(-.75,.45,3.3,.03,STEEL,.4,6)       # .50 cal
    t+=ships.bevel_box(-2.3,0,2.0,.5,.95,.2,(98,94,70),.08)+ships.bevel_box(-2.55,.4,2.2,.25,.3,.22,(110,100,72),.06)  # stowage
    for y in (-.45,.45):t+=ships.bevel_box(2.6,y,1.35,.06,.18,.12,(60,62,46),.03)                 # spare track blocks
    t+=star(-.6,1.33,1.35,.32)+star(-.6,-1.33,1.35,.32)+star(-.3,0,2.88,.35,WHITE,'z')
    return t

def pershing():
    """M26: long low hull, torsion-bar road wheels, wide turret, 90 mm with muzzle brake."""
    t=track_run(1.38,6.2,.95,.6,6,.38,False)+track_run(-1.38,6.2,.95,.6,6,.38,False)
    hull=solid([(-3.3,1.2,.5,1.7,.12),(1.6,1.2,.5,1.75,.15),(2.9,1.15,.5,1.25,.2),(3.3,1.0,.45,.75,.25)],OD)
    turret=solid([(-2.0,.75,1.75,2.35,.35),(-1.4,1.25,1.75,2.5,.45),(.4,1.3,1.75,2.55,.45),(1.05,1.0,1.75,2.4,.35)],OD)
    t+=hull+turret+ships.bevel_box(1.15,0,1.8,.2,.6,.55,OD_DARK,.08)+barrel(1.1,5.4,2.05,.09)+barrel(5.3,5.65,2.05,.14,OD_DARK)
    t+=ships.cylinder(-.6,.5,2.55,.3,.3,.1,OD_DARK,10)+ships.cylinder(-.6,-.5,2.55,.3,.3,.1,OD_DARK,10)
    t+=ships.bevel_box(-2.9,0,1.75,.35,1.0,.18,(98,94,70),.06)
    t+=star(-.8,1.21,1.15,.32)+star(-.8,-1.21,1.15,.32)
    return t

def chi_ha():
    """Type 97 Chi-Ha: narrow riveted hull, offset small turret, 57 mm, rail antenna."""
    t=track_run(.92,5.0,.8,.32,6,.24,True)+track_run(-.92,5.0,.8,.32,6,.24,True)
    hull=solid([(-2.6,.75,.45,1.55,.06),(1.3,.82,.45,1.6,.06),(2.2,.8,.45,1.25,.1),(2.6,.72,.4,.85,.12)],IJN_GREEN)
    hull+=solid([(-1.4,.9,1.2,1.62,.04),(1.2,.9,1.2,1.62,.04)],IJN_GREEN)                     # sponsons over the tracks
    turret=solid([(-.75,.55,1.6,2.25,.18),(-.3,.62,1.6,2.35,.22),(.45,.6,1.6,2.3,.2),(.7,.5,1.62,2.2,.15)],IJN_GREEN)
    t+=hull+gi.transform(turret,1,(.15,.12,0))
    t+=ships.cylinder(.05,.12,2.33,.24,.24,.18,IJN_GREEN,10)                                     # cupola
    t+=barrel(.85,1.9,1.98,.07,STEEL,.12)+ships.bevel_box(.85,.12,1.85,.08,.2,.25,IJN_GREEN,.04)
    for i in range(12):                                                                         # horseshoe rail antenna
        a=math.radians(-150+300*i/11)
        t+=gi.boxes([(.15+.75*math.cos(a),.12+.75*math.sin(a),2.25,.02,.02,.1,STEEL)])
    for x in (-1.6,-.8,0,.8):t+=gi.boxes([(x,s*.83,1.0,.03,.01,.03,(60,58,44)) for s in (-1,1)])  # rivet rows
    t=camo(t,(IJN_BROWN,IJN_GREEN,IJN_KHAKI))
    return t

def chi_nu():
    """Type 3 Chi-Nu: Chi-He hull, large hexagonal turret, long 75 mm Type 3."""
    t=track_run(1.05,5.6,.85,.38,6,.27,True)+track_run(-1.05,5.6,.85,.38,6,.27,True)
    hull=solid([(-2.8,.95,.45,1.6,.06),(1.6,.98,.45,1.65,.08),(2.4,.95,.45,1.25,.1),(2.8,.85,.4,.85,.12)],IJN_GREEN)
    turret=solid([(-1.3,.75,1.62,2.4,.12),(-.9,1.0,1.62,2.5,.15),(.5,1.0,1.62,2.5,.15),(.95,.8,1.62,2.4,.12)],IJN_GREEN)
    t+=hull+turret+ships.bevel_box(1.0,0,1.75,.15,.45,.5,IJN_GREEN,.06)+barrel(1.0,4.9,2.02,.075)
    t+=ships.cylinder(-.4,.4,2.5,.26,.26,.16,IJN_GREEN,10)
    t=camo(t,(IJN_BROWN,IJN_GREEN,IJN_KHAKI),1.1)
    return t

def hinomaru(tris,x,z,r):
    """Small white-bordered red disc on both hull sides (IJA tanks carried few markings)."""
    lo,hi=gi.bounds(tris)
    out=[]
    for y,sign in ((hi[1]+.01,1),(lo[1]-.01,-1)):
        for radius,colour in ((r,WHITE),(r*.7,(186,30,34))):
            pts=[(x+radius*math.cos(a),y,z+radius*math.sin(a)) for a in (i*math.tau/12 for i in range(12))]
            c=(x,y+sign*.005*(radius<r),z)
            out+=[((c,pts[i],pts[(i+1)%12]) if sign>0 else (c,pts[(i+1)%12],pts[i]),colour,'decal') for i in range(12)]
    return out

TANKS={'tank':sherman,'heavytank':pershing,'tank_ijn':lambda:chi_ha(),'heavytank_ijn':lambda:chi_nu()}
