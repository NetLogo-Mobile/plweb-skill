"""Publishing, image uploads and invitation actions; all requests stay in one account."""
import base64
import json
import mimetypes
from pathlib import Path
import time
from urllib.parse import urlsplit
from urllib.request import Request, build_opener
import uuid
from community_client import CommunityError, _NoRedirect, redact

MAX_AVATAR_BYTES = 1024 * 1024
MAX_COVER_BYTES = 8 * 1024 * 1024


def image_file(path, maximum):
    file = Path(path)
    if not 0 < file.stat().st_size <= maximum:
        raise ValueError(f'Image must be 1..{maximum} bytes')
    data = file.read_bytes()
    valid = (data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff')
             or data[:4] == b'RIFF' and data[8:12] == b'WEBP')
    if not valid:
        raise ValueError('Use a JPEG, PNG or WebP image')
    return data


def upload_image(data, token):
    """Use only the storage host and short-lived form authorization returned by the API."""
    host = token.get('RequestHost')
    uri = token.get('RequestURI')
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
            response.read(4096)
    except Exception as error:
        if isinstance(error, CommunityError):raise
        raise CommunityError(getattr(error, 'code', None), 'image_upload_failed') from None


class CommunityActions:
    def __init__(self, api):
        self.api = api

    def publish(self, archive, *, title=None, description=None, tags=None, category='Experiment', cover=None):
        if isinstance(archive, (str, Path)):
            file = Path(archive)
            if file.stat().st_size > 32 * 1024 * 1024:raise ValueError('Archive exceeds 32MB')
            archive = json.loads(file.read_text(encoding='utf-8-sig'))
        if not isinstance(archive, dict) or not isinstance(archive.get('Experiment'), dict):
            raise ValueError('Expected a .plsav object containing Experiment')
        if category not in ('Experiment','Discussion','Model'):raise ValueError('Invalid category')
        summary, experiment = dict(archive.get('Summary') or {}), dict(archive['Experiment'])
        for key in ('ID','ContentID'):summary[key]=None
        experiment['ID']=None
        experiment['Summary']=None
        summary.update({'Category':category,'Subject':title or summary.get('Subject') or experiment.get('Subject'),
                        'Language':summary.get('Language') or 'Chinese',
                        'User':{'ID':self.api._session.get('account_id')}, 'Coauthors':[]})
        if description is not None:summary['Description']=description.splitlines() if isinstance(description,str) else description
        if tags is not None:summary['Tags']=list(dict.fromkeys([tag for tag in summary.get('Tags',[]) if str(tag).startswith('Type-')]+tags))
        experiment['Subject']=summary['Subject']
        result=self.api.request('/Contents/SubmitExperiment',{'Summary':summary,'Experiment':experiment,'Workspace':None})
        created=result['Data']['Summary']
        if cover is not None:self.set_cover(created['ID'],cover,category=category)
        else:
            from experiment_cover import render
            self._set_cover_bytes(created['ID'],render({'Experiment':experiment}),category)
        saved=self.api.request('/Contents/GetExperiment',{'ContentID':created['ContentID']})['Data']
        final=self.api.request('/Contents/GetSummary',{'ContentID':created['ID'],'Category':category})['Data']
        if saved.get('StatusSave')!=experiment.get('StatusSave'):raise ValueError('Published model differs from submitted model')
        return {'published':True,'summary':final,'contentId':created['ContentID'],'modelVerified':True,'coverUploaded':True}

    def set_avatar(self,path):
        data=image_file(path,MAX_AVATAR_BYTES)
        user_id=self.api._session.get('account_id')
        user=self.api.request('/Users/GetUser',{'ID':user_id})['Data']['User']
        index=int(user.get('Avatar') or 0)+1
        token=self.api._exchange('/Users/RequestAvatar',{'Request':{'FileSize':-len(data),'Extension':'.jpg'}})['Data']
        upload_image(data,token)
        self.api.request('/Users/ConfirmAvatar',{'Avatar':index})
        current=self.api.request('/Users/GetUser',{'ID':user_id})['Data']['User']
        return {'updated':current.get('Avatar')==index,'avatar':current.get('Avatar'),'previousAvatar':user.get('Avatar')}

    def set_cover(self,summary_id,path,*,category='Experiment'):
        data=image_file(path,MAX_COVER_BYTES)
        return self._set_cover_bytes(summary_id,data,category)

    def _set_cover_bytes(self,summary_id,data,category='Experiment'):
        summary=self.api.request('/Contents/GetSummary',{'Category':category,'ContentID':summary_id})['Data']
        index=int(summary.get('Image') or 0)+1
        confirm={'Category':category,'SummaryID':summary_id,'Image':index,'Extension':'.png'}
        self.api.request('/Contents/ConfirmExperiment',confirm)
        summary['Image']=index
        token=self.api._exchange('/Contents/SubmitExperiment',{'Summary':summary,'Request':{'FileSize':-len(data),'Extension':'.jpg'}})['Data']['Token']
        upload_image(data,token)
        self.api.request('/Contents/ConfirmExperiment',confirm)
        current=self.api.request('/Contents/GetSummary',{'Category':category,'ContentID':summary_id})['Data']
        return {'updated':current.get('Image')==index,'image':current.get('Image'),'summaryId':summary_id}

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

    def run_batch(self,jobs):
        from community_reads import CommunityReads
        methods={'publish':self.publish,'avatar':self.set_avatar,'cover':self.set_cover,'remove':self.remove,
                 'restore':self.restore,
                 'invite':self.invite_coauthor,'remove_coauthor':self.remove_coauthor,'accept_invitation':self.handle_invitation}
        if not isinstance(jobs,list) or not 1<=len(jobs)<=20:raise ValueError('Action batch supports 1..20 jobs')
        for job in jobs:
            if not isinstance(job,dict) or job.get('action') not in methods or not isinstance(job.get('args'),dict):raise ValueError('Unknown action or invalid arguments')
        return CommunityReads(self.api.request)._batch(jobs,lambda job:methods[job['action']](**job['args']))
