"""Which Frontline models come from CC0 meshes (third_party/CREDITS.md) and how.

Every recipe returns engine-space triangles fitted to the unit's existing box
silhouette (models.GEOMETRY stays the source of footprints, icons' framing,
selection scale and wakes). Warships, landing craft, projectiles and the
remaining artillery stay procedural boxes; the Emberfield pine becomes a palm.
"""
import hashlib
import math
import pickle
from pathlib import Path

from tools.frontline import gltf_import as gi

TEAM=gi.TEAM
# Material atlas colours (cells 0-7, cell 8 = team) used when boxes are mixed in.
MAT=[(128,124,102),(106,119,120),(146,136,105),(94,82,58),(189,165,123),(40,47,46),(120,141,144),(88,105,63)]
OLIVE=(92,102,62);OLIVE_DARK=(70,78,48);GUNMETAL=(70,72,76);KHAKI=(132,120,84)
CACHE=Path(__file__).resolve().parents[2]/'build'/'frontline-import-cache'

def cached(tag,builder):
    """Decimation is the slow part (~3 s per mesh); keep results keyed by source bytes + recipe."""
    src=b''.join(p.read_bytes() for p in sorted((gi.SOURCE/'polypizza').glob('*.glb')))
    key=hashlib.sha1(src+Path(__file__).read_bytes()+Path(gi.__file__).read_bytes()+tag.encode()).hexdigest()[:16]
    path=CACHE/f'{tag}-{key}.pickle'
    if path.is_file():return pickle.loads(path.read_bytes())
    tris=builder()
    CACHE.mkdir(parents=True,exist_ok=True);path.write_bytes(pickle.dumps(tris))
    return tris

def part(name,size,budget,yaw=0,axis='xy',include=None,colours=None):
    tris=gi.load(name,yaw,include)
    if colours:tris=gi.recolour(tris,colours)
    return gi.decimate(gi.fit(tris,size,axis),budget)

def place(tris,x=0,y=0,z=0,yaw=0,scale=1):
    return gi.transform(tris,scale,(x,y,z),yaw)

def box_tris(boxes):
    """Building boxes with bevelled edges (thin trims stay sharp)."""
    from tools.frontline import ships
    out=[]
    for x,y,z,w,d,h,c in boxes:
        colour=TEAM if c==8 else MAT[c]
        out+=ships.bevel_box(x,y,z,w,d,h,colour,min(w,d,h)*.12) if min(w,d,h)>=3 else gi.boxes([(x,y,z,w,d,h,colour)])
    return out

def flag(x,y,z,height=60,width=22,yaw=0):
    """Pole + team-colour flag: the readable team marker on imported art."""
    return place(gi.boxes([(0,0,0,1.2,1.2,height,(60,58,52)),(width/2+1,0,height-16,width/2,.8,15,TEAM)]),x,y,z,yaw)

def pennant(tris,height=26):
    """Antenna pennant at the rear-left of a vehicle's top."""
    lo,hi=gi.bounds(tris)
    return flag(lo[0]*.55,hi[1]*.45,hi[2]*.62,height,12,180)

# ---------------------------------------------------------------- infantry
# Realistic-proportion body (Quaternius SWAT, CC0) in a two-handed firing stance:
# the one-handed pointing pose with the right arm mirrored onto the left. Head,
# helmet, uniform colours and every piece of WWII kit are built here per role.
POSE='CharacterArmature|Idle_Gun_Pointing';ARMS=('Shoulder','UpperArm','LowerArm','Wrist')
UNIFORM=(92,96,62);WEBBING=(116,108,78);BOOTS=(70,54,38);SKIN=(190,146,108)
HELMET=(78,84,56);WOOD=(112,74,42);METAL=(48,49,52);CANVAS=(110,104,74)
def ellipsoid(cx,cy,cz,rx,ry,rz,colour,detail=1):
    return [(tuple((cx+(p[0]-cx)*rx/10,cy+(p[1]-cy)*ry/10,cz+(p[2]-cz)*rz/8.5) for p in t),colour,'e') for t,_,_ in puff(cx,cy,cz,10,colour,detail)]

def rod(x0,x1,y,z,r,colour,segments=6):
    """Cylinder along +X from x0 to x1 (gun barrels, stocks)."""
    from tools.frontline import ships
    tube=ships.cylinder(0,0,0,r,(x1-x0)/2,0,colour,segments,axis='y')
    return gi.transform(tube,1,((x0+x1)/2,y,z),-90)

def tank_pair(x,z0,z1,r,colour):
    from tools.frontline import ships
    return sum((ships.cylinder(x,y,z0,r,r,z1-z0,colour,8) for y in (-r*1.15,r*1.15)),[])

def kit(name,bones):
    """WWII kit in metres, engine frame (+X forward), around the posed bones."""
    from tools.frontline import ships
    head=bones['Head'];hx,hz=head[0]+.01,head[2]
    wr,wl=bones['Wrist.R'],bones['Wrist.L']
    gx=(wr[0]+wl[0])/2;gz=(wr[2]+wl[2])/2;gy=(wr[1]+wl[1])/2-.02
    parts=ellipsoid(hx,0,hz+.11,.095,.085,.12,SKIN)                       # head
    if name=='commando':                                                    # soft patrol cap
        parts+=ships.cylinder(hx-.01,0,hz+.17,.105,.1,.07,(60,64,46),10)+ships.bevel_box(hx+.09,0,hz+.17,.05,.09,.015,(60,64,46),.01)
    else:                                                                   # M1 steel helmet with brim
        parts+=ellipsoid(hx-.005,0,hz+.17,.135,.125,.105,HELMET)+ships.cylinder(hx-.005,0,hz+.15,.155,.145,.018,HELMET,12)
    pack=ships.bevel_box(-.17,0,1.02,.075,.15,.21,CANVAS,.03)               # field pack
    flap=gi.boxes([(-.17,0,1.23,.07,.13,.012,TEAM)])                       # team patch on the pack flap
    band=gi.boxes([(bones['UpperArm.L'][0]+.02,bones['UpperArm.L'][1]+.05,bones['UpperArm.L'][2]-.12,.05,.035,.05,TEAM)])
    parts+=gi.boxes([(.02,0,.98,.13,.15,.05,WEBBING)])                       # cartridge belt
    parts+=ships.cylinder(-.05,.14,.86,.045,.045,.13,(70,72,58),8)          # canteen
    if name=='rifle':                                                       # M1 Garand + bayonet
        parts+=pack+flap+rod(gx-.38,gx+.05,gy,gz,.032,WOOD)+rod(gx+.05,gx+.55,gy,gz+.01,.012,METAL)+rod(gx+.55,gx+.72,gy,gz+.01,.006,(150,150,150))
    elif name=='machinegun':                                                # M1919: perforated jacket, ammo can, bipod
        parts+=pack+flap+rod(gx-.30,gx+.02,gy,gz,.04,WOOD)+gi.boxes([(gx+.12,gy,gz-.06,.13,.05,.1,METAL)])
        parts+=rod(gx+.2,gx+.78,gy,gz+.01,.03,(40,40,42),8)+gi.boxes([(gx+.06,gy-.14,gz-.24,.08,.05,.08,(74,78,52))])
        parts+=gi.boxes([(gx+.62,gy-.06,gz-.24,.008,.008,.22,METAL),(gx+.62,gy+.06,gz-.24,.008,.008,.22,METAL)])
    elif name=='commando':                                                  # Thompson SMG, light kit
        parts+=rod(gx-.26,gx+.05,gy,gz,.03,WOOD)+gi.boxes([(gx+.12,gy,gz-.05,.09,.035,.08,METAL)])+rod(gx+.2,gx+.42,gy,gz+.01,.016,METAL)
        parts+=ships.bevel_box(-.15,0,1.1,.06,.12,.14,(64,66,50),.02)+gi.boxes([(-.15,0,1.24,.055,.1,.01,TEAM)])
    elif name=='mortar':                                                    # M2 60 mm mortar tube and baseplate on the back, carbine in hand
        parts+=pack+flap+gi.transform(ships.cylinder(0,0,0,.045,.045,.75,(52,56,44),8),1,(-.24,.06,.9))
        parts+=gi.transform(ships.cylinder(0,0,0,.14,.14,.025,(60,62,52),8),1,(-.27,-.02,.7))
        parts+=rod(gx-.3,gx+.05,gy,gz,.028,WOOD)+rod(gx+.05,gx+.4,gy,gz+.01,.011,METAL)
    elif name=='engineer':                                                  # M2 flamethrower tanks, wand in hand
        parts+=tank_pair(-.2,.82,1.38,.075,(84,88,64))+ships.cylinder(-.2,0,1.15,.03,.03,.25,METAL,6)
        parts+=gi.boxes([(-.2,0,1.36,.03,.17,.02,TEAM)])
        parts+=rod(gx-.2,gx+.25,gy,gz,.03,(70,72,60),8)+rod(gx+.25,gx+.52,gy,gz+.01,.016,METAL)
    return parts+band

# Imperial Japanese Army/SNLF kit: Type 98 khaki, puttees, Type 90 helmet with cloth cover.
IJA_UNIFORM=(146,128,84);IJA_WEBBING=(104,82,54);IJA_PUTTEES=(160,142,98);IJA_HELMET=(122,112,74);IJA_STAR=(214,182,64)
def kit_ijn(name,bones):
    from tools.frontline import ships
    head=bones['Head'];hx,hz=head[0]+.01,head[2]
    wr,wl=bones['Wrist.R'],bones['Wrist.L']
    gx=(wr[0]+wl[0])/2;gz=(wr[2]+wl[2])/2;gy=(wr[1]+wl[1])/2-.02
    parts=ellipsoid(hx,0,hz+.11,.095,.085,.12,SKIN)
    if name=='commando':                                                    # field cap with neck flaps
        parts+=ellipsoid(hx-.01,0,hz+.18,.11,.105,.07,IJA_UNIFORM)+ships.bevel_box(hx+.1,0,hz+.17,.045,.08,.012,(70,58,40),.01)
        parts+=gi.boxes([(hx-.11,0,hz+.03,.02,.1,.1,IJA_UNIFORM)])
    else:                                                                   # Type 90: rounder, shallower brim, cloth cover, star
        parts+=ellipsoid(hx-.005,0,hz+.18,.128,.12,.1,IJA_HELMET)+ships.cylinder(hx-.005,0,hz+.155,.14,.132,.012,IJA_HELMET,12)
        parts+=gi.boxes([(hx+.127,0,hz+.2,.006,.022,.022,IJA_STAR)])
    pack=ships.bevel_box(-.16,0,1.05,.07,.14,.17,(118,100,66),.04)+ships.cylinder(-.16,0,1.24,.05,.14,0,(90,84,62),8,axis='y')  # pack + rolled blanket
    flap=gi.boxes([(-.16,0,1.225,.06,.12,.012,TEAM)])
    band=gi.boxes([(bones['UpperArm.L'][0]+.02,bones['UpperArm.L'][1]+.05,bones['UpperArm.L'][2]-.12,.05,.035,.05,TEAM)])
    parts+=gi.boxes([(.02,0,.98,.13,.15,.04,IJA_WEBBING)])+gi.boxes([(.12,s*.09,.96,.035,.05,.05,IJA_WEBBING) for s in (-1,1)])  # belt + cartridge boxes
    parts+=ships.cylinder(-.05,.14,.86,.04,.04,.12,(98,82,54),8)
    if name=='rifle':                                                       # Arisaka Type 99 with long Type 30 bayonet
        parts+=pack+flap+rod(gx-.4,gx+.1,gy,gz,.03,(96,58,32))+rod(gx+.1,gx+.6,gy,gz+.01,.011,METAL)+rod(gx+.6,gx+.86,gy,gz+.01,.006,(160,160,160))
    elif name=='machinegun':                                                # Type 99 LMG: top box magazine, bipod, finned barrel
        parts+=pack+flap+rod(gx-.32,gx,gy,gz,.035,(96,58,32))+gi.boxes([(gx+.1,gy,gz-.04,.12,.04,.08,METAL)])
        parts+=gi.boxes([(gx+.08,gy,gz+.06,.05,.02,.09,METAL)])+rod(gx+.2,gx+.62,gy,gz+.01,.026,(44,44,46),8)+rod(gx+.62,gx+.76,gy,gz+.01,.012,METAL)
        parts+=gi.boxes([(gx+.58,gy-.06,gz-.22,.008,.008,.2,METAL),(gx+.58,gy+.06,gz-.22,.008,.008,.2,METAL)])
    elif name=='commando':                                                  # Type 100 SMG: side magazine, bayonet lug
        parts+=rod(gx-.3,gx+.05,gy,gz,.03,(96,58,32))+rod(gx+.05,gx+.4,gy,gz+.01,.016,METAL)+gi.boxes([(gx+.12,gy+.07,gz,.03,.06,.025,METAL)])
        parts+=ships.bevel_box(-.15,0,1.1,.06,.12,.13,(110,96,64),.02)+gi.boxes([(-.15,0,1.235,.055,.1,.01,TEAM)])
    elif name=='mortar':                                                    # Type 89 knee mortar carried at the hip, rifle in hand
        parts+=pack+flap+rod(-.05,.55,-.2,.95,.03,(60,62,50),8)+gi.boxes([(-.08,-.2,.95,.05,.05,.02,(60,62,50))])
        parts+=rod(gx-.4,gx+.1,gy,gz,.028,(96,58,32))+rod(gx+.1,gx+.5,gy,gz+.01,.011,METAL)
    elif name=='engineer':                                                  # Type 93 flamethrower: three tanks
        parts+=sum((ships.cylinder(-.2,y,.85,.055,.055,.5,(92,90,70),8) for y in (-.12,0,.12)),[])+gi.boxes([(-.2,0,1.37,.03,.17,.02,TEAM)])
        parts+=rod(gx-.2,gx+.25,gy,gz,.028,(80,76,60),8)+rod(gx+.25,gx+.55,gy,gz+.01,.015,METAL)
    return parts+band

def soldier(name):
    if name.endswith('_ijn'):
        base_name=name[:-4]
        body=gi.load('swat',0,('Swat_Legs','Swat_Feet','Swat_Body'),(),POSE,0,ARMS)
        body=gi.recolour(body,{'Swat':IJA_UNIFORM,'Swat_Black':IJA_WEBBING,'Skin':SKIN})
        # Puttees wrap the lower legs; split-toe boots below.
        legs=[t for t in body if .12<=min(p[2] for p in t[0]) and max(p[2] for p in t[0])<.5]
        feet=[t for t in body if min(p[2] for p in t[0])<.12]
        rest=[t for t in body if t not in legs and t not in feet]
        body=rest+gi.recolour(legs,{IJA_UNIFORM:IJA_PUTTEES,IJA_WEBBING:IJA_PUTTEES})+gi.recolour(feet,{IJA_UNIFORM:(78,58,40),IJA_WEBBING:(78,58,40)})
        tris=gi.decimate(body,1700)+kit_ijn(base_name,gi.load_bones('swat',POSE,0,0,ARMS))
        return gi.fit(tris,70,'z')
    return soldier_usn(name)

def soldier_usn(name):
    body=gi.load('swat',0,('Swat_Legs','Swat_Feet','Swat_Body'),(),POSE,0,ARMS)
    tint={'Swat':UNIFORM,'Swat_Black':WEBBING,'Skin':SKIN}
    if name=='commando':tint.update(Swat=(66,72,54),Swat_Black=(84,80,60))
    if name=='engineer':tint.update(Swat=(104,104,74))
    body=gi.recolour(body,tint)
    feet=[t for t in body if min(p[2] for p in t[0])<.12]
    body=[t for t in body if min(p[2] for p in t[0])>=.12]+gi.recolour(feet,{WEBBING:BOOTS,UNIFORM:BOOTS})
    tris=gi.decimate(body,1700)+kit(name,gi.load_bones('swat',POSE,0,0,ARMS))
    return gi.fit(tris,72,'z')

# ---------------------------------------------------------------- vehicles
def tank(name):
    """Procedural M4 Sherman / M26 Pershing / Type 97 Chi-Ha / Type 3 Chi-Nu (tools/frontline/armor.py)."""
    from tools.frontline import armor
    tris=fit_to(name,armor.TANKS[name]())
    if name.endswith('_ijn'):tris+=armor.hinomaru(tris,-22 if name=='tank_ijn' else -30,16,6)
    return tris+pennant(tris)

# ---------------------------------------------------------------- aircraft
def _loft(stations,segments=10,colour=(128,128,128)):
    """Fuselage from (x, half-width, half-height, z-centre) stations, nose at +X."""
    rings=[]
    for x,w,h,zc in stations:
        rings.append([(x,w*math.cos(a),zc+h*math.sin(a)) for a in (i*math.tau/segments for i in range(segments))])
    tris=[]
    for r0,r1 in zip(rings,rings[1:]):
        for i in range(segments):
            j=(i+1)%segments
            tris+=[((r0[i],r1[i],r1[j]),colour,'hull'),((r0[i],r1[j],r0[j]),colour,'hull')]
    for ring,flip in ((rings[0],False),(rings[-1],True)):
        cx=sum(p[0] for p in ring)/len(ring);cz=sum(p[2] for p in ring)/len(ring)
        for i in range(segments):
            a,b=ring[i],ring[(i+1)%segments]
            tris.append((((cx,0,cz),b,a) if flip else ((cx,0,cz),a,b),colour,'cap'))
    return tris

def _slab(root_x,root_chord,tip_x,tip_chord,span,z,thick,colour,dihedral=0,y0=0):
    """Tapered wing/tailplane panel pair (both sides), leading edge toward +X."""
    tris=[]
    for side in (1,-1):
        ry=y0*side;ty=(y0+span)*side;tz=z+dihedral
        pts=[(root_x,ry,z),(root_x-root_chord,ry,z),(tip_x-tip_chord,ty,tz),(tip_x,ty,tz)]
        top=[(x,y,zz+thick) for x,y,zz in pts];bot=[(x,y,zz-thick*.4) for x,y,zz in pts]
        quads=[(top[0],top[3],top[2],top[1]),(bot[0],bot[1],bot[2],bot[3]),(top[0],bot[0],bot[3],top[3]),
               (top[1],top[2],bot[2],bot[1]),(top[2],top[3],bot[3],bot[2])]
        for q in quads:
            if side<0:q=q[::-1]
            tris+=[((q[0],q[1],q[2]),colour,'wing'),((q[0],q[2],q[3]),colour,'wing')]
    return tris

def _disc(x,y,z,r,colour,n=12,normal='z'):
    pts=[(x+r*math.cos(a),y+r*math.sin(a),z) if normal=='z' else (x,y+r*math.cos(a),z+r*math.sin(a)) for a in (i*math.tau/n for i in range(n))]
    return [(((x,y,z),pts[i],pts[(i+1)%n]),colour,'decal') for i in range(n)]

def _star(x,y,z,r,colour):
    pts=[]
    for i in range(10):
        a=math.pi/2+i*math.pi/5;rr=r if i%2==0 else r*.38
        pts.append((x+rr*math.cos(a),y+rr*math.sin(a),z))
    return [(((x,y,z),pts[i],pts[(i+1)%10]),colour,'decal') for i in range(10)]

def _insignia(x,y,z,r,kind):
    if kind=='usn':return _disc(x,y,z,r,(28,48,96))+_star(x,y,z+.6,r*.92,(236,236,236))
    if kind=='ijn':return _disc(x,y,z,r*1.05,(236,236,236))+_disc(x,y,z+.6,r*.82,(186,28,32))
    return _disc(x,y,z,r,TEAM)

def _prop(x,z,r,colour=(34,34,36)):
    blades=gi.boxes([(x,0,z-1,1,1.2,2,colour)])
    for a in (0,120,240):
        c,s=math.cos(math.radians(a)),math.sin(math.radians(a))
        y1,z1=r*c,r*s
        blades+=[(((x,0,z),(x,y1-s*2,z+z1+c*2),(x,y1+s*2,z+z1-c*2)),colour,'prop'),
                 (((x,0,z),(x,y1+s*2,z+z1-c*2),(x,y1-s*2,z+z1+c*2)),colour,'prop')]
    return blades

AIRCRAFT={ # span, length, canopy length, top, underside, insignia, twin engine
    'fighter':(92,72,12,(84,96,64),(150,156,150),'team',False),
    'recon':(88,76,22,(92,104,86),(160,166,160),'team',False),
    'bomber':(150,104,20,(80,92,62),(146,150,146),'team',True),
    'wildcat':(58,62,12,(70,90,116),(196,200,204),'usn',False),
    'dauntless':(70,70,22,(74,94,120),(196,200,204),'usn',False),
    'avenger':(80,80,24,(70,90,116),(196,200,204),'usn',False),
    'zero':(64,64,14,(184,184,160),(176,178,160),'ijn',False),
    'val':(68,72,22,(62,76,54),(160,160,146),'ijn',False),
    'kate':(78,82,24,(62,76,54),(160,160,146),'ijn',False)}
def aircraft(name):
    span,length,canopy,top,under,kind,twin=AIRCRAFT[name]
    half=length/2;r=length*.085;zc=20
    stations=[(half,r*.9,r*.9,zc),(half-4,r*1.08,r*1.05,zc),(half*.55,r*1.12,r*1.15,zc+1),(0,r,r*1.05,zc+1),
              (-half*.55,r*.62,r*.72,zc+2),(-half+3,r*.25,r*.4,zc+3),(-half,r*.12,r*.25,zc+3)]
    tris=_loft(stations,14,top)
    cowl=_loft([(half+1,r*.95,r*.95,zc),(half-6,r*1.1,r*1.1,zc)],14,(48,48,50))
    glass=_loft([(half*.42,r*.45,r*.5,zc+r*.95),(half*.42-canopy,r*.5,r*.6,zc+r*1.05),(half*.42-canopy-6,r*.2,r*.3,zc+r*.9)],8,(150,190,210))
    wing_x=half*.38;chord=length*.3
    wings=_slab(wing_x,chord,wing_x-chord*.25,chord*.55,span/2-r*.6,zc-r*.55,1.6,top,4,r*.6)
    tail=_slab(-half+length*.13,length*.14,-half+length*.06,length*.08,span*.17,zc+1,1,top,0,r*.2)
    fin=gi.boxes([(-half+6,0,zc+2,6,.9,r*1.8,top)])
    # Roundels sit on the dihedral upper surface at 68% half-span.
    deck=zc-r*.55+1.6+4*(span*.34-r*.6)/(span/2-r*.6)+.8
    ins=_insignia(wing_x-chord*.45,span*.34,deck,chord*.26,kind)+_insignia(wing_x-chord*.45,-span*.34,deck,chord*.26,kind)
    parts=tris+cowl+glass+wings+tail+fin+ins
    if twin:
        for side in (1,-1):
            y=side*span*.2
            parts+=place(_loft([(chord*.2,r*.55,r*.55,0),(-chord*.35,r*.5,r*.5,0),(-chord*.8,r*.15,r*.2,0)],8,top),wing_x,y,zc-r*.3)
            parts+=place(_prop(0,0,r*1.6),wing_x+chord*.21,y,zc-r*.3)
        parts+=_insignia(-half*.45,0,zc+r*1.05+.5,r*.6,kind)
    else:
        parts+=_prop(half+2,zc,r*1.7)
    lo,hi=gi.bounds(parts)
    return gi.transform(parts,1,(0,0,-lo[2]+8))

# ---------------------------------------------------------------- buildings and props
def crate(s=1):return place(cached('crate',lambda:part('crate',26,120)),scale=s)
def barrel(s=1):return place(cached('barrel',lambda:part('barrel',13,110,colours={(110,147,167):(84,92,60)})),scale=s)
def container():return cached('container',lambda:part('container_green',62,300,90,'x'))
def sandbags(length=80):return place(cached('sandbags',lambda:part('sandbags',80,700,90,'x')),scale=length/80)
def water_tower():return cached('water_tower',lambda:part('water_tower',150,420,0,'z'))
def tent():return cached('tent',lambda:part('tent',74,420,0,'x'))

def _geometry(name):
    from tools.frontline import models
    return models.GEOMETRY[name]

def building(name):
    if name=='watchtower':
        tower=cached('guard_tower',lambda:part('guard_tower',155,420,0,'z',colours={'Celing':TEAM}))
        return tower+place(sandbags(44),0,-34,0)
    if name=='sandbag':return place(sandbags(80),0,2,0)+flag(-38,-14,0,38,12)
    if name=='barracks':
        pad=box_tris([(0,-6,0,86,78,3,3)])
        tents=[place(tent(),x,y,3) for x in (-40,40) for y in (-38,34)]
        return pad+sum(tents,[])+place(sandbags(60),-40,-82,3)+flag(70,-70,3,90,30)+[t for b in (crate(.9),) for t in place(b,6,-4,3)]
    if name=='depot':
        return box_tris([(0,-6,0,50,50,3,3)])+place(container(),-6,16,3,90)+place(crate(),26,-24,3)+place(crate(),26,-24,29)+place(crate(.8),2,-30,3)+place(barrel(),-30,-30,3)+place(barrel(),-38,-24,3)+flag(-42,-46,3,70,24)
    if name=='stockpile':
        crates=[place(crate(),x,y,3+z) for x,y,z in [(-40,-20,0),(-14,-20,0),(-27,-20,26),(-40,8,0),(-14,8,0)]]
        barrels=[place(barrel(),x,y,3) for x,y in [(20,-28),(34,-28),(48,-28),(20,-12),(34,-12)]]
        return box_tris([(0,0,0,62,48,3,3)])+sum(crates,[])+sum(barrels,[])+place(sandbags(70),18,26,3)+place(outcrop(),-10,52,0)+flag(54,-40,3,70,24)
    # Original procedural silhouettes, dressed with props around them.
    tris=box_tris(_geometry(name))
    lo=[min(b[i]-b[i+3] for b in _geometry(name)) for i in range(2)];hi=[max(b[i]+b[i+3] for b in _geometry(name)) for i in range(2)]
    if name=='headquarters':tris+=place(water_tower(),hi[0]-14,hi[1]-14,0)+place(barrel(),lo[0]+10,lo[1]-6)+place(barrel(),lo[0]+24,lo[1]-6)
    elif name=='factory':tris+=place(container(),lo[0]+20,hi[1]+8,0,90)+place(crate(),hi[0]-6,lo[1]-14)+place(crate(),hi[0]-6,lo[1]-14,26)
    elif name=='airfield':tris+=sum((place(barrel(),hi[0]-8-12*i,lo[1]-8) for i in range(4)),[])
    elif name=='shipyard':tris+=place(crate(),lo[0]+12,hi[1]-16)+place(crate(),lo[0]+12,hi[1]-42)+place(barrel(),lo[0]+40,hi[1]-14)
    elif name in ('bunker','coastalgun'):tris+=place(sandbags(70),-30,lo[1]-12,0)+place(sandbags(70),36,lo[1]-12,0,8)
    return tris

# ---------------------------------------------------------------- scenery
def palm():
    return cached('palm',lambda:part('palm_a',170,460,0,'z'))
def outcrop():
    """Grey island rocks behind the materiel stockpile (the mine)."""
    def build():
        rock=gi.decimate(gi.fit(gi.recolour(gi.load('rock_large'),{'Atlas':(118,112,100)}),80),200)
        rocks=gi.decimate(gi.fit(gi.load('rock_medium'),46),260)
        return rock+place(rocks,58,-6,0,40)
    return cached('outcrop',build)

def puff(x,y,z,r,colour,detail=1):
    """Low-poly sphere (subdivided octahedron) for smoke and flame effects."""
    tris=[((0,0,1),(1,0,0),(0,1,0)),((0,0,1),(0,1,0),(-1,0,0)),((0,0,1),(-1,0,0),(0,-1,0)),((0,0,1),(0,-1,0),(1,0,0))]
    tris+=[(a,c,b) for a,b,c in (((0,0,-1),p,q) for _,p,q in tris)]
    unit=lambda v:tuple(c/math.sqrt(sum(d*d for d in v)) for c in v)
    for _ in range(detail):
        nxt=[]
        for a,b,c in tris:
            ab,bc,ca=(unit(tuple((p+q)/2 for p,q in zip(u,v))) for u,v in ((a,b),(b,c),(c,a)))
            nxt+=[(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)]
        tris=nxt
    return [(tuple((x+r*p[0],y+r*p[1],z+r*p[2]*.85) for p in t),colour,'puff') for t in tris]

EFFECTS={'smoke':(puff(0,0,10,11,(92,92,94))+puff(6,4,20,8,(110,110,112))+puff(-5,-3,17,7,(80,80,82))),
         'fire':(puff(0,0,7,6,(255,120,32))+puff(-2,2,13,4,(255,190,70)))}

# Projectiles: the original box body in flight, a rounded fireball on impact (Death).
PROJECTILE_BURST={'tracer':(6,(255,214,120)),'shell':(15,(255,138,40)),'bomb':(22,(255,120,30))}
def projectile(name):
    from tools.frontline import models
    # Slim round bodies: a glowing tracer streak, an ogival shell, a finned bomb.
    if name=='tracer':body=rod(-14,14,0,1.5,1.1,(255,226,140),5)
    elif name=='shell':body=rod(-7,5,0,2,2.2,(120,112,84),8)+rod(5,10,0,2,1.4,(150,120,60),8)
    else:body=rod(-12,10,0,5,4.5,(70,74,58),10)+rod(10,15,0,5,2.5,(70,74,58),8)+gi.boxes([(-13,0,5,2.5,6,.4,(60,64,50)),(-13,0,1,2.5,.4,8,(60,64,50))])
    r,colour=PROJECTILE_BURST[name]
    burst=puff(0,0,r*.4,r,colour)+puff(r*.35,r*.2,r*.8,r*.7,(255,200,90))+puff(-r*.3,-r*.25,r*.9,r*.6,(96,92,88))
    return body,burst
PROJECTILE_SCALE=[(0,1),(70,1),(2999,1),(3000,.35),(3120,1),(3400,1.35),(3800,1.5),(3999,0),(4000,1)]

INFANTRY=("rifle","machinegun","commando","mortar","engineer")
INFANTRY_IJN=("rifle_ijn","machinegun_ijn","commando_ijn","mortar_ijn")
# ---------------------------------------------------------------- artillery (procedural, +X forward)
GUNMETAL_OLIVE=(86,94,60);TYRE=(36,36,34)
def wheel(x,y,r,width,colour=TYRE,hub=GUNMETAL_OLIVE):
    """Tyre on the ground (centre height r) with an outboard hub."""
    from tools.frontline import ships
    return ships.cylinder(x,y,r,r,width/2,0,colour,14,axis='y')+ships.cylinder(x,y+(width/2+.4)*(1 if y>0 else -1),r,r*.45,.4,0,hub,8,axis='y')

def pitch(tris,degrees,pivot=(0,0,0)):
    """Rotate about the Y axis through pivot (positive raises +X)."""
    c,s=math.cos(math.radians(degrees)),math.sin(math.radians(degrees));px,py,pz=pivot
    return [(tuple((px+(x-px)*c-(z-pz)*s,y,pz+(x-px)*s+(z-pz)*c) for x,y,z in pts),colour,tag) for pts,colour,tag in tris]

def slab(x0,y0,x1,y1,z,w,h,colour):
    """Bevelled beam between two ground points (split trails, outriggers)."""
    from tools.frontline import ships
    length=math.hypot(x1-x0,y1-y0);yaw=math.degrees(math.atan2(y1-y0,x1-x0))
    return gi.transform(ships.bevel_box(0,0,0,length/2,w,h,colour,min(w,h)*.3),1,((x0+x1)/2,(y0+y1)/2,z),yaw)

def howitzer(_):
    """M2A1 105 mm on split-trail carriage with shield, firing toward +X."""
    from tools.frontline import ships
    c=GUNMETAL_OLIVE
    tris=wheel(4,25,14,7)+wheel(4,-25,14,7)
    tris+=gi.transform(ships.cylinder(0,0,0,2,23,0,c,8,axis='y'),1,(4,0,14))
    tris+=slab(-2,7,-56,22,4,3.5,3,c)+slab(-2,-7,-56,-22,4,3.5,3,c)+gi.boxes([(-57,s*22,0,3,3,4,c) for s in (-1,1)])
    gun=ships.bevel_box(4,0,18,14,6,8,c,1.5)+rod(-12,6,0,24,4.2,c,10)+rod(6,72,0,25,2.6,(70,76,50),10)+rod(70,76,0,25,3.4,(60,64,46),10)
    gun+=rod(-6,30,4,20,1.4,(60,64,46),6)+rod(-6,30,-4,20,1.4,(60,64,46),6)
    tris+=pitch(gun,14,(4,0,20))
    tris+=gi.transform(ships.bevel_box(0,0,0,1.2,24,10,c,.6),1,(16,0,16))+gi.boxes([(14,0,26,.6,6,4,TEAM)])
    return tris

def halftrack(_):
    """M16 half-track with a quad .50 Maxson mount (anti-aircraft)."""
    from tools.frontline import ships
    c=GUNMETAL_OLIVE;dark=(58,62,44)
    tris=wheel(28,20,8,6)+wheel(28,-20,8,6)
    for s in (-1,1):
        tris+=ships.bevel_box(-14,s*19,2,22,5,11,dark,2.5)+sum((wheel(x,s*19,5.5,9.5,(48,48,44)) for x in (-30,-20,-10,0)),[])
    tris+=ships.bevel_box(-10,0,10,30,16,10,c,1.5)+ships.bevel_box(26,0,10,14,13,9,c,3)+ships.bevel_box(16,0,18,3,15,7,dark,.8)
    tris+=gi.boxes([(40,0,10,1,12,7,(40,40,38))])+ships.bevel_box(26,0,19,13,14,1,c,.4)
    mount=ships.cylinder(-12,0,20,9,9,4,dark,12)+ships.bevel_box(-12,0,24,6,10,8,c,1.5)
    for dy,dz in ((-6,0),(6,0),(-6,5),(6,5)):mount+=rod(-6,22,dy,28+dz,1.1,(40,40,38),6)
    tris+=pitch(mount,22,(-12,0,26))+gi.boxes([(-34,0,22,2,8,.6,TEAM)])
    return tris

def calliope(_):
    """Truck-mounted rocket launcher: 4x6 tube rack elevated over the bed."""
    from tools.frontline import ships
    c=GUNMETAL_OLIVE;dark=(58,62,44)
    tris=sum((wheel(x,s*21,8,7) for x in (26,-12,-26) for s in (-1,1)),[])
    tris+=ships.bevel_box(-8,0,8,34,15,6,dark,1.5)+ships.bevel_box(24,0,14,12,15,14,c,3)+ships.bevel_box(10,0,14,4,16,16,c,2)
    tris+=gi.boxes([(17,0,22,.6,13,6,(60,80,96))])+gi.boxes([(37,0,10,1,13,8,(40,40,38))])
    rack=[]
    for i in range(6):
        for k in range(4):rack+=rod(-40,8,-15+i*6,24+k*5,2.2,(70,76,52),6)
    rack+=ships.bevel_box(-16,0,20,8,19,2,dark,.6)
    tris+=pitch(rack,18,(-16,0,22))+gi.boxes([(-38,0,16,2,10,.6,TEAM)])
    return tris

def fit_to(name,tris):
    from tools.frontline import models
    box=models.GEOMETRY[name]
    want=max(b[0]+b[3] for b in box)-min(b[0]-b[3] for b in box)
    lo,hi=gi.bounds(tris)
    return gi.transform(tris,want/(hi[0]-lo[0]),(0,0,0))

def jeep(_):
    """Willys MB: flat fenders, folded windscreen, spare wheel, pintle .30 cal."""
    from tools.frontline import ships
    c=(84,92,58);dark=(56,60,42)
    tris=sum((wheel(x,s*15,7,5) for x in (22,-18) for s in (-1,1)),[])
    tris+=ships.bevel_box(0,0,8,34,13,6,c,1.5)+ships.bevel_box(24,0,14,11,11,5,c,2.5)          # tub, hood
    tris+=sum((ships.bevel_box(x,s*15,13,9,4,1.2,c,.5) for x in (22,-18) for s in (-1,1)),[])  # fenders
    tris+=gi.boxes([(34,0,8,1,10,6,(40,40,38))])+ships.bevel_box(12,0,20,1,13,1,dark,.4)       # grille, folded screen
    tris+=gi.boxes([(-6,s*7,14,4,4,5,dark) for s in (-1,1)])+gi.boxes([(-24,s*7,14,5,5,4,dark) for s in (-1,1)])  # seats
    tris+=gi.transform(ships.cylinder(0,0,0,7,2.5,0,TYRE,12,axis='y'),1,(-35,0,15),90)       # spare wheel
    tris+=ships.cylinder(-14,0,14,1,1,14,METAL,6)+rod(-18,6,0,30,1.3,(40,40,38),6)            # pintle mount + .30 cal
    tris+=gi.boxes([(-28,-9,20,.4,.4,14,dark),(-28,-11,30,.4,3,4,TEAM)])                       # whip antenna pennant
    return tris

ARTILLERY={'artillery':howitzer,'antiair':halftrack,'rocketart':calliope,'scoutcar':jeep}

RECIPES={**{n:soldier for n in INFANTRY+INFANTRY_IJN},**{n:tank for n in ('tank','heavytank','tank_ijn','heavytank_ijn')},
         **{n:(lambda name,f=f:fit_to(name,f(name))) for n,f in ARTILLERY.items()},
         **{n:aircraft for n in AIRCRAFT},
         **{n:building for n in ('headquarters','barracks','depot','factory','airfield','shipyard','bunker','coastalgun','watchtower','stockpile','sandbag')}}
SCENERY={'pine':palm}

def triangles(name):
    if name in SCENERY:return SCENERY[name]()
    if name in INFANTRY+INFANTRY_IJN:
        return cached(name,lambda:RECIPES[name](name))
    return RECIPES[name](name)
