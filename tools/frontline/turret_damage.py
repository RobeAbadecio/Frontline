"""Knocked-out main-battery turrets: '<turret>_broken' variants of every battery mount model.

The RTS logic (S_NavalMountBroken, s_naval.c) swaps a mount's model to its broken variant.
Each variant keeps the ship condition sequence table (ship_states.SEQUENCES) because a mount
plays its ship's frame; it is scorched (dark, the team band kept), its barrels droop, a thin
smoke wisp rises from it, and it neither recoils nor flashes. Original MIT geometry.
"""
import math

from tools.frontline import gltf_import as gi, rich_mdx as rm, ship_states, ships

TURRETS=('naval_triple','naval_twin','yamato_turret','yamato_turret_aa')
SEQUENCES=ship_states.SEQUENCES
DROOP_DEG=14
SMOKE=(78,76,72);SMOKE2=(112,110,104)

def broken(name):return name+'_broken'

def barrels(tris):
    """The barrels, as ship_states.turret_mdx splits them: everything well forward of centre."""
    hi=gi.bounds(tris)[1][0]
    return [t for t in tris if min(p[0] for p in t[0])>hi*.35]

def _scorch(colour):
    if colour==gi.TEAM:return colour
    r,g,b=colour
    return (int(r*.34)+14,int(g*.3)+11,int(b*.27)+9)

def triangles(name):
    """Engine-frame turret (barrels +X) scorched, with the barrels pitched down at their roots."""
    tris=ships.triangles(name);lo,hi=gi.bounds(tris)
    guns=barrels(tris);root=hi[0]*.35
    z0=sum(p[2] for t in guns for p in t[0])/max(1,3*len(guns))
    c,s=math.cos(math.radians(DROOP_DEG)),math.sin(math.radians(DROOP_DEG))
    def droop(p):
        x,y,z=p;dx,dz=x-root,z-z0
        return (root+dx*c+dz*s,y,z0-dx*s+dz*c) if x>root else p
    # Vertex-wise: barrels that start inside the house bend at the trunnion line, tips stay on.
    return [(tuple(droop(p) for p in t[0]),_scorch(t[1]),t[2]) for t in tris]

def mdx(name):
    base=name[:-len('_broken')]
    tris=triangles(base);lo,hi=gi.bounds(tris)
    team=[t for t in tris if t[1]==gi.TEAM];plain=[t for t in tris if t[1]!=gi.TEAM]
    bones=[rm.Bone('Turret')];layers=[rm.Layer(plain,rm.OPAQUE,0),rm.Layer(team,rm.TEAMCOL,0)]
    windows=[(a,b) for n,a,b,*_ in SEQUENCES if not n.startswith('Decay')]
    # Two smoke wisps rising and spreading over every sequence (each loop restarts the rise).
    for k,(dx,size) in enumerate(((-.1,4.0),(.25,3.0))):
        bones.append(rm.Bone(f'Smoke{k}',0,(hi[0]*dx,0,hi[2])));sid=len(bones)-1
        for a,b in windows:
            mid=(a+b)//2
            bones[sid].translation+=[(a,0,0,0),(mid,-3-k*2,0,7),(b,-7-k*3,0,15)]
            bones[sid].scale+=[(a,.5,.5,.5),(mid,1.2,1.2,1.1),(b,1.9,1.9,1.6)]
        layers.append(rm.Layer(ship_states.puff(0,0,0,size,SMOKE if k==0 else SMOKE2),rm.BLEND,sid,[(0,.55),(ship_states.END,.55)]))
    return rm.emit(name,layers,bones,[(n,a,b,speed,once) for n,a,b,speed,once,*_ in SEQUENCES])
