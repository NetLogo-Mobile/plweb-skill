"""Generate a compact PNG preview from an experiment archive using the standard library."""
import argparse,json,struct,zlib,math
from pathlib import Path
from experiment_view import parts


def project(elements,width=800,height=600):
    positions=[]
    for item in elements:
        if not isinstance(item,dict):continue
        value=item.get('Position','0,0,0')
        try:
            if isinstance(value,str):p=[float(v) for v in value.split(',')];x,z=p[:2]
            else:x,z=float(value.get('X',0)),float(value.get('Z',0))
            if not math.isfinite(x) or not math.isfinite(z):continue
        except (ValueError,AttributeError,TypeError):continue
        positions.append((item,x,z))
    if not positions:return []
    minx,maxx=min(p[1] for p in positions),max(p[1] for p in positions)
    minz,maxz=min(p[2] for p in positions),max(p[2] for p in positions)
    scale=min((width-128)/(maxx-minx or 1),(height-128)/(maxz-minz or 1))
    return [(item,round(width/2+(x-(minx+maxx)/2)*scale),round(height/2-(z-(minz+maxz)/2)*scale)) for item,x,z in positions]


def render(payload,width=800,height=600):
    _,collections=parts(payload)
    elements=collections.get('Elements',collections.get('Objects',collections.get('Planets',[])))
    pixels=bytearray(bytes([239,246,255])*(width*height))
    points={}
    positions=project(elements,width,height)
    for item,x,y in positions:points[item.get('Identifier',item.get('ID',str(len(points))))]=(x,y)
    def dot(x,y,color):
        if 0<=x<width and 0<=y<height:pixels[(y*width+x)*3:(y*width+x)*3+3]=bytes(color)
    def line(a,b,color):
        steps=max(abs(b[0]-a[0]),abs(b[1]-a[1]),1)
        for t in range(steps+1):
            x,y=int(a[0]+(b[0]-a[0])*t/steps),int(a[1]+(b[1]-a[1])*t/steps)
            for dx in range(-1,2):
                for dy in range(-1,2):dot(x+dx,y+dy,color)
    for wire in collections.get('Wires',[]):
        if isinstance(wire,dict) and wire.get('Source') in points and wire.get('Target') in points:line(points[wire['Source']],points[wire['Target']],(59,130,246))
    digits=['111101101101111','010110010010111','111001111100111','111001111001111','101101111001001','111100111001111','111100111101111','111001001001001','111101111101111','111101111001111']
    for number,(item,x,y) in enumerate(positions,1):
        model=str(item.get('ModelID','')).lower();color=(15,23,42)
        if any(name in model for name in ('charge','planet','earth','sun','instrument')):
            for angle in range(0,360,3):dot(round(x+13*math.cos(math.radians(angle))),round(y+13*math.sin(math.radians(angle))),color)
        elif 'resistor' in model:
            nodes=[(x-18,y),(x-12,y-8),(x-6,y+8),(x,y-8),(x+6,y+8),(x+12,y-8),(x+18,y)]
            for a,b in zip(nodes,nodes[1:]):line(a,b,color)
        else:
            for a,b in [((x-14,y-11),(x+14,y-11)),((x+14,y-11),(x+14,y+11)),((x+14,y+11),(x-14,y+11)),((x-14,y+11),(x-14,y-11))]:line(a,b,color)
        label=str(number)
        for offset,char in enumerate(label):
            for i,pixel in enumerate(digits[int(char)]):
                if pixel=='1':
                    for dx in range(2):
                        for dy in range(2):dot(x-len(label)*4+offset*8+(i%3)*2+dx,y+18+(i//3)*2+dy,color)
    def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    raw=b''.join(b'\0'+pixels[y*width*3:(y+1)*width*3] for y in range(height))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('archive',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise FileExistsError('Choose a new output filename')
    data=render(json.loads(args.archive.read_text(encoding='utf-8-sig')))
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(data)
    print(json.dumps({'cover':str(args.output.resolve()),'bytes':len(data)}))
