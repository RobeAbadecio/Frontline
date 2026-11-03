"""Original vector-drawn Emberfield art, rasterized offline with Pillow.

No runtime dependency. Assets use a restrained bronze, slate and ivory palette.
"""
from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

ASSETS=Path(__file__).with_name('assets')
BRONZE=(181,139,78,255)
IVORY=(241,227,189,255)
BLUE=(126,193,207,255)

def font(size):return ImageFont.truetype(str(ASSETS/'fonts/DejaVuSans.ttf'),size)

def icon(symbol,disabled=False):
    original=symbol
    aliases={'ranger':'patrol','skylark':'move','siege':'attack','mender':'repair','marshal':'guard','seer':'spell','tower':'beacon','bastion':'hold','sanctum':'pylon','roost':'move','workshop':'forge'}
    symbol=aliases.get(symbol,symbol)
    # 2x vector rasterization keeps diagonals smooth at high-DPI HUD sizes.
    k=2;n=256
    im=Image.new('RGBA',(n*k,n*k));d=ImageDraw.Draw(im)
    def poly(p,fill=IVORY):d.polygon([(int(x*k),int(y*k)) for x,y in p],fill=fill)
    def line(p,fill=IVORY,w=9):d.line([(int(x*k),int(y*k)) for x,y in p],fill=fill,width=int(w*k),joint='curve')
    def rect(b,fill,outline=None,w=1,r=0):d.rounded_rectangle(tuple(int(v*k) for v in b),radius=r*k,fill=fill,outline=outline,width=w*k)
    for y in range(n*k):
        t=y/(n*k);c=tuple(int(a*(1-t)+b*t) for a,b in zip((54,67,72),(17,26,33)))
        d.line((0,y,n*k,y),fill=(*c,255))
    rect((3,3,252,252),(13,18,23),BRONZE,3,15)
    rect((10,10,245,245),(35,46,52),(91,90,73),2,10)
    rect((19,19,236,236),(23,35,42),(51,63,64),1,5)
    # subtle radial light, not noisy repeated squares
    for j in range(8):
        d.ellipse(((36+j*8)*k,(32+j*8)*k,(220-j*8)*k,(216-j*8)*k),fill=(26+j,39+j,47+j,255))
    for x,y in [(17,17),(239,17),(17,239),(239,239)]:d.ellipse(((x-3)*k,(y-3)*k,(x+3)*k,(y+3)*k),fill=BRONZE)
    gold=(223,177,97,255);muted=(106,146,154,255)
    if symbol=='move':
        poly([(58,118),(132,118),(132,67),(205,128),(132,189),(132,140),(58,140)])
        line([(61,165),(92,165)],gold,5)
    elif symbol in ('attack','guard'):
        poly([(73,185),(86,197),(192,79),(195,52),(168,60)],(184,207,210,255))
        poly([(93,166),(101,174),(186,75),(190,60)],IVORY)
        line([(69,149),(117,191)],gold,12);line([(61,202),(87,174)],gold,13)
        if symbol=='guard':poly([(39,60),(81,47),(115,62),(106,114),(79,140),(48,111)],gold)
    elif symbol=='stop':
        poly([(88,58),(168,58),(201,91),(201,169),(168,202),(88,202),(55,169),(55,91)],gold)
        rect((94,83,113,177),IVORY,r=2);rect((140,83,159,177),IVORY,r=2)
    elif symbol=='hold':
        poly([(127,48),(196,72),(186,153),(128,207),(69,153),(59,72)],gold)
        poly([(128,66),(176,83),(168,145),(128,180),(87,144),(79,83)],(30,48,58,255))
        line([(128,85),(128,161)],IVORY,10);line([(99,119),(157,119)],IVORY,10)
    elif symbol=='patrol':
        d.arc((59*k,59*k,197*k,197*k),205,355,fill=IVORY,width=10*k)
        d.arc((59*k,59*k,197*k,197*k),25,175,fill=gold,width=10*k)
        poly([(190,84),(207,132),(164,123)]);poly([(66,172),(49,124),(92,133)],gold)
    elif symbol in ('build','repair','surveyor','upgrade'):
        line([(74,192),(165,90)],gold,19)
        poly([(128,62),(151,42),(208,94),(186,118),(166,101),(150,120),(123,96),(143,78)])
        if symbol in ('repair','surveyor'):
            line([(67,71),(178,188)],muted,14)
            poly([(47,55),(54,88),(77,100),(97,87),(95,63),(78,45),(81,68),(66,78)],IVORY)
        if symbol=='upgrade':poly([(51,126),(72,126),(72,93),(93,93),(61,51),(30,93),(51,93)],gold)
    elif symbol=='gather':
        poly([(57,167),(98,76),(141,54),(179,89),(202,174),(156,197),(87,194)],gold)
        poly([(98,76),(111,140),(141,54),(161,139),(179,89),(202,174),(156,197),(111,140),(87,194),(57,167)],(157,121,66,255))
        line([(111,140),(156,197)],IVORY,3)
    elif symbol=='cancel':
        line([(74,73),(183,183)],gold,16);line([(183,73),(74,183)],gold,16)
    elif symbol in ('beacon','forge','pylon','ore'):
        if symbol=='ore':
            poly([(55,184),(76,100),(107,129),(130,48),(162,108),(185,84),(207,184)],BLUE)
            line([(130,48),(132,181)],IVORY,4)
        else:
            rect((48,184,208,204),gold);rect((63,107,193,184),(145,154,149,255))
            if symbol=='forge':
                poly([(47,110),(128,57),(207,110)],gold);rect((161,46,185,98),IVORY)
                d.ellipse((100*k,136*k,153*k,195*k),fill=(16,26,32,255));poly([(113,181),(123,146),(130,170),(144,158),(143,181)],gold)
            else:
                rect((93,77,163,184),(172,183,174,255));rect((83,68,173,86),gold)
                poly([(128,32),(153,54),(128,104),(103,54)],BLUE)
                line([(105,123),(151,123)],gold,6)
    elif symbol=='spell':
        poly([(140,40),(78,132),(124,132),(101,211),(180,106),(135,106)],BLUE)
    elif symbol=='inventory':
        rect((65,88,193,196),gold,IVORY,3,12);line([(91,88),(91,57),(164,57),(164,88)],IVORY,10)
        line([(82,118),(177,118)],(88,64,39,255),5)
    elif symbol=='group':
        for x,y in [(75,91),(179,91),(128,125)]:
            d.ellipse(((x-20)*k,(y-40)*k,(x+20)*k,y*k),fill=IVORY if x==128 else gold)
            rect((x-30,y+5,x+30,y+66),IVORY if x==128 else gold,r=12)
    elif symbol=='camera':
        line([(65,102),(65,64),(104,64)],gold,9);line([(153,64),(191,64),(191,103)],gold,9)
        line([(65,155),(65,193),(104,193)],gold,9);line([(153,193),(191,193),(191,155)],gold,9)
        d.ellipse((99*k,99*k,157*k,157*k),outline=IVORY,width=8*k)
    elif symbol=='supply':
        poly([(64,182),(89,89),(126,54),(166,89),(193,182)],IVORY)
        line([(126,54),(126,182)],gold,6);line([(52,183),(204,183)],gold,8)
    elif symbol=='timber':
        for y in (95,134,173):line([(72,y),(181,y-31)],gold,27)
    else:raise ValueError(symbol)
    if original in aliases:
        rect((81,204,175,234),(14,25,32,255),BRONZE,1,4)
        d.text((128*k,217*k),original[:3].upper(),font=font(18*k),anchor='mm',fill=IVORY)
    im=im.resize((256,256),Image.Resampling.LANCZOS)
    if disabled:
        gray=ImageOps.grayscale(im);gray=ImageOps.colorize(gray,(12,18,23),(113,120,122))
        gray.putalpha(im.getchannel('A'));im=gray
    return im


def panel(width,height,kind='panel'):
    im=Image.new('RGBA',(width,height));d=ImageDraw.Draw(im)
    for y in range(height):
        t=y/max(1,height-1);v=int(5*math.sin(t*math.pi))
        d.line((0,y,width,y),fill=(23+v,31+v,36+v,255))
    d.rectangle((0,0,width-1,height-1),outline=(114,91,58),width=2)
    d.line((2,3,width-3,3),fill=(199,160,97),width=1)
    d.line((2,height-4,width-3,height-4),fill=(8,16,22),width=2)
    # Subtle engraved geometric grain. No full-screen repeating noise.
    for x in range(16,width,64):d.line((x,9,x+20,9),fill=(49,57,58),width=1)
    if kind=='hud':
        for x in (int(width*.19),int(width*.38),int(width*.608)):
            d.line((x,9,x,height-10),fill=(91,77,55),width=2)
            d.line((x+3,9,x+3,height-10),fill=(9,19,25),width=1)
        f=font(max(10,int(height*.052)))
        for x,label in [(0.015,'TACTICAL MAP'),(.218,'SELECTED'),(.39,'UNIT DETAILS'),(.622,'COMMANDS')]:
            d.text((int(width*x),9),label,font=f,fill=(169,150,115))
        # The native portrait layer draws before ConsoleUI. Keep its model and
        # live HP/mana strip unobscured; the rest of the console stays opaque.
        left,right=int(width*.26375),int(width*.368125)
        top=int(height*((.4865-.45)/.15))
        d.rectangle((left-2,top-2,right+2,height-1),outline=(114,91,58),width=2)
        d.rectangle((left,top,right,height-1),fill=(0,0,0,0))
    return im


def terrain():
    # Atlas cells are independent, seamless variants; no painted grid seams.
    size=512
    im=Image.new('RGBA',(size,size));p=im.load()
    for y in range(size):
        for x in range(size):
            u=x%128;v=y%128
            smooth=math.sin(u*math.tau/128+math.cos(v*math.tau/128))*3+math.cos(v*math.tau/64)*2
            noise=((x*37+y*71+x*y*3)%11-5)*.45
            p[x,y]=(int(73+smooth+noise),int(89+smooth+noise),int(57+smooth*.6+noise),255)
    d=ImageDraw.Draw(im)
    for cy in range(4):
        for cx in range(4):
            for i in range(20):
                x=cx*128+(i*53+cx*11)%116+6;y=cy*128+(i*37+cy*9)%116+6
                d.line((x,y,x+2,y-4),fill=(89,105,64,255),width=1)
    return im


def material_atlas():
    im=Image.new('RGBA',(256,256));d=ImageDraw.Draw(im)
    colors=[(144,143,123),(91,104,108),(168,123,63),(89,63,43),(210,188,142),(52,67,73),(79,162,182),(96,118,63)]
    for i,c in enumerate(colors):
        x=(i%4)*64;y=(i//4)*128
        d.rectangle((x,y,x+63,y+127),fill=(*c,255))
        for j in range(1,5):d.line((x+3,y+j*25,x+60,y+j*25),fill=tuple(int(v*.89) for v in c),width=1)
        d.line((x+1,y+1,x+61,y+1),fill=tuple(min(255,int(v*1.15)) for v in c),width=2)
    return im


def blp_bytes(im,mips=False):
    import struct
    levels=[];cur=im.convert('RGBA')
    while True:
        levels.append(cur.tobytes('raw','BGRA'))
        if not mips or cur.size==(1,1):break
        cur=cur.resize((max(1,cur.width//2),max(1,cur.height//2)),Image.Resampling.LANCZOS)
    offsets=[];offset=148
    for data in levels:offsets.append(offset);offset+=len(data)
    pad=lambda a:a+[0]*(16-len(a))
    return b'BLP2'+struct.pack('<I4B2I',1,3,8,0,int(mips),im.width,im.height)+struct.pack('<16I',*pad(offsets))+struct.pack('<16I',*pad([len(v) for v in levels]))+b''.join(levels)
