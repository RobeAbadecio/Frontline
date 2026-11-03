"""Ship status icons for the unit panel status strip (hud_infopanel.c WriteShipStatusFrames):
burning, flooding, a knocked-out turret, listing, dead in the water, critical, docked.

32x32 RGBA, drawn at 4x and reduced for clean edges, on the dark navy frame of the other
Frontline icons (generate.icon) with a coloured rim per kind. Original MIT artwork.
"""
from PIL import Image, ImageDraw

NAMES=('burning','flooding','turret','listing','dead','critical','docked')
S=128   # working size; saved at 32
RIM={'burning':(236,120,40),'flooding':(70,150,230),'turret':(200,200,190),'listing':(220,190,90),
     'dead':(150,150,150),'critical':(220,50,40),'docked':(120,200,140)}

def _frame(d,rim):
    d.rounded_rectangle((2,2,S-3,S-3),radius=18,fill=(24,34,44,255),outline=rim+(255,),width=8)

def _hull(d,cx,cy,w,h,angle=0,colour=(170,176,184)):
    import math
    c,s=math.cos(math.radians(angle)),math.sin(math.radians(angle))
    pts=[(-w,-h*.2),(w*.8,-h*.2),(w,-h*.7),(w*.85,h*.6),(-w*.9,h*.6),(-w,0)]
    d.polygon([(cx+x*c-y*s,cy+x*s+y*c) for x,y in pts],fill=colour+(255,))

def draw(name):
    im=Image.new('RGBA',(S,S),(0,0,0,0));d=ImageDraw.Draw(im);_frame(d,RIM[name])
    if name=='burning':
        _hull(d,64,92,40,22)
        d.polygon([(44,82),(52,40),(62,62),(68,26),(80,58),(88,44),(86,82)],fill=(240,110,30,255))
        d.polygon([(54,82),(60,56),(68,68),(72,48),(78,82)],fill=(255,214,90,255))
    elif name=='flooding':
        _hull(d,64,58,40,22)
        for k,y in enumerate((78,92,106)):
            d.arc((14,y-14,64,y+10),200,340,fill=(110,180,250,255),width=8);d.arc((62,y-14,112,y+10),200,340,fill=(110,180,250,255),width=8)
        d.polygon([(64,22),(76,42),(64,50),(52,42)],fill=(130,200,255,255))
    elif name=='turret':
        d.rounded_rectangle((34,52,94,92),radius=8,fill=(150,154,160,255))
        for y in (60,72,84):d.line((94,y,118,y+10),fill=(120,124,130,255),width=7)   # drooped barrels
        d.line((36,30,92,110),fill=(230,60,40,255),width=12);d.line((92,30,36,110),fill=(230,60,40,255),width=12)
    elif name=='listing':
        d.line((14,96,114,96),fill=(90,150,210,255),width=6)
        _hull(d,64,74,40,22,angle=-18)
        d.line((64,34,84,22),fill=(220,190,90,255),width=6)
    elif name=='dead':
        _hull(d,64,70,42,24,colour=(130,134,140))
        d.line((14,96,114,96),fill=(90,150,210,255),width=6)
        d.ellipse((42,30,62,50),outline=(200,200,200,255),width=6)                   # stopped screw
        d.line((52,30,52,50),fill=(200,200,200,255),width=5);d.line((40,104,88,104),fill=(90,150,210,180),width=4)
    elif name=='critical':
        d.polygon([(64,18),(112,106),(16,106)],fill=(220,50,40,255))
        d.rectangle((58,44,70,80),fill=(255,245,230,255));d.rectangle((58,88,70,98),fill=(255,245,230,255))
    elif name=='docked':
        d.rectangle((20,40,108,50),fill=(150,150,140,255));d.rectangle((20,88,108,98),fill=(150,150,140,255))   # dock walls
        _hull(d,60,69,34,16)
        d.rectangle((98,50,108,88),fill=(120,200,140,255))                                 # shut gate
        for x in (30,50,70,90):d.rectangle((x,34,x+5,40),fill=(200,200,190,255))          # bollards
    return im.resize((32,32),Image.Resampling.LANCZOS)

def all_icons():return {name:draw(name) for name in NAMES}
