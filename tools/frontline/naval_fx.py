"""Torpedo and armour-hit effect models (rich_mdx), plus torpedo tube positions.

  torpedo         projectile: dark slim body just under the surface and a white
                  bubble wake trailing astern (+X forward); loops in every live
                  sequence and vanishes in Death
  torpedo_hit     Death: dark/orange flash at the waterline, a column about 3.5x
                  the near-miss splash, spray arcs, a white plume collapsing back,
                  a base surge and foam spreading on the surface (~5 s)
  torpedo_launch  Death: grey compressed-air/powder puff at the tube and the fish
                  entering the water with a small splash (~1.5 s).  The origin is
                  the tube mount; +X points out along the launch direction and the
                  water entry sits LAUNCH_DROP below and LAUNCH_REACH ahead of it.
  armor_spark     Death: a hot flash, additive sparks fanning out and falling, and
                  a grey smoke wisp (~1 s)

TUBES maps each torpedo-armed ship model to its tube mounts in engine space (bow
+X, +Y port, waterline z=0, as ships.triangles returns), one (x, y, z) per mount
at the centre of its tube bundle, z on top of the tubes.  It is derived from the
tube boxes in historical_models.py; the generic destroyer is the Fletcher scaled
the way ships.generic scales it.
"""
import math
import random

from tools.frontline import gltf_import as gi
from tools.frontline import historical_models as hm
from tools.frontline import rich_mdx as rm
from tools.frontline import ships
from tools.frontline import unit_anim as ua

EFFECT_SEQ=ua.EFFECT_SEQ                 # Stand 0-99, Death 100-6099
D0,D1=EFFECT_SEQ[1][1],EFFECT_SEQ[1][2]
MODELS=('torpedo','torpedo_hit','torpedo_launch','armor_spark','launch_wake')

# Palette colours already used by the other effects (the shared atlas has 1024 cells).
FOAM=(240,246,248);FOAM2=(232,240,244);FOAM3=(226,236,240);SPRAY=(236,242,246);RING=(238,244,246)
FIRE=(255,150,50);FIRE2=(255,226,120);HOT=(255,244,190);SPARK=(255,214,120)
SMOKE=(58,56,54);GREY=(160,158,150);DARK=(40,34,28)

def puff(x,y,z,r,colour,detail=1):return ua.puff(x,y,z,r,colour,detail)

def disc(r0,r1,colour,segments=20,z=.4):
    """Flat ring (r0>0) or filled disc (r0=0) on the water."""
    out=[]
    for k in range(segments):
        a0,a1=k*math.tau/segments,(k+1)*math.tau/segments
        c0,s0,c1,s1=math.cos(a0),math.sin(a0),math.cos(a1),math.sin(a1)
        if r0<=0:out.append((((0,0,z),(c0*r1,s0*r1,z),(c1*r1,s1*r1,z)),colour,'disc'));continue
        q=[(c0*r0,s0*r0,z),(c0*r1,s0*r1,z),(c1*r1,s1*r1,z),(c1*r0,s1*r0,z)]
        out+=[((q[0],q[1],q[2]),colour,'ring'),((q[0],q[2],q[3]),colour,'ring')]
    return out

def face_up(tris):
    """Flip flat surface triangles so they all face the camera above."""
    out=[]
    for (a,b,c),colour,tag in tris:
        nz=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        out.append((((a,c,b) if nz<0 else (a,b,c)),colour,tag))
    return out

def window(a,b,on=1.0,end=D1,fade_in=0,fade_out=0):
    """Geoset alpha: 0 outside [a, b]; optional linear fade-in/out."""
    keys={0:0.0,end:0.0}
    if a>0:keys[a-1]=0.0
    keys[a]=0.0 if fade_in else on
    if fade_in:keys[a+fade_in]=on
    if fade_out:keys[b-fade_out]=on
    keys[b]=0.0 if fade_out else on
    if b+1<end:keys[b+1]=0.0
    return sorted(keys.items())

def arc(bone,start,dur,vec,up,steps=8):
    """Ballistic translation keys: out along vec (x, y), up then down by gravity."""
    dx,dy,dz=vec
    for k in range(steps+1):
        f=k/steps;t=start+int(dur*f)
        bone.translation.append((t,dx*f,dy*f,dz*f+up*4*f*(1-f)))

# ------------------------------------------------------------------ torpedo (projectile)
def torpedo_mdx():
    seq=ua.UNIT_SEQ
    live=[(a,b) for n,a,b,_,_ in seq if n!='Death']
    death=ua.DEATH
    bones=[rm.Bone('Root')]
    # Body: 18 long, radius 1.1, axis along X with the tapered nose forward, top just under water.
    body=gi.transform(ships.cylinder(0,0,-.85,1.1,9,0,DARK,8,taper=.45,axis='y'),1,(0,0,0),yaw=90)
    body+=gi.boxes([(-9.6,0,-1.8,.5,.15,1.9,DARK),(-9.6,0,-.85,.5,1.6,.12,DARK)])   # rudders/fins
    hide=[(0,1.0),(death[0]-1,1.0),(death[0],0.0),(death[1],0.0),(death[1]+1,1.0),(ua.END,1.0)]
    layers=[rm.Layer(body,rm.OPAQUE,0,hide)]
    # Surface wake: a white V widening astern, brightest near the fish, in three alpha bands.
    for i,(x0,x1,w0,w1,alpha) in enumerate([(4,-24,2.5,6,.95),(-24,-56,6,11,.75),(-56,-92,11,16,.45)]):
        strip=[]
        for s in (-1,1):   # two foam lines with a paler centre streak between them
            strip+=ships.quad((x0,s*w0*.35,.5),(x1,s*w1*.35,.5),(x1,s*w1,.5),(x0,s*w0,.5),FOAM if i==0 else FOAM2,'wake')
        strip+=ships.quad((x0,-w0*.35,.45),(x1,-w1*.35,.45),(x1,w1*.35,.45),(x0,w0*.35,.45),FOAM3,'wake')
        layers.append(rm.Layer(face_up(strip),rm.BLEND,0,[(t,v*alpha) for t,v in hide]))
    layers.append(rm.Layer(puff(5,0,.6,2.2,FOAM,0)+puff(9,0,.4,1.2,FOAM,0),rm.BLEND,0,[(t,v*.8) for t,v in hide]))   # bow ripple
    # Bubble boils: flat puffs born at the propellers, swelling and fading astern, staggered and looping.
    rng=random.Random('torpedo')
    for i in range(6):
        phase=i/6;y=rng.uniform(-1.5,1.5)
        bones.append(rm.Bone(f'Bubble{i}',0,(-10,y,.6)));b=bones[-1]
        for a,e in live:
            T=e-a;wrap=a+int(T*(1-phase))
            b.translation+=[(a,-70*phase,0,0),(wrap,-70,0,0)]
            b.scale+=[(a,.6+1.6*phase,.6+1.6*phase,.5),(wrap,2.2,2.2,.5)]
            if wrap+1<e:
                b.translation+=[(wrap+1,0,0,0),(e,-70*phase,0,0)]
                b.scale+=[(wrap+1,0,0,0),(wrap+60,.6,.6,.5),(e,.6+1.6*phase,.6+1.6*phase,.5)]
        layers.append(rm.Layer(puff(0,0,0,2.6,SPRAY,0),rm.BLEND,len(bones)-1,[(t,v*.75) for t,v in hide]))
    return rm.emit('torpedo',layers,bones,seq)

# ------------------------------------------------------------------ torpedo hit
def torpedo_hit_mdx(return_parts=False):
    """A torpedo detonating against a hull: column ~3.5x the near-miss splash (~280 vs 80)."""
    rng=random.Random('torpedo_hit')
    t0=D0
    bones=[rm.Bone('Root')];layers=[]
    # Flash at the base: an orange fireball and a dark burst of water and smoke behind it.
    bones.append(rm.Bone('Flash',0,(0,0,6)));f=len(bones)-1
    bones[f].scale+=[(0,.1,.1,.1),(t0,.4,.4,.3),(t0+80,1.7,1.7,1.3),(t0+260,2.3,2.3,1.7),(t0+420,.2,.2,.2),(D1,.2,.2,.2)]
    layers.append(rm.Layer(puff(0,0,4,20,FIRE)+puff(6,3,12,9,FIRE2,0),rm.ADD,f,window(t0,t0+420,1.0,fade_out=200)))
    bones.append(rm.Bone('Dark',0,(0,0,8)));d=len(bones)-1
    bones[d].scale+=[(0,.1,.1,.1),(t0,.3,.3,.3),(t0+200,1.4,1.4,1.6),(t0+900,2.0,2.0,2.4),(D1,2.0,2.0,2.4)]
    bones[d].translation+=[(t0,0,0,0),(t0+900,0,0,30),(D1,0,0,30)]
    layers.append(rm.Layer(puff(0,0,0,22,SMOKE)+puff(-12,8,14,15,SMOKE),rm.BLEND,d,window(t0,t0+1400,.8,fade_out=700)))
    # Main column: a tapering stack of white puffs that shoots up and later slumps.
    col=[]
    for i in range(12):
        z=12+i*23;r=36-i*1.9;a=i*2.1
        col+=puff(rng.uniform(-3,3),rng.uniform(-3,3),z,r,(FOAM,FOAM2,FOAM3)[i%3])
        if i<9:col+=puff(math.cos(a)*r*.6,math.sin(a)*r*.6,z+10,r*.6,(FOAM2,SPRAY)[i%2],0)   # lumpy flanks
    bones.append(rm.Bone('Column',0,(0,0,0)));c=len(bones)-1
    bones[c].scale+=[(0,.1,.1,.02),(t0,.35,.35,.02),(t0+120,.4,.4,.3),(t0+450,.85,.85,.9),(t0+800,1.0,1.0,1.05),
                     (t0+1500,1.15,1.15,1.0),(t0+2300,1.5,1.5,.55),(t0+3000,1.9,1.9,.18),(t0+3300,.1,.1,.02),(D1,.1,.1,.02)]
    layers.append(rm.Layer(col,rm.BLEND,c,window(t0,t0+3300,.92,fade_out=900)))
    # Darker core: grey water and debris rising inside the column, gone sooner.
    core=[t for z,r in ((20,20),(60,17),(105,14),(150,11)) for t in puff(0,0,z,r,GREY)]
    bones.append(rm.Bone('Core',0,(0,0,0)));k=len(bones)-1
    bones[k].scale+=[(0,.1,.1,.02),(t0,.3,.3,.02),(t0+150,.7,.7,.5),(t0+500,1,1,1),(t0+1300,1.1,1.1,.8),(t0+2000,1.3,1.3,.2),(t0+2100,.1,.1,.02),(D1,.1,.1,.02)]
    layers.append(rm.Layer(core,rm.BLEND,k,window(t0,t0+2100,.7,fade_out=800)))
    # Plume: a broad white cap riding the column top, then collapsing back down and spreading.
    cap=[t for i in range(7) for t in puff(math.cos(i*math.tau/7)*16,math.sin(i*math.tau/7)*16,0,14,(FOAM,FOAM2)[i%2])]+puff(0,0,6,18,FOAM)
    bones.append(rm.Bone('Plume',0,(0,0,262)));pl=len(bones)-1
    bones[pl].translation+=[(0,0,0,-250),(t0,0,0,-250),(t0+450,0,0,-30),(t0+900,0,0,0),(t0+1500,0,0,-12),(t0+2200,0,0,-90),
                            (t0+2900,0,0,-200),(t0+3400,0,0,-245),(D1,0,0,-245)]
    bones[pl].scale+=[(0,.2,.2,.2),(t0,.2,.2,.2),(t0+450,.6,.6,.6),(t0+900,1.0,1.0,.9),(t0+1500,1.3,1.3,1.0),(t0+2200,1.7,1.7,1.0),
                      (t0+2900,2.2,2.2,.8),(t0+3400,2.6,2.6,.3),(D1,2.6,2.6,.3)]
    layers.append(rm.Layer(cap,rm.BLEND,pl,window(t0+250,t0+3500,.88,fade_in=250,fade_out=900)))
    # Spray: clumps thrown out on arcs from up the column, falling back to the sea.
    for i in range(10):
        ang=i*math.tau/10+rng.uniform(-.25,.25);dist=rng.uniform(70,130);z0=rng.uniform(60,200)
        bones.append(rm.Bone(f'Spray{i}',0,(0,0,z0)));s=len(bones)-1
        start=t0+rng.randint(150,450);dur=rng.randint(1500,2200)
        arc(bones[s],start,dur,(math.cos(ang)*dist,math.sin(ang)*dist,-z0),rng.uniform(30,70))
        bones[s].translation.insert(0,(t0,0,0,-z0*.8))
        bones[s].scale+=[(t0,.3,.3,.3),(start,.6,.6,.6),(start+dur//2,1.3,1.3,1.2),(start+dur,1.8,1.8,.6)]
        layers.append(rm.Layer(puff(0,0,0,10,SPRAY)+puff(6,3,-7,7,FOAM2,0),rm.BLEND,s,window(start-100,start+dur,.8,fade_out=500)))
    # Base surge: the falling water rolls outward as a low ring of puffs.
    surge=[t for i in range(12) for t in puff(math.cos(i*math.tau/12)*30,math.sin(i*math.tau/12)*30,8,11,(FOAM,FOAM2)[i%2],0)]
    bones.append(rm.Bone('Surge',0,(0,0,0)));sg=len(bones)-1
    bones[sg].scale+=[(0,.3,.3,.3),(t0+1600,.5,.5,.4),(t0+2600,1.6,1.6,1.0),(t0+3800,2.6,2.6,.6),(t0+4600,3.2,3.2,.2),(D1,3.2,3.2,.2)]
    layers.append(rm.Layer(surge,rm.BLEND,sg,window(t0+1600,t0+4600,.75,fade_in=300,fade_out=1200)))
    # Foam: a filled patch and a bright ring spreading on the surface, lingering to the end.
    bones.append(rm.Bone('Foam',0,(0,0,0)));fm=len(bones)-1
    bones[fm].scale+=[(0,.2,.2,1),(t0,.3,.3,1),(t0+600,1.2,1.2,1),(t0+2500,2.4,2.4,1),(t0+5000,3.4,3.4,1),(D1,3.4,3.4,1)]
    layers.append(rm.Layer(disc(0,28,FOAM3,18,.5),rm.BLEND,fm,window(t0,t0+5400,.7,fade_in=200,fade_out=2000)))
    bones.append(rm.Bone('FoamRing',0,(0,0,0)));fr=len(bones)-1
    bones[fr].scale+=[(0,.2,.2,1),(t0,.3,.3,1),(t0+500,1.4,1.4,1),(t0+2000,3.0,3.0,1),(t0+4800,4.6,4.6,1),(D1,4.6,4.6,1)]
    layers.append(rm.Layer(disc(26,34,RING,24,.6),rm.BLEND,fr,window(t0,t0+4800,.85,fade_out=2400)))
    data=rm.emit('torpedo_hit',layers,bones,EFFECT_SEQ)
    if return_parts:return data,bones,layers
    return data

# ------------------------------------------------------------------ torpedo launch
LAUNCH_DROP=12      # tube decks sit 11.5-14 above the waterline
LAUNCH_REACH=26     # the fish enters the water this far out along +X
def torpedo_launch_mdx():
    t0=D0;rng=random.Random('torpedo_launch')
    bones=[rm.Bone('Root')];layers=[]
    # Muzzle puff: a quick hot pop then grey powder/compressed-air smoke drifting out and up.
    bones.append(rm.Bone('Pop',0,(3,0,1)));p=len(bones)-1
    bones[p].scale+=[(0,.1,.1,.1),(t0,.5,.5,.5),(t0+60,1.3,1.1,1.1),(t0+160,.2,.2,.2),(D1,.2,.2,.2)]
    layers.append(rm.Layer(puff(0,0,0,3.5,SPARK,0)+puff(2,0,0,2,HOT,0),rm.ADD,p,window(t0,t0+160,.9,fade_out=80)))
    for i in range(3):
        bones.append(rm.Bone(f'Puff{i}',0,(2+i*3,rng.uniform(-2,2),1)));s=len(bones)-1
        bones[s].translation+=[(t0,0,0,0),(t0+250,7+i*4,0,2),(t0+1400,14+i*6,rng.uniform(-3,3),12+i*2)]
        bones[s].scale+=[(0,.2,.2,.2),(t0,.3,.3,.3),(t0+250,1.0,1.0,.9),(t0+1400,2.0,2.0,1.8),(D1,2.0,2.0,1.8)]
        layers.append(rm.Layer(puff(0,0,0,5-i*.6,GREY),rm.BLEND,s,window(t0+20*i,t0+1450,.75,fade_out=900)))
    # The fish: a dark body arcing from the tube into the sea.
    bones.append(rm.Bone('Fish',0,(0,0,0)));fi=len(bones)-1
    arc(bones[fi],t0,380,(LAUNCH_REACH,0,-LAUNCH_DROP-2),3,6)
    bones[fi].rotation+=[(t0,*rm.euler(0,0)),(t0+380,*rm.euler(0,35))]
    fish=gi.transform(ships.cylinder(0,0,0,.9,7,0,DARK,6,taper=.5,axis='y'),1,(0,0,0),yaw=90)
    layers.append(rm.Layer(fish,rm.OPAQUE,fi,window(t0,t0+380)))
    # Entry splash: a small white column and spray where it hits, then a foam ring.
    ex,ez=LAUNCH_REACH,-LAUNCH_DROP
    bones.append(rm.Bone('Splash',0,(ex,0,ez)));sp=len(bones)-1
    bones[sp].scale+=[(0,.1,.1,.1),(t0+360,.2,.2,.1),(t0+480,.9,.9,1.0),(t0+800,1.2,1.2,.8),(t0+1250,1.4,1.4,.15),(D1,1.4,1.4,.15)]
    splash=puff(0,0,4,5,FOAM)+puff(0,0,11,3.6,FOAM2)+[t for i in range(5) for t in puff(math.cos(i*1.3)*5,math.sin(i*1.3)*5,3,2.2,SPRAY,0)]
    layers.append(rm.Layer(splash,rm.BLEND,sp,window(t0+360,t0+1250,.85,fade_out=500)))
    bones.append(rm.Bone('Ring',0,(ex,0,ez)));rg=len(bones)-1
    bones[rg].scale+=[(0,.2,.2,1),(t0+380,.3,.3,1),(t0+1500,2.4,2.4,1),(D1,2.4,2.4,1)]
    layers.append(rm.Layer(disc(4,6.5,RING,16,.5),rm.BLEND,rg,window(t0+380,t0+1500,.75,fade_out=700)))
    return rm.emit('torpedo_launch',layers,bones,EFFECT_SEQ)

# ------------------------------------------------------------------ dock launch wake
def launch_wake_mdx():
    """A newly built ship pushed out of the dry dock: stern churn, a widening V of foam
    trailing aft (-X) and bow-wave spray ahead (+X). Origin = ship centre on the water, +X =
    the heading it leaves on; sized for a ~200-unit hull (S_ShipLaunchFx scales it)."""
    t0=D0;rng=random.Random('launch_wake')
    bones=[rm.Bone('Root')];layers=[]
    # Stern churn: a boiling white patch that spreads and thins.
    bones.append(rm.Bone('Churn',0,(-90,0,0)));c=len(bones)-1
    bones[c].scale+=[(0,.3,.3,1),(t0,.4,.4,1),(t0+1500,1.6,1.4,1),(t0+5000,2.4,2.0,1),(D1,2.4,2.0,1)]
    churn=face_up(disc(0,22,FOAM,18,.6))+[t for i in range(7) for t in puff(rng.uniform(-14,14),rng.uniform(-14,14),1,rng.uniform(4,7),FOAM2,0)]
    layers.append(rm.Layer(churn,rm.BLEND,c,window(t0,t0+5200,.8,fade_in=200,fade_out=2600)))
    # Wake V: two foam arms streaming aft from the quarters, spreading outward.
    for side in (-1,1):
        bones.append(rm.Bone(f'Arm{side}',0,(-60,side*20,0)));a=len(bones)-1
        bones[a].translation+=[(t0,0,0,0),(t0+5000,-70,side*45,0)]
        bones[a].scale+=[(0,.3,.3,1),(t0,.4,.4,1),(t0+5000,1.8,1.3,1),(D1,1.8,1.3,1)]
        arm=[]
        for k in range(6):
            x=-k*20;y=side*k*7
            arm+=face_up([((( x-10,y-3,.5),(x+10,y-3,.5),(x+10,y+3,.5)),FOAM3,'foam'),(((x-10,y-3,.5),(x+10,y+3,.5),(x-10,y+3,.5)),FOAM3,'foam')])
        layers.append(rm.Layer(arm,rm.BLEND,a,window(t0+150,t0+5600,.7,fade_in=300,fade_out=3000)))
    # Bow wave: spray thrown off the stem as she gathers way.
    for side in (-1,1):
        bones.append(rm.Bone(f'Bow{side}',0,(95,side*8,2)));b=len(bones)-1
        arc(bones[b],t0+200,900,(10,side*14,0),9,6)
        bones[b].scale+=[(0,.3,.3,.3),(t0+200,.5,.5,.5),(t0+700,1.2,1.2,1.0),(t0+1400,1.5,1.5,.6),(D1,1.5,1.5,.6)]
        layers.append(rm.Layer(puff(0,0,2,5,SPRAY)+puff(3,side*3,5,3.5,FOAM),rm.BLEND,b,window(t0+200,t0+1500,.8,fade_out=600)))
    return rm.emit('launch_wake',layers,bones,EFFECT_SEQ)

# ------------------------------------------------------------------ armour spark
def armor_spark_mdx():
    """Shell shattering or ricocheting on armour: flash, sparks fanning out, a smoke wisp."""
    t0=D0;rng=random.Random('armor_spark')
    bones=[rm.Bone('Root')];layers=[]
    bones.append(rm.Bone('Flash',0,(0,0,0)));f=len(bones)-1
    bones[f].scale+=[(0,.1,.1,.1),(t0,.6,.6,.6),(t0+40,1.6,1.6,1.6),(t0+140,.9,.9,.9),(t0+220,.1,.1,.1),(D1,.1,.1,.1)]
    layers.append(rm.Layer(puff(0,0,0,5,HOT)+puff(0,0,0,7,SPARK),rm.ADD,f,window(t0,t0+220,1.0,fade_out=120)))
    # Sparks: thin bright streaks along their direction of flight, dropping under gravity.
    streak=gi.boxes([(0,0,-.2,2.6,.22,.4,HOT)])+gi.boxes([(-2.4,0,-.15,1.6,.16,.3,SPARK)])
    for i in range(16):
        yaw=i*360/16+rng.uniform(-10,10);elev=rng.uniform(8,65);speed=rng.uniform(22,42)
        ce,se=math.cos(math.radians(elev)),math.sin(math.radians(elev))
        v=(math.cos(math.radians(yaw))*ce*speed,math.sin(math.radians(yaw))*ce*speed,se*speed)
        bones.append(rm.Bone(f'Spark{i}',0,(0,0,0)));s=len(bones)-1
        dur=rng.randint(380,650)
        arc(bones[s],t0,dur,(v[0],v[1],v[2]-14),8,6)
        bones[s].rotation+=[(t0,*rm.euler(0,-elev,yaw)),(t0+dur,*rm.euler(0,min(60,elev*.2+30),yaw))]
        bones[s].scale+=[(0,.1,.1,.1),(t0,1.3,1,1),(t0+int(dur*.6),1.0,.9,.9),(t0+dur,.1,.1,.1),(D1,.1,.1,.1)]
        layers.append(rm.Layer(streak,rm.ADD,s,window(t0,t0+dur,1.0,fade_out=dur//2)))
    bones.append(rm.Bone('Smoke',0,(0,0,2)));sm=len(bones)-1
    bones[sm].translation+=[(t0,0,0,0),(t0+1000,4,2,16),(D1,4,2,16)]
    bones[sm].scale+=[(0,.2,.2,.2),(t0+80,.5,.5,.5),(t0+1000,2.0,2.0,1.6),(D1,2.0,2.0,1.6)]
    layers.append(rm.Layer(puff(0,0,0,5,GREY)+puff(3,1,3,3.6,GREY,0),rm.BLEND,sm,window(t0+60,t0+1000,.6,fade_in=60,fade_out=600)))
    return rm.emit('armor_spark',layers,bones,EFFECT_SEQ)

BUILD={'torpedo':torpedo_mdx,'torpedo_hit':torpedo_hit_mdx,'torpedo_launch':torpedo_launch_mdx,'armor_spark':armor_spark_mdx,'launch_wake':launch_wake_mdx}
def mdx(name):return BUILD[name]()

# ------------------------------------------------------------------ tube positions
TORPEDO_SHIPS=('fletcher','sumner','atlanta','fubuki','kagero','akizuki','mogami','takao','myoko')

def _tube_boxes(name):
    """Torpedo tubes: plain GUN boxes ~0.4 wide, 4-6 long, 0.5 high (torpedoes() and the triple/quintuple sets)."""
    return [b for b in hm.GEOMETRY[name] if b[6]==hm.GUN and .3<=b[3]<=.45 and 3.5<=b[4]<=6.5 and .4<=b[5]<=.55]

def tube_mounts(name):
    """One (x, y, z) per tube mount in engine space: bundle centre, z on top of the tubes."""
    groups=[]
    for b in _tube_boxes(name):
        for g in groups:
            if abs(g[0][1]-b[1])<.01 and abs(g[0][2]-b[2])<.01 and min(abs(o[0]-b[0]) for o in g)<2:g.append(b);break
        else:groups.append([b])
    out=[]
    for g in groups:
        x=sum(b[0] for b in g)/len(g);y=g[0][1];z=g[0][2]+g[0][5]
        out.append((float(round(-y,2)),float(round(x,2)),float(round(z,2))))   # authoring (bow -Y, +X port) -> engine (bow +X)
    return sorted(out)

def _tubes():
    tubes={name:tube_mounts(name) for name in TORPEDO_SHIPS}
    from tools.frontline import models
    source=ships.GENERIC['destroyer'][0]
    box=models.GEOMETRY['destroyer']
    want=max(b[0]+b[3] for b in box)-min(b[0]-b[3] for b in box)
    lo,hi=gi.bounds(ships.triangles(source))
    k=want/(hi[0]-lo[0])
    tubes['destroyer']=[tuple(round(c*k,2) for c in p) for p in tubes[source]]
    return tubes
TUBES=_tubes()
