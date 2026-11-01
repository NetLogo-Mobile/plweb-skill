"""Credential-free batching helpers; supply a secure, fixed-account request adapter."""
from concurrent.futures import ThreadPoolExecutor
import json
from threading import BoundedSemaphore, Lock, Event
from time import monotonic, sleep
from pathlib import Path
from uuid import uuid4

_slots = BoundedSemaphore(2)
_start_lock = Lock()
_next_start = 0.0
_READ_PATHS = {"/Contents/GetLibrary","/Contents/QueryExperiments","/Contents/GetSummary","/Contents/GetExperiment","/Contents/GetWorkspace","/Contents/GetDerivatives","/Contents/GetProfile","/Contents/GetSupporters","/Contents/IsStarred","/Messages/GetComments","/Users/GetUser","/Users/GetRelations"}
_WRITE_PATHS = {"/Contents/SubmitExperiment","/Contents/MoveCategory","/Contents/StarContent","/Contents/RemoveExperiment","/Contents/RestoreExperiment","/Contents/ConfirmExperiment","/Messages/PostComment","/Messages/RemoveComment","/Messages/GetMessages","/Messages/GetMessage","/Messages/SendMessages","/Users/Follow","/Users/Block","/Users/Rename","/Users/ModifyInformation","/Users/SetCover","/Users/Ban","/Users/Unban","/Users/Appoint","/Users/SyncActivities","/Users/ReceiveBonus","/Users/Logout"}
_WRITE_PATHS.update({'/Contents/VisitExperiment','/Contents/InviteCoauthor','/Contents/RemoveCoauthor','/Messages/HandleInvitation','/Users/RequestAvatar','/Users/ConfirmAvatar'})
_WRITE_PATHS.update({'/Contents/SelectExperiment','/Contents/AcknowledgeExperiment'})

def _array(value):
    if isinstance(value, list):
        return value
    return value.get("$values", []) if isinstance(value, dict) else []

def _check_count(value, maximum):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise ValueError(f"count must be an integer from 0 to {maximum}")

class CommunityReads:
    """The adapter handles HTTPS, HTTP/Status checks, credential rotation and redaction."""
    def __init__(self, request):
        self._adapter = request

    def _request(self, path, body):
        global _next_start
        with _slots:
            with _start_lock:
                delay = max(0.0, _next_start - monotonic())
                if delay:
                    sleep(delay)
                _next_start = monotonic() + 0.35
            return self._adapter(path, body)

    def _collect(self, kind, filters, count, cursor=None, page_size=20):
        _check_count(count, 1000 if kind == "comments" else 20)
        items, seen = [], set([cursor] if cursor else [])
        pages, reason = 0, "requested_count"
        deadline = monotonic() + 90
        while len(items) < count:
            if pages >= 200 or monotonic() >= deadline:
                reason = "time_or_page_limit"
                break
            # Either list can include the boundary. Request at least two rows to
            # avoid stopping with only the known boundary when one item is left.
            take = max(2, min(max(2, min(page_size, 20)), count-len(items)+1))
            try:
                if kind == "comments":
                    result = self._request("/Messages/GetComments", {**filters, "CommentID": cursor or "", "Skip": 0, "Take": max(2,take)})
                    raw = result.get("Data", {}).get("Comments")
                else:
                    query = {"Category":"Experiment", "Languages":[], "ExcludeLanguages":[], "Tags":None, "ExcludeTags":None, "ModelTags":None, "ModelID":None, "ParentID":None, "UserID":None, "Special":None, "Days":0, "Sort":0, "ShowAnnouncement":False, **filters, "From":cursor, "Skip":0, "Take":take}
                    result = self._request("/Contents/QueryExperiments", {"Query": query})
                    raw = result.get("Data")
            except Exception as error:
                if not items:
                    raise
                reason = "rate_limited" if getattr(error, "status", None) in (429,503) else "upstream_error"
                break
            pages += 1
            if not isinstance(raw, list) and not (isinstance(raw, dict) and isinstance(raw.get("$values"), list)):
                reason = "invalid_response"
                break
            rows = _array(raw)
            if not rows:
                reason = "exhausted"
                break
            before = len(items)
            for item in rows:
                identifier = item.get("ID") if isinstance(item, dict) else None
                if not isinstance(identifier, str) or not identifier:
                    reason = "invalid_response"
                    break
                if identifier in seen:
                    continue
                seen.add(identifier)
                items.append(item)
                cursor = identifier
                if len(items) == count:
                    break
            if reason == "invalid_response":
                break
            if len(items) == before:
                reason = "no_progress"
                break
        return {"requested":count,"returned":len(items),"complete":len(items)==count,"stopReason":reason,"pages":pages,"nextCursor":cursor,"items":items}

    def fetch_comments(self, target_id, target_type, count, cursor=None, page_size=20):
        if target_type not in ("User","Experiment","Discussion"):
            raise ValueError("Unknown target_type")
        return self._collect("comments", {"TargetID":target_id,"TargetType":target_type}, count, cursor, page_size)

    def fetch_works(self, category, count, user_id=None, tags=None, languages=None, sort=0, cursor=None, page_size=20):
        if category not in ("Experiment","Discussion"):
            raise ValueError("Unknown category")
        return self._collect("works", {"Category":category,"UserID":user_id,"Tags":tags,"Languages":languages or [],"Sort":sort}, count, cursor, page_size)

    def _batch(self, jobs, function):
        halt = Event()
        def run(pair):
            index, job = pair
            if halt.is_set():
                return {"index":index,"ok":False,"skipped":True,"error":"rate_limited"}
            try:
                data = function(job)
                if isinstance(data,dict) and data.get("stopReason") == "rate_limited":
                    halt.set()
                return {"index":index,"ok":True,"data":data}
            except Exception as error:
                if getattr(error,"status",None) in (429,503):
                    halt.set()
                return {"index":index,"ok":False,**(error.as_dict() if hasattr(error,'as_dict') else {"errorType":type(error).__name__,**({'message':str(error)} if isinstance(error,ValueError) else {})})}
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(run, enumerate(jobs)))

    def fetch_comments_batch(self, targets):
        if not targets or len(targets)>1000:
            raise ValueError("A comment batch must have 1 to 1000 targets")
        for target in targets:
            _check_count(target["count"],1000)
        if sum(x["count"] for x in targets)>1000:
            raise ValueError("A comment batch cannot exceed 1000 total comments")
        return self._batch(targets, lambda job:self.fetch_comments(**job))

    def fetch_works_batch(self, queries):
        if not queries or len(queries)>20:
            raise ValueError("A work batch must have 1 to 20 queries")
        for query in queries:
            _check_count(query["count"],20)
        if sum(x["count"] for x in queries)>20:
            raise ValueError("A work batch cannot exceed 20 total works")
        return self._batch(queries, lambda job:self.fetch_works(**job))

    def get_users(self, ids):
        if not ids or len(ids)>20:
            raise ValueError("A user batch must have 1 to 20 IDs")
        ids = list(dict.fromkeys(ids))
        return self._batch(ids, lambda identifier:self._request("/Users/GetUser", {"ID":identifier}))

    def get_users_by_name(self, names):
        """Exact nickname lookup, not fuzzy/global full-text search."""
        if not names or len(names)>20 or any(not isinstance(n,str) or not n for n in names):
            raise ValueError("Provide 1 to 20 exact nicknames")
        return self._batch(list(dict.fromkeys(names)), lambda name:self._request("/Users/GetUser", {"Name":name}))

    def _offset_list(self,path,body,key,count,offset=0,page_size=20):
        _check_count(count,20)
        if not isinstance(offset,int) or isinstance(offset,bool) or offset<0:raise ValueError('offset must be non-negative')
        items,seen,pages=[],set(),0
        reason='requested_count'
        while len(items)<count:
            take=min(max(1,min(page_size,20)),count-len(items))
            result=self._request(path,{**body,'Skip':offset,'Take':take})
            data=result.get('Data');rows=_array(data.get(key) if key and isinstance(data,dict) else data)
            pages+=1
            if not rows:reason='exhausted';break
            before=len(items)
            for row in rows:
                identifier=row.get('ID')
                if identifier and identifier not in seen:items.append(row);seen.add(identifier)
            offset+=len(rows)
            if len(items)==before:reason='no_progress';break
            if len(rows)<take:reason='exhausted';break
        return {'requested':count,'returned':len(items),'complete':len(items)==count,'stopReason':reason,'pages':pages,'nextOffset':offset,'items':items}

    def fetch_supporters(self,summary_id,count=20,category='Experiment',offset=0,page_size=20):
        return self._offset_list('/Contents/GetSupporters',{'Category':category,'ContentID':summary_id},None,count,offset,page_size)

    def fetch_messages(self,count=20,category_id=0,offset=0,page_size=20):
        """Reads the inbox and may reset unread counters; call only for a requested inbox task."""
        return self._offset_list('/Messages/GetMessages',{'CategoryID':category_id,'NoTemplates':False},'Messages',count,offset,page_size)

    def get_available_tags(self, category=None):
        result = self._request("/Users/Authenticate", {"Login":None,"Password":None,"Version":2411,"Device":{"Identifier":"0d1a760b44023875d2123f2cfcb56dad","Language":"Chinese"}})
        raw = result.get("Data",{}).get("ContentTags")
        if not isinstance(raw,list) and not (isinstance(raw,dict) and isinstance(raw.get("$values"),list)):
            raise ValueError("ContentTags missing; do not use a static snapshot")
        tags = _array(raw)
        if not tags or any(not isinstance(t.get("Identifier"),str) or not t["Identifier"] for t in tags):
            raise ValueError("Invalid ContentTags")
        tags = [{**tag,"Flags":_array(tag.get("Flags")),"Conflicts":_array(tag.get("Conflicts"))} for tag in tags]
        selected=[t for t in tags if category is None or category in t['Flags'] or not set(t['Flags'])&{'Experiment','Discussion','Model'}]
        def managed(t):return t['Identifier'].startswith('Type-') or bool(set(t['Flags'])&{'Immutable','EditOnly','Volunteer','Junior','Editor','Administrator','Oldtimer','Emeritus'})
        return {"source":"Authenticate.Data.ContentTags","total":len(tags),"tags":selected,"availableIsPermission":False,"normalTagIdentifiers":[t['Identifier'] for t in selected if not managed(t)],"managedTagIdentifiers":[t['Identifier'] for t in selected if managed(t)],"availabilityNote":"Available是无效的账号权限信号，忽略其true/false，不能据此拒绝交流等普通标签。normalTagIdentifiers用于普通标签选择，组合按Conflicts/Tips匹配；managedTagIdentifiers含系统、管理或编辑限制标签。普通SubmitExperiment不会新增精选或知识库，即使返回200也要读回Tags确认。"}

    def inspect_experiments(self, content_ids, output_dir):
        """Download and process internally. Return only overviews and local file paths."""
        from experiment_view import overview
        if not content_ids or len(content_ids)>20:raise ValueError('At most 20 saved content IDs per batch')
        output_dir=Path(output_dir)
        output_dir.mkdir(parents=True,exist_ok=True)
        def inspect(identifier):
            payload=self._request('/Contents/GetExperiment',{'ContentID':identifier})
            destination=output_dir/(str(uuid4())+'.json')
            with destination.open('x',encoding='utf-8') as stream:json.dump(payload,stream,ensure_ascii=False)
            try:result=overview(payload)
            except (ValueError,TypeError,KeyError):result={'mode':'file_only','reason':'unsupported_structure','rawIncluded':False}
            return {**result,'contentId':identifier,'file':str(destination.resolve())}
        return self._batch(list(dict.fromkeys(content_ids)),inspect)

    def call_batch(self, path, bodies, write=False):
        """Call a documented community path. Authorization and write verification stay with the caller."""
        if not isinstance(write, bool):
            raise ValueError("write must be a boolean")
        if path not in (_WRITE_PATHS if write else _READ_PATHS):
            raise ValueError("Only documented community-relative paths are allowed")
        if path=='/Contents/GetExperiment':raise ValueError('Use inspect_experiments(content_ids, output_dir), then experiment_view.py pages; never emit a full model into chat')
        maximum = 1000 if "Comment" in path else 20
        if not bodies or len(bodies)>maximum:
            raise ValueError(f"Batch limit is {maximum}")
        total = 0
        for body in bodies:
            if not isinstance(body,dict):raise ValueError('Each body must be an object')
            if path in ('/Contents/SelectExperiment','/Contents/AcknowledgeExperiment'):
                if not isinstance(body.get('SummaryID'),str) or not body['SummaryID'] or not isinstance(body.get('Status'),bool) or body.get('Category') not in ('Experiment','Discussion','Model'):raise ValueError('Category, SummaryID and boolean Status are required')
                if path=='/Contents/AcknowledgeExperiment' and body.get('Tag')!='知识库':raise ValueError('AcknowledgeExperiment is reserved for Knowledge Base; Tag must be 知识库')
                if path=='/Contents/SelectExperiment' and 'Tag' in body:raise ValueError('SelectExperiment does not take Tag; use Status to manage Featured')
            if path=='/Messages/SendMessages':
                targets=body.get('TargetID')
                if not isinstance(targets,list) or not targets or len(targets)>20:
                    raise ValueError('A template message batch supports at most 20 target users')
                amount=len(targets)
            elif path=='/Contents/QueryExperiments':
                query=body.get('Query')
                if not isinstance(query,dict):raise ValueError('Query must be an object')
                if query.get('Skip',0)!=0:raise ValueError('Use From and Skip=0 for works')
                amount=query.get('Take',20)
            elif path in ('/Messages/GetComments','/Users/GetRelations','/Contents/GetSupporters','/Messages/GetMessages'):
                if path=='/Messages/GetComments' and body.get('Skip',0)!=0:
                    raise ValueError('Use CommentID and Skip=0 for comments')
                amount=body.get('Take',20)
            else:amount=1
            _check_count(amount, maximum)
            if not amount:raise ValueError('Batch Take must be positive')
            total+=amount
        if total>maximum:
            raise ValueError(f"Batch result count exceeds {maximum}")
        return self._batch(bodies, lambda body:self._request(path,body))
