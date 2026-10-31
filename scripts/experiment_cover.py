"""Generate a compact PNG preview from an experiment archive using the standard library."""
import argparse,json,struct,zlib
from pathlib import Path
from experiment_view import parts


def render(payload,width=512,height=320):
    _,collections=parts(payload)
    elements=collections.get('Elements',collections.get('Objects',collections.get('Planets',[])))
    pixels=bytearray(bytes([239,246,255])*(width*height))
    points={}
    positions=[]
    for item in elements:
        if not isinstance(item,dict):continue
        value=item.get('Position','0,0,0')
        try:
            p=[float(v) for v in value.split(',')] if isinstance(value,str) else [float(value.get('X',0)),float(value.get('Y',0)),float(value.get('Z',0))]
        except (ValueError,AttributeError):p=[0,0,0]
        positions.append((item,p[0],p[2] if len(p)>2 else 0))
    if positions:
        minx,maxx=min(p[1] for p in positions),max(p[1] for p in positions)
        miny,maxy=min(p[2] for p in positions),max(p[2] for p in positions)
        for item,x,y in positions:
            points[item.get('Identifier',item.get('ID',str(len(points))))]=(int(48+(width-96)*(x-minx)/(maxx-minx or 1)),int(48+(height-96)*(y-miny)/(maxy-miny or 1)))
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
    for x,y in points.values():
        for dx in range(-10,11):
            for dy in range(-10,11):
                if dx*dx+dy*dy<=100:dot(x+dx,y+dy,(15,23,42))
    def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    raw=b''.join(b'\0'+pixels[y*width*3:(y+1)*width*3] for y in range(height))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('archive',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise FileExistsError('Choose a new output filename')
    data=render(json.loads(args.archive.read_text(encoding='utf-8-sig')))
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(data)
    print(json.dumps({'cover':str(args.output.resolve()),'bytes':len(data)}))
