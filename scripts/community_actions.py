"""Publishing, image uploads and invitation actions; all requests stay in one account."""
import base64
import binascii
import hashlib
import json
import mimetypes
from pathlib import Path
import time
from urllib.parse import urlsplit
from urllib.request import Request, build_opener
import uuid
from community_client import CommunityError, _NoRedirect, redact
from image_integrity import validate_image,assess_png

MAX_AVATAR_BYTES = 1024 * 1024
MAX_COVER_BYTES = 8 * 1024 * 1024
STATIC_BASE = 'https://physics-lab.oss-cn-hongkong.aliyuncs.com'

def validate_archive_model(archive):
    if not isinstance(archive,dict) or not isinstance(archive.get('Experiment'),dict):raise ValueError('Expected a .plsav object containing Experiment')
    experiment=archive['Experiment']
    if experiment.get('Type') not in (0,3,4) or isinstance(experiment.get('Type'),bool):raise ValueError('Experiment.Type must be 0, 3 or 4')
    try:state=json.loads(experiment['StatusSave'])
    except (KeyError,ValueError,TypeError):raise ValueError('Experiment.StatusSave must be a model JSON string') from None
    elements=state.get('Elements') if isinstance(state,dict) else None
    if not isinstance(elements,(list,dict)):raise ValueError('StatusSave.Elements must be an array or object dictionary')
    values=elements.get('$values',list(elements.values())) if isinstance(elements,dict) else elements
    if not isinstance(values,list) or any(not isinstance(v,dict) for v in values):raise ValueError('Elements must contain model objects')


def upload_target(token):
    if token.get('RequestHost'):
        path=token.get('RequestURI')
    else:
        try:path=json.loads(base64.b64decode(token['Policy']))['save-key']
        except (ValueError,KeyError,TypeError,binascii.Error):raise ValueError('Upload policy has no concrete save-key') from None
    if not isinstance(path,str) or not path or any(x in path for x in ('..','?', '#', '://', '{', '}')):raise ValueError('Invalid upload target')
    return '/'+path.lstrip('/')


def verify_image(path,allow_blank_image=False):
    url=STATIC_BASE+path
    try:
        with build_opener(_NoRedirect()).open(Request(url,headers={'Cache-Control':'no-cache'}),timeout=25) as response:
            header=response.read(MAX_COVER_BYTES+1)
            valid=header.startswith(b'\x89PNG\r\n\x1a\n') or header.startswith(b'\xff\xd8\xff') or header[:4]==b'RIFF' and header[8:12]==b'WEBP'
            if valid and len(header)<=MAX_COVER_BYTES:validate_image(header)
            assessment=assess_png(header) if valid and len(header)<=MAX_COVER_BYTES else None
            return {'verified':response.status==200 and valid and len(header)<=MAX_COVER_BYTES and (allow_blank_image or not assessment or not assessment['uniform']),'url':url,'httpStatus':response.status,'contentType':response.headers.get('Content-Type'),'cacheControl':response.headers.get('Cache-Control'),'assessment':assessment}
    except Exception as error:return {'verified':False,'url':url,'httpStatus':getattr(error,'code',None),'error':type(error).__name__}


def image_file(path, maximum, allow_blank_image=False):
    file = Path(path)
    if not 0 < file.stat().st_size <= maximum:
        raise ValueError(f'Image must be 1..{maximum} bytes')
    data = file.read_bytes()
    valid = (data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff')
             or data[:4] == b'RIFF' and data[8:12] == b'WEBP')
    if not valid:
        raise ValueError('Use a JPEG, PNG or WebP image')
    validate_image(data)
    assessment=assess_png(data)
    if assessment and assessment['uniform'] and not allow_blank_image:raise ValueError('The image is blank, transparent or a solid color; select the intended image. Only allow_blank_image=True explicitly permits this.')
    return data


def upload_image(data, token):
    """Use only the storage host and short-lived form authorization returned by the API."""
    host = token.get('RequestHost')
    uri = token.get('RequestURI')
    target=upload_target(token)
    if not isinstance(uri, str) or not uri:
        raise ValueError('Upload credential has no RequestURI')
    fields = {}
    if host:
        endpoint = str(host).replace('http:', 'https:', 1)
        name = urlsplit(endpoint).hostname or ''
        if not name.endswith('.aliyuncs.com'):
            raise ValueError('Unexpected object storage host')
        fields = {'key': uri, 'OSSAccessKeyId': token.get('AccessKey') or '',
                  'policy': token.get('Policy') or '', 'Signature': token.get('Authorization') or ''}
    else:
        if not uri.startswith('/') or uri.startswith('//'):
            raise ValueError('Unexpected upload bucket path')
        endpoint = 'https://v0.api.upyun.com' + uri
        fields = {'authorization': token.get('Authorization') or '', 'policy': token.get('Policy') or ''}
    boundary = 'plweb-' + uuid.uuid4().hex
    chunks = []
    for key, value in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    chunks += [f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="image.jpg"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode(), data, f'\r\n--{boundary}--\r\n'.encode()]
    request = Request(endpoint, data=b''.join(chunks), method='POST',
                      headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
    try:
        with build_opener(_NoRedirect()).open(request, timeout=40) as response:
            if not 200 <= response.status < 300:
                raise CommunityError(response.status, 'image_upload_failed')
            raw=response.read(16384)
            try:result=json.loads(raw) if raw.strip() else {}
            except ValueError:result={}
            if not host and (not isinstance(result,dict) or result.get('code')!=200 or not isinstance(result.get('url'),str)):raise CommunityError(502,'invalid_upload_response')
            if isinstance(result,dict) and 'code' in result and result['code']!=200:raise CommunityError(result['code'],'image_upload_failed',code=str(result.get('message','')))
            actual=result.get('url') if isinstance(result,dict) else None
            if actual is not None and actual!=target:raise CommunityError(502,'upload_target_mismatch',data={'expectedPath':target,'actualPath':actual})
            return {'path':target,'storageCode':result.get('code') if isinstance(result,dict) else None,'storageMessage':result.get('message') if isinstance(result,dict) else None}
    except Exception as error:
        if isinstance(error, CommunityError):raise
        raise CommunityError(getattr(error, 'code', None), 'image_upload_failed') from None


class CommunityActions:
    def __init__(self, api):
        self.api = api

    def publish(self, archive, *, title=None, description=None, tags=None, category='Experiment', cover=None, replace_tags=False):
        if isinstance(archive, (str, Path)):
            file = Path(archive)
            if file.stat().st_size > 32 * 1024 * 1024:raise ValueError('Archive exceeds 32MB')
            archive = json.loads(file.read_text(encoding='utf-8-sig'))
        validate_archive_model(archive)
        if category not in ('Experiment','Discussion','Model'):raise ValueError('Invalid category')
        summary, experiment = dict(archive.get('Summary') or {}), dict(archive['Experiment'])
        for key in ('ID','ContentID'):summary[key]=None
        experiment['ID']=None
        experiment['Summary']=None
        summary.update({'Category':category,'Subject':title or summary.get('Subject') or experiment.get('Subject'),
                        'Language':summary.get('Language') or 'Chinese',
                        'User':{'ID':self.api._session.get('account_id')}, 'Coauthors':[]})
        if description is not None:summary['Description']=description.splitlines() if isinstance(description,str) else description
        if summary.get('Description') is None:summary['Description']=[]
        if tags is not None:summary['Tags']=list(dict.fromkeys([tag for tag in (summary.get('Tags') or []) if not replace_tags or str(tag).startswith('Type-')]+tags))
        experiment['Subject']=summary['Subject']
        result=self.api.request('/Contents/SubmitExperiment',{'Summary':summary,'Experiment':experiment,'Workspace':None})
        created=result['Data']['Summary']
        context={'operation':'publish','summaryId':created['ID'],'contentId':created.get('ContentID'),'category':category,'submitted':True,'next':'Read the existing work; do not repeat publication'}
        try:
            if cover is not None:cover_result=self.set_cover(created['ID'],cover,category=category)
            else:
                from experiment_cover import render
                cover_result=self._set_cover_bytes(created['ID'],render({'Experiment':experiment}),category)
            saved=self.api.request('/Contents/GetExperiment',{'ContentID':created['ContentID']})['Data']
            final=self.api.request('/Contents/GetSummary',{'ContentID':created['ID'],'Category':category})['Data']
            if saved.get('StatusSave')!=experiment.get('StatusSave'):raise ValueError('Published model differs from submitted model')
        except CommunityError as error:
            error.context={**(error.context or {}),'publication':context};raise
        except Exception:
            raise CommunityError(None,'publish_post_submit_failed',context={'publication':context}) from None
        return {'published':True,'summary':final,'contentId':created['ContentID'],'modelVerified':True,'coverUploaded':cover_result['updated'],'cover':cover_result}

    def set_avatar(self,path,*,allow_blank_image=False):
        data=image_file(path,MAX_AVATAR_BYTES,allow_blank_image)
        user_id=self.api._session.get('account_id')
        user=self.api.request('/Users/GetUser',{'ID':user_id})['Data']['User']
        index=int(user.get('Avatar') or 0)+1
        token=self.api._exchange('/Users/RequestAvatar',{'Request':{'FileSize':-len(data),'Extension':'.jpg'}})['Data']
        receipt=upload_image(data,token)
        verification=verify_image(receipt['path'],allow_blank_image)
        if not verification['verified']:return {'updated':False,'avatar':user.get('Avatar'),'pendingAvatar':index,'imageVerification':verification,'storage':receipt}
        self.api.request('/Users/ConfirmAvatar',{'Avatar':index})
        current=self.api.request('/Users/GetUser',{'ID':user_id})['Data']['User']
        return {'updated':current.get('Avatar')==index and verification['verified'],'avatar':current.get('Avatar'),'previousAvatar':user.get('Avatar'),'imageVerification':verification,'storage':receipt,'inputImage':{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}}

    def set_cover(self,summary_id,path,*,category='Experiment',allow_blank_image=False):
        data=image_file(path,MAX_COVER_BYTES,allow_blank_image)
        return self._set_cover_bytes(summary_id,data,category,allow_blank_image)

    def _set_cover_bytes(self,summary_id,data,category='Experiment',allow_blank_image=False):
        summary=self.api.request('/Contents/GetSummary',{'Category':category,'ContentID':summary_id})['Data']
        token=self.api._exchange('/Contents/SubmitExperiment',{'Summary':summary,'Request':{'FileSize':-len(data),'Extension':'.jpg'}})['Data']['Token']
        target=upload_target(token)
        expected='/experiments/images/'+summary_id[:4]+'/'+summary_id[4:6]+'/'+summary_id[6:8]+'/'+summary_id[8:24]+'/'
        if not target.startswith(expected) or not target[len(expected):].removesuffix('.jpg').isdigit() or not target.endswith('.jpg'):raise ValueError('Cover token target does not match this work')
        index=int(target.rsplit('/',1)[1].split('.')[0])
        receipt=upload_image(data,token)
        verification=verify_image(receipt['path'],allow_blank_image)
        if not verification['verified']:return {'updated':False,'image':summary.get('Image'),'pendingImage':index,'summaryId':summary_id,'imageVerification':verification,'storage':receipt}
        confirm={'Category':category,'SummaryID':summary_id,'Image':index,'Extension':'.jpg'}
        self.api.request('/Contents/ConfirmExperiment',confirm)
        current=self.api.request('/Contents/GetSummary',{'Category':category,'ContentID':summary_id})['Data']
        return {'updated':current.get('Image')==index and verification['verified'],'image':current.get('Image'),'summaryId':summary_id,'imageVerification':verification,'storage':receipt,'inputImage':{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}}

    def remove(self,summary_id,*,category='Experiment',hide=False,reason=''):
        before=self.api.request('/Contents/GetSummary',{'Category':category,'ContentID':summary_id})['Data']
        if not hide and before.get('User',{}).get('ID')!=self.api._session.get('account_id'):
            raise ValueError('Delete applies to your own works; use hide for moderation')
        result=self.api.request('/Contents/RemoveExperiment',{'Category':category,'SummaryID':summary_id,'Hiding':hide,'Reason':reason})
        return {'operation':'hide' if hide else 'delete','summaryId':summary_id,'result':result}

    def restore(self,summary_id,*,category='Experiment',reason=''):
        self.api.request('/Contents/GetSummary',{'Category':category,'ContentID':summary_id})
        self.api.request('/Contents/RestoreExperiment',{'Category':category,'SummaryID':summary_id,'Reason':reason})
        current=self.api.request('/Contents/GetSummary',{'Category':category,'ContentID':summary_id})['Data']
        return {'restored':current.get('Visibility')==0,'summary':current}

    def invite_coauthor(self,summary_id,target_id,category='Experiment'):
        return self.api.request('/Contents/InviteCoauthor',{'Category':category,'SummaryID':summary_id,'TargetID':target_id})

    def remove_coauthor(self,summary_id,target_id,category='Experiment'):
        return self.api.request('/Contents/RemoveCoauthor',{'Category':category,'SummaryID':summary_id,'TargetID':target_id})

    def handle_invitation(self,message_id,accept=True):
        if not accept:raise ValueError('Use the accept-invitation operation only')
        return self.api.request('/Messages/HandleInvitation',{'MessageID':message_id})

    def _set_managed_tag(self,summary_id,status,category,*,path,tag):
        if not isinstance(status,bool):raise ValueError('status must be a boolean')
        if category not in ('Experiment','Discussion','Model'):raise ValueError('Invalid category')
        before=self.api.request('/Contents/GetSummary',{'Category':category,'ContentID':summary_id})['Data']
        body={'Category':category,'SummaryID':summary_id,'Status':status}
        if tag=='知识库':body['Tag']='知识库'
        self.api.request(path,body)
        after=self.api.request('/Contents/GetSummary',{'Category':category,'ContentID':summary_id})['Data']
        def tag_list(summary):
            value=summary.get('Tags') or []
            return value if isinstance(value,list) else value.get('$values',[]) if isinstance(value,dict) else []
        tags=tag_list(after)
        return {'summaryId':summary_id,'category':category,'tag':tag,'requestedStatus':status,
                'updated':(tag in tags)==status,'beforeTags':tag_list(before),'tags':tags}

    def set_featured(self,summary_id,status,category='Experiment'):
        """Add/remove Featured through SelectExperiment, then read back Tags."""
        return self._set_managed_tag(summary_id,status,category,path='/Contents/SelectExperiment',tag='精选')

    def set_knowledge_base(self,summary_id,status,category='Experiment'):
        """Add/remove Knowledge Base; AcknowledgeExperiment.Tag is fixed here."""
        return self._set_managed_tag(summary_id,status,category,path='/Contents/AcknowledgeExperiment',tag='知识库')

    def _managed_batch(self,summary_ids,status,category,method):
        from community_reads import CommunityReads
        if not isinstance(summary_ids,list) or not 1<=len(summary_ids)<=20 or any(not isinstance(s,str) or not s for s in summary_ids):raise ValueError('Provide 1..20 summary IDs')
        if len(set(summary_ids))!=len(summary_ids):raise ValueError('Summary IDs must be unique')
        if not isinstance(status,bool):raise ValueError('status must be a boolean')
        return CommunityReads(self.api.request)._batch(summary_ids,lambda sid:method(sid,status,category))

    def set_featured_batch(self,summary_ids,status,category='Experiment'):
        return self._managed_batch(summary_ids,status,category,self.set_featured)

    def set_knowledge_base_batch(self,summary_ids,status,category='Experiment'):
        return self._managed_batch(summary_ids,status,category,self.set_knowledge_base)

    def run_batch(self,jobs):
        from community_reads import CommunityReads
        methods={'publish':self.publish,'avatar':self.set_avatar,'cover':self.set_cover,'remove':self.remove,
                 'restore':self.restore,
                 'invite':self.invite_coauthor,'remove_coauthor':self.remove_coauthor,'accept_invitation':self.handle_invitation,
                 'set_featured':self.set_featured,'set_knowledge_base':self.set_knowledge_base}
        if not isinstance(jobs,list) or not 1<=len(jobs)<=20:raise ValueError('Action batch supports 1..20 jobs')
        for job in jobs:
            if not isinstance(job,dict) or job.get('action') not in methods or not isinstance(job.get('args'),dict):raise ValueError('Unknown action or invalid arguments')
        return CommunityReads(self.api.request)._batch(jobs,lambda job:methods[job['action']](**job['args']))
