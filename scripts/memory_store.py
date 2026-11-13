"""Local, account-scoped community notes; bounded search previews and explicit reads."""
import json,os,re,sqlite3,time,uuid
from contextlib import contextmanager
from pathlib import Path

def check_note(key,title,content,tags):
    for name,value,maximum in [('key',key,120),('title',title,120),('content',content,2000)]:
        if not isinstance(value,str) or not value.strip() or len(value)>maximum:raise ValueError(f'{name}: nonempty string, at most {maximum} characters')
    if not isinstance(tags,list) or len(tags)>8 or any(not isinstance(t,str) or not t.strip() or len(t)>40 for t in tags):raise ValueError('tags: at most 8 strings of 1..40 characters')
    text=title+'\n'+content
    if re.search(r'(?:password|authcode|x-api-token|x-api-authcode|authorization|token|密码)\s*[:=：]\s*\S{8,}',text,re.I) or re.search(r'[A-Za-z0-9+/]{160,}={0,2}',text):raise ValueError('Do not store credentials, Base64 files or complete models in notes')

class MemoryStore:
    def __init__(self,path=None):
        if path is None:
            base=Path(os.environ['LOCALAPPDATA']) if os.name=='nt' else Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))
            path=base/'plweb-skill'/'memory.sqlite3'
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self._db() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,domain TEXT NOT NULL,account_id TEXT NOT NULL,note_key TEXT NOT NULL,
                title TEXT NOT NULL,content TEXT NOT NULL,tags TEXT NOT NULL,target_id TEXT,target_type TEXT,
                revision INTEGER NOT NULL,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,
                UNIQUE(domain,account_id,note_key));
                CREATE INDEX IF NOT EXISTS notes_scope_time ON notes(domain,account_id,updated_at DESC,id DESC);''')

    @contextmanager
    def _db(self):
        db=sqlite3.connect(self.path,timeout=10);db.row_factory=sqlite3.Row
        try:
            with db:yield db
        finally:db.close()

    @staticmethod
    def _item(row,full=False):
        value=dict(row);value['key']=value.pop('note_key');value['tags']=json.loads(value['tags'])
        if not full:value['preview']=value.pop('content')[:200]
        return value

    def put(self,key,title,content,*,account_id='shared',domain='physics-api-cn.turtlesim.com',tags=None,target_id=None,target_type=None):
        raw_tags=[] if tags is None else tags;check_note(key,title,content,raw_tags);tags=list(dict.fromkeys(raw_tags))
        if not isinstance(account_id,str) or not account_id or len(account_id)>100:raise ValueError('account_id must be a nonempty string of at most 100 characters')
        if domain not in ('physics-api-cn.turtlesim.com','physics-api-us.turtlesim.com'):raise ValueError('Unknown API region')
        if target_id is not None and (not isinstance(target_id,str) or len(target_id)>100):raise ValueError('target_id too long')
        if target_type not in (None,'User','Experiment','Discussion'):raise ValueError('Unknown target_type')
        now=int(time.time()*1000)
        with self._db() as db:
            db.execute('''INSERT INTO notes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(domain,account_id,note_key) DO UPDATE SET title=excluded.title,content=excluded.content,
                tags=excluded.tags,target_id=excluded.target_id,target_type=excluded.target_type,
                revision=notes.revision+1,updated_at=MAX(notes.updated_at+1,excluded.updated_at)''',
                (str(uuid.uuid4()),domain,account_id,key.strip(),title.strip(),content.strip(),json.dumps(tags,ensure_ascii=False),target_id,target_type,1,now,now))
            row=db.execute('SELECT * FROM notes WHERE domain=? AND account_id=? AND note_key=?',(domain,account_id,key.strip())).fetchone()
        value=self._item(row);value.pop('preview');return value

    def search(self,query='',*,account_id='shared',domain='physics-api-cn.turtlesim.com',all_accounts=False,target_id=None,limit=5,cursor=None):
        if isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=10:raise ValueError('limit must be 1..10')
        if not isinstance(query,str) or len(query)>200:raise ValueError('query must be at most 200 characters')
        conditions=['domain=?'];values=[domain]
        if not all_accounts:conditions.append('account_id=?');values.append(account_id)
        if target_id:conditions.append('target_id=?');values.append(target_id)
        for word in list(dict.fromkeys(query.split()))[:8]:
            pattern='%'+word.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
            conditions.append("(title LIKE ? ESCAPE '\\' OR content LIKE ? ESCAPE '\\' OR tags LIKE ? ESCAPE '\\')");values.extend([pattern]*3)
        if cursor:
            if not isinstance(cursor,str) or len(cursor)>300:raise ValueError('Invalid memory cursor')
            try:stamp,note_id=json.loads(cursor)
            except (ValueError,TypeError):raise ValueError('Invalid memory cursor') from None
            if not isinstance(stamp,int) or not isinstance(note_id,str):raise ValueError('Invalid memory cursor')
            conditions.append('(updated_at<? OR (updated_at=? AND id<?))');values.extend([stamp,stamp,note_id])
        with self._db() as db:rows=db.execute('SELECT * FROM notes WHERE '+' AND '.join(conditions)+' ORDER BY updated_at DESC,id DESC LIMIT ?',values+[limit+1]).fetchall()
        more=len(rows)>limit;rows=rows[:limit]
        return {'items':[self._item(r) for r in rows],'returned':len(rows),'next_cursor':json.dumps([rows[-1]['updated_at'],rows[-1]['id']]) if more and rows else None}

    def read(self,note_ids):
        if not isinstance(note_ids,list) or not 1<=len(note_ids)<=5 or any(not isinstance(i,str) for i in note_ids):raise ValueError('Read 1..5 note IDs')
        with self._db() as db:rows=db.execute('SELECT * FROM notes WHERE id IN ('+','.join('?' for _ in note_ids)+')',note_ids).fetchall()
        by_id={r['id']:r for r in rows};return {'items':[self._item(by_id[i],True) for i in dict.fromkeys(note_ids) if i in by_id]}

    def delete(self,note_ids):
        if not isinstance(note_ids,list) or not 1<=len(note_ids)<=20 or any(not isinstance(i,str) for i in note_ids):raise ValueError('Delete 1..20 note IDs')
        with self._db() as db:result=db.execute('DELETE FROM notes WHERE id IN ('+','.join('?' for _ in note_ids)+')',note_ids)
        return {'deleted':result.rowcount}
