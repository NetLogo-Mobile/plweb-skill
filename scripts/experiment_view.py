"""Inspect experiment JSON on disk without emitting a complete model into chat."""
import argparse
from collections import Counter
import json
from pathlib import Path

def _parsed(value):
    return json.loads(value) if isinstance(value,str) else value

def parts(payload):
    if not isinstance(payload,dict):raise ValueError('Expected an experiment object')
    data=_parsed(payload.get('Data',payload))
    if not isinstance(data,dict):raise ValueError('Unsupported experiment structure')
    data=data.get('Experiment',data)
    if not isinstance(data,dict) or data.get('StatusSave') is None:raise ValueError('StatusSave unavailable; model not parsed')
    state=_parsed(data['StatusSave'])
    if not isinstance(state,dict):raise ValueError('StatusSave is not a model object')
    collections={}
    for key,value in state.items():
        if isinstance(value,list):collections[key]=value
        elif isinstance(value,dict) and isinstance(value.get('$values'),list):collections[key]=value['$values']
    return data,collections

def compact(value,depth=0):
    if isinstance(value,str):return {'text':value[:600],'truncated':True,'originalLength':len(value)} if len(value)>600 else value
    if not isinstance(value,(dict,list)):return value
    if depth>=3:return {'omitted':True,'size':len(value),'type':type(value).__name__}
    if isinstance(value,list):return {'items':[compact(v,depth+1) for v in value[:10]],'total':len(value),'truncated':len(value)>10}
    return {**{k:compact(v,depth+1) for k,v in list(value.items())[:24]},**({'__omittedFieldCount':len(value)-24} if len(value)>24 else {})}

def overview(payload):
    data,collections=parts(payload)
    elements=collections.get('Elements',collections.get('Objects',collections.get('Planets',[])))
    counts=Counter(str(item.get('ModelID',item.get('Type','unknown'))) for item in elements if isinstance(item,dict))
    return {'mode':'overview','id':data.get('ID'),'type':data.get('Type'),'title':str(data.get('Subject',''))[:200],
            'collections':[{'name':name[:200],'count':len(items)} for name,items in list(collections.items())[:40]],
            'collectionNamesTruncated':any(len(name)>200 for name in collections),
            'collectionsOmitted':max(0,len(collections)-40),
            'modelTypes':[{'model':compact(name),'count':count} for name,count in counts.most_common(20)],
            'modelTypesOmitted':max(0,len(counts)-20),
            'sample':[compact({k:item.get(k) for k in ('Identifier','ID','ModelID','Position')}) for item in elements[:2] if isinstance(item,dict)],'rawIncluded':False}

def page(payload,collection,offset=0,limit=20,fields=None):
    if isinstance(offset,bool) or not isinstance(offset,int) or offset<0 or isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=20:raise ValueError('offset >= 0; limit 1..20')
    _,collections=parts(payload)
    if collection not in collections:raise ValueError('Unknown collection; inspect overview first')
    items=collections[collection]
    result=[]
    for item in items[offset:offset+limit]:
        source={key:item[key] for key in fields if key in item} if fields and isinstance(item,dict) else item
        view=compact(source)
        text=json.dumps(view,ensure_ascii=False)
        result.append({'preview':text[:2400],'truncated':True,'originalPreviewLength':len(text)} if len(text)>3000 else view)
    return {'mode':'page','collection':collection,'offset':offset,'returned':len(result),'total':len(items),'nextOffset':offset+len(result) if offset+len(result)<len(items) else None,'items':result,'rawIncluded':False}

def read_file(path,max_bytes=268435456):
    path=Path(path)
    if path.stat().st_size>max_bytes:raise ValueError('File exceeds local processing limit; use a streaming file processor')
    with path.open(encoding='utf-8-sig') as stream:return json.load(stream)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('path',type=Path)
    parser.add_argument('--collection')
    parser.add_argument('--offset',type=int,default=0)
    parser.add_argument('--limit',type=int,default=20)
    parser.add_argument('--fields',nargs='*')
    args=parser.parse_args()
    payload=read_file(args.path)
    result=page(payload,args.collection,args.offset,args.limit,args.fields) if args.collection else overview(payload)
    print(json.dumps(result,ensure_ascii=False))
