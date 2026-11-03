"""Small original silhouettes; two materials at most per instance."""
import struct
import math
P=lambda f,*v:struct.pack('<'+f,*v)
S=lambda s,n:s.encode()[:n].ljust(n,b'\0')
CH=lambda t,b:t.encode()+P('I',len(b))+b
# x,y,z, half-width, half-depth, height, atlas cell (8 = team color).
GEOMETRY={
'surveyor':[(0,0,0,14,11,9,5),(-8,0,9,6,8,24,3),(8,0,9,6,8,24,3),(0,0,32,16,11,23,3),(0,-12,37,12,2,17,8),(0,0,55,9,9,14,4),(0,0,68,14,13,5,2),(-19,0,32,5,6,21,4),(19,0,32,5,6,21,4),(25,0,25,3,3,40,3),(25,0,61,17,5,7,1)],
'guard':[(-9,0,0,8,13,9,5),(9,0,0,8,13,9,5),(-9,0,9,6,9,24,1),(9,0,9,6,9,24,1),(0,0,32,21,13,27,1),(0,-14,37,14,2,20,8),(-24,0,47,8,16,11,2),(24,0,47,8,16,11,2),(0,0,60,12,12,18,1),(0,-13,65,8,2,3,5),(0,0,78,3,11,7,8),(-28,-12,28,4,20,30,2),(-33,-13,34,2,14,17,8),(30,0,23,3,3,42,4),(30,0,53,11,4,4,2)],
'beacon':[(0,0,0,108,103,12,5),(0,0,12,97,91,13,0),(0,0,25,76,72,82,0),(0,0,107,86,82,13,2),(0,0,120,59,56,18,0),(0,0,138,38,35,34,5),(0,0,172,45,42,9,2),(0,0,181,20,20,34,6),(0,-74,47,23,3,47,3),(-78,-77,24,18,15,100,0),(78,-77,24,18,15,100,0),(-78,77,24,18,15,100,0),(78,77,24,18,15,100,0),(-78,-77,124,22,19,11,2),(78,-77,124,22,19,11,2),(-50,-76,79,14,3,32,8),(50,-76,79,14,3,32,8)],
'forge':[(0,0,0,82,77,12,5),(0,0,12,72,64,69,0),(-31,0,81,38,70,16,3),(28,0,81,22,70,16,3),(0,0,97,39,70,12,2),(0,0,109,24,70,10,3),(0,0,119,9,70,8,2),(40,29,80,17,19,81,0),(40,29,161,22,23,9,5),(0,-66,37,26,3,32,5),(0,-70,38,17,2,23,2),(-48,-67,47,11,3,25,8),(-40,-96,12,25,17,23,1)],
'pylon':[(0,0,0,45,45,10,5),(0,0,10,36,36,12,0),(0,0,22,17,17,69,0),(0,0,91,27,27,10,2),(0,0,101,18,18,25,6),(0,-19,43,10,2,29,8)],
'pine':[(0,0,0,13,13,120,3),(0,0,50,60,55,33,7),(0,0,83,46,43,32,7),(0,0,115,33,30,29,7),(0,0,144,19,17,24,7)],
'ore':[(-29,-13,0,47,46,38,5),(29,20,0,39,37,32,0),(-27,-10,25,15,17,61,6),(10,23,19,20,17,106,6),(41,-15,20,14,16,72,6),(8,30,125,12,11,18,4)]}

GEOMETRY.update({
'ranger':GEOMETRY['surveyor'][:7]+[(23,-8,20,3,18,57,3),(26,-8,20,2,2,57,4),(0,0,71,3,12,8,8)],
'skylark':[(0,0,20,17,28,16,1),(0,-34,27,12,12,16,2),(-40,0,26,35,19,5,8),(40,0,26,35,19,5,8),(-72,8,22,13,12,5,4),(72,8,22,13,12,5,4),(0,32,24,8,19,6,2)],
'siege':[(0,0,16,33,48,18,3),(-38,-30,0,8,13,35,5),(38,-30,0,8,13,35,5),(-38,30,0,8,13,35,5),(38,30,0,8,13,35,5),(0,0,34,18,18,22,1),(0,0,56,8,42,9,2),(0,35,63,20,20,5,8)],
'mender':[(0,0,0,19,18,45,4),(0,0,45,13,13,22,4),(0,0,67,10,10,12,1),(0,-19,16,9,3,30,8),(27,0,0,3,3,90,3),(27,0,90,9,9,11,6)],
'marshal':GEOMETRY['guard']+[(0,0,85,6,15,12,2),(0,15,33,23,3,37,8)],
'seer':[(0,0,0,22,20,45,5),(0,-21,5,16,3,35,8),(0,0,45,15,14,24,4),(0,0,69,19,18,7,2),(0,0,76,9,10,15,6),(30,0,0,3,3,105,3),(30,0,105,12,12,14,6)],
 'tower':[(0,0,0,46,46,14,5),(0,0,14,33,33,128,0),(0,-35,70,14,2,40,8),(0,0,142,48,48,13,2),(-40,-40,155,9,9,16,0),(40,-40,155,9,9,16,0),(-40,40,155,9,9,16,0),(40,40,155,9,9,16,0),(0,0,156,7,40,8,3),(0,-24,165,35,4,5,1)],
 'bastion':[(0,0,0,52,52,17,5),(0,0,17,41,41,135,0),(0,-43,65,19,2,53,8),(0,0,152,57,57,15,2),(-31,0,168,6,43,10,1),(31,0,168,6,43,10,1),(0,0,180,12,12,15,6)],
 'sanctum':GEOMETRY['beacon'][:7]+[(-65,-65,20,13,13,130,0),(65,-65,20,13,13,130,0),(0,0,147,25,25,45,6),(0,-76,72,18,3,37,8)],
 'roost':GEOMETRY['forge'][:3]+[(0,0,100,67,60,10,3),(-48,0,110,7,42,55,0),(48,0,110,7,42,55,0),(0,0,165,70,65,9,8)],
 'workshop':GEOMETRY['forge']+[(0,-95,12,48,30,12,3),(0,0,125,12,12,17,8)],
 'bolt':[(0,0,0,2,18,2,2),(0,-18,0,5,6,3,4)]})


def mesh(name, boxes=None, translation=None, scale=None, texture='Emberfield\\Textures\\materials.blp', grid=(4,2)):
    # Root keys: translation (t,z) or (t,x,y,z); scale (t,s) or (t,sx,sy,sz).
    # grid=(columns,rows) of the colour atlas; cell 8 is always the team colour.
    boxes=GEOMETRY[name] if boxes is None else boxes
    lo=[min(v[i]-(v[i+3] if i<2 else 0) for v in boxes) for i in range(3)]
    high=[max(v[i]+v[i+3] for v in boxes) for i in range(3)]
    extent=max(abs(v) for v in lo+high);hi=high[2]
    radius=math.sqrt(sum(max(abs(a),abs(b))**2 for a,b in zip(lo,high)))
    bounds=P('7f',radius,*lo,*high)
    seq=b''.join(S(n,80)+P('2IfIfI',i*1000,(i+1)*1000-1,270 if n=='Walk' else 0,int(n in ['Death','Birth','Decay']),0,0)+bounds for i,n in enumerate(['Stand','Walk','Attack','Death','Birth','Work','Stand Work','Decay']))
    textures=P('I',0)+S(texture,260)+P('I',0)
    textures+=P('I',1)+S('',260)+P('I',0)
    materials=b'';geosets=b''
    for mat in range(2):
        layer=P('I5If',28,0,0x10,mat,0xffffffff,0,1)
        m=P('2I',0,0)+b'LAYS'+P('I',1)+layer
        materials+=P('I',len(m)+4)+m
        verts=[];normals=[];uv=[];indices=[]
        faces=[((0,3,2,1),(0,0,-1)),((4,5,6,7),(0,0,1)),((0,1,5,4),(0,-1,0)),((1,2,6,5),(1,0,0)),((2,3,7,6),(0,1,0)),((3,0,4,7),(-1,0,0))]
        for x,y,z,w,d,h,cell in boxes:
            if (cell==8)!=(mat==1):continue
            corners=[(x-w,y-d,z),(x+w,y-d,z),(x+w,y+d,z),(x-w,y+d,z),(x-w,y-d,z+h),(x+w,y-d,z+h),(x+w,y+d,z+h),(x-w,y+d,z+h)]
            cw,ch=1/grid[0],1/grid[1]
            u,v=(cell%grid[0])*cw,(cell//grid[0])*ch
            coords=[(u+cw*.06,v+ch*.03),(u+cw*.94,v+ch*.03),(u+cw*.94,v+ch*.97),(u+cw*.06,v+ch*.97)] if mat==0 else [(0,0),(1,0),(1,1),(0,1)]
            for f,normal in faces:
                start=len(verts);verts.extend(corners[i] for i in f);normals.extend([normal]*4);uv.extend(coords);indices.extend([start,start+1,start+2,start,start+2,start+3])
        if not verts:continue
        sub=lambda t,c,b:t.encode()+P('I',c)+b
        n=len(verts)
        geo=sub('VRTX',n,b''.join(P('3f',*v) for v in verts))+sub('NRMS',n,b''.join(P('3f',*v) for v in normals))+sub('UVBS',n,b''.join(P('2f',*v) for v in uv))
        geo+=sub('PTYP',1,P('I',4))+sub('PCNT',1,P('I',len(indices)//3))+sub('PVTX',len(indices),P(str(len(indices))+'H',*indices))
        geo+=sub('GNDX',n,bytes(n))+sub('MTGC',1,P('I',1))+sub('UVAS',1,b'')+sub('MATS',1,P('4I',0,mat,0,0)+bounds+P('I',0))
        geosets+=P('I',len(geo)+4)+geo
    track=b''
    vec=lambda k,pad:(k[0],*(k[1:] if len(k)==4 else (pad,pad,k[1]) if pad==0 else (k[1],)*3))
    if translation:
        track+=b'KGTR'+P('3I',len(translation),1,0xffffffff)+b''.join(P('I3f',*vec(k,0)) for k in translation)
    if scale:
        track+=b'KGSC'+P('3I',len(scale),1,0xffffffff)+b''.join(P('I3f',*vec(k,1)) for k in scale)
    bone=P('I',96+len(track))+S('Root',80)+P('3I',0,0xffffffff,256)+track+P('2I',0,0xffffffff)
    distance=max(160,extent*2.8)
    camera=P('I',120)+S('Portrait',80)+P('3f3f3f',distance,-distance,extent*.9,.55,4000,1,0,0,hi*.45)
    return b'MDLX'+CH('VERS',P('I',800))+CH('MODL',S('Emberfield '+name,80)+S('',260)+bounds+P('I',100))+CH('SEQS',seq)+CH('TEXS',textures)+CH('MTLS',materials)+CH('GEOS',geosets)+CH('BONE',bone)+CH('PIVT',P('3f',0,0,0))+CH('CAMS',camera)
