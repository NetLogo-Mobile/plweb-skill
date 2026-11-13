"""Check complete image bytes before requesting an upload credential."""
import struct,zlib

def validate_image(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        if len(data)<45 or data[8:16]!=b'\0\0\0\rIHDR':raise ValueError('Invalid PNG header')
        offset=8
        has_data=False
        while offset+12<=len(data):
            size=struct.unpack('!I',data[offset:offset+4])[0];end=offset+12+size
            if end>len(data):break
            kind=data[offset+4:offset+8]
            if kind==b'IDAT':has_data=True
            expected=struct.unpack('!I',data[end-4:end])[0]
            if zlib.crc32(data[offset+4:end-4])&0xffffffff!=expected:raise ValueError('PNG checksum mismatch; read the original image again')
            if kind==b'IEND' and size==0 and end==len(data) and has_data:return
            offset=end
    elif data.startswith(b'\xff\xd8\xff') and data.endswith(b'\xff\xd9'):return
    elif data[:4]==b'RIFF' and data[8:12]==b'WEBP' and len(data)>=12 and struct.unpack('<I',data[4:8])[0]+8==len(data):return
    raise ValueError('Incomplete or invalid image bytes; regenerate Base64 from the original file without manual copying')


def assess_png(data):
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):return None
    width,height,depth,kind,_,_,interlace=struct.unpack('!IIBBBBB',data[16:29])
    channels={0:1,2:3,4:2,6:4}.get(kind)
    if not channels or depth!=8 or interlace or height*(1+width*channels)>32000000:return None
    chunks=[];offset=8
    while offset+12<=len(data):
        size=struct.unpack('!I',data[offset:offset+4])[0]
        if data[offset+4:offset+8]==b'IDAT':chunks.append(data[offset+8:offset+8+size])
        offset+=size+12
    inflater=zlib.decompressobj();raw=inflater.decompress(b''.join(chunks),height*(1+width*channels)+1)
    stride=width*channels
    if len(raw)!=height*(stride+1):return None
    previous=bytearray(stride);first=None;uniform=True;transparent=True
    for y in range(height):
        row=bytearray(raw[y*(stride+1)+1:(y+1)*(stride+1)]);filter_type=raw[y*(stride+1)]
        if filter_type>4:return None
        for i in range(stride):
            a=row[i-channels] if i>=channels else 0;b=previous[i];c=previous[i-channels] if i>=channels else 0
            p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c);paeth=a if pa<=pb and pa<=pc else b if pb<=pc else c
            row[i]=(row[i]+(0,a,b,(a+b)//2,paeth)[filter_type])&255
        for x in range(width):
            pixel=row[x*channels:(x+1)*channels];alpha=pixel[-1] if kind in (4,6) else 255
            rgb=pixel[:3] if kind in (2,6) else [pixel[0]]*3
            color=tuple((v*alpha+255*(255-alpha)+127)//255 for v in rgb)
            if first is None:first=color
            elif color!=first:uniform=False
            if alpha:transparent=False
        previous=row
    return {'width':width,'height':height,'uniform':uniform,'allTransparent':transparent}
