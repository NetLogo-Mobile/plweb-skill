"""HTTPS adapter for CommunityReads. Credentials stay inside this process."""
import gzip
import json
from threading import RLock
from time import monotonic, sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

DOMAINS = ('physics-api-cn.turtlesim.com', 'physics-api-us.turtlesim.com')
DEVICE = '0d1a760b44023875d2123f2cfcb56dad'
_SECRET_KEYS = {'token', 'authcode', 'password', 'devicetoken', 'usertoken',
                'authorization', 'policy', 'accesskey', 'login', 'x-api-token', 'x-api-authcode'}


def redact(value):
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()
                if key.lower() not in _SECRET_KEYS}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


class CommunityError(RuntimeError):
    def __init__(self, status, kind='upstream_error', *, code=None, data=None, http_status=None):
        self.status = status
        self.kind = kind
        self.code = code
        self.data = redact(data)
        self.http_status = http_status
        super().__init__(f'{code or kind} (status={status})')

    def as_dict(self):
        return {'ok': False, 'error': self.kind, 'httpStatus': self.http_status,
                'Status': self.status, 'Message': self.code, 'Data': self.data}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward credentials to another host.


class CommunityClient:
    def __init__(self, *, domain=DOMAINS[0], version=2411, api_version=2502,
                 device=DEVICE, timeout=30, session=None, persist=None):
        if domain not in DOMAINS:
            raise ValueError('Select the CN or US community API domain')
        self.domain, self.version, self.api_version = domain, version, api_version
        self.device, self.timeout = device, timeout
        self._session = dict(session or {})
        self._persist = persist
        self._opener = build_opener(_NoRedirect())
        self._lock = RLock()
        self._next_start = 0.0

    @classmethod
    def from_saved(cls, account_id, *, domain=DOMAINS[0], store=None):
        from session_store import SessionStore
        store = store or SessionStore()
        record = store.load(domain, account_id)
        return cls(domain=domain, version=record.get('version', 2411),
                   device=record.get('device', DEVICE), session=record,
                   persist=lambda value: store.save(domain, account_id, value))

    def _exchange(self, path, body, *, auth=True, method='POST'):
        parsed = urlsplit(path)
        if (parsed.scheme or parsed.netloc or parsed.query or parsed.fragment
                or not path.startswith('/') or path.startswith('//')
                or '..' in path or '\\' in path):
            raise ValueError('Expected a community-relative API path')
        with self._lock:  # Bind a batch to one account; serialize token rotation.
            delay = self._next_start - monotonic()
            if delay > 0:
                sleep(delay)
            self._next_start = monotonic() + 0.35
            headers = {'Content-Type': 'application/json', 'Accept-Encoding': 'gzip',
                       'x-API-Version': str(self.api_version)}
            if auth:
                for key, header in (('Token', 'x-API-Token'), ('AuthCode', 'x-API-AuthCode')):
                    if self._session.get(key):
                        headers[header] = self._session[key]
            data = json.dumps(body).encode('utf-8') if method == 'POST' else None
            request = Request(f'https://{self.domain}{path}', data=data,
                              headers=headers, method=method)
            try:
                with self._opener.open(request, timeout=self.timeout) as response:
                    status, response_headers = response.status, response.headers
                    raw = response.read()
                    if response_headers.get('Content-Encoding') == 'gzip':
                        raw = gzip.decompress(raw)
                    result = json.loads(raw)
            except HTTPError as error:
                try:
                    payload = json.load(error)
                except (ValueError, OSError):
                    payload = {}
                raise CommunityError(payload.get('Status', error.code), 'http_error',
                                     code=payload.get('Message'), data=payload.get('Data'),
                                     http_status=error.code) from None
            except (URLError, TimeoutError, OSError):
                raise CommunityError(None, 'network_error') from None
            except (ValueError, EOFError):
                raise CommunityError(None, 'invalid_response') from None
            if status != 200 or not isinstance(result, dict):
                raise CommunityError(status, 'invalid_response')
            if result.get('Status') != 200:
                raise CommunityError(result.get('Status'), 'business_error', code=result.get('Message'),
                                     data=result.get('Data'), http_status=status)
            updates = {}
            if path == '/Users/Authenticate':
                if (auth and self._session.get('Token') and self._session.get('account_id')
                        and (result.get('Data', {}).get('User') or {}).get('ID') != self._session['account_id']):
                    raise CommunityError(403, 'saved_account_session_expired')
                updates = {key: result[key] for key in ('Token', 'AuthCode') if key in result}
            for key, header in (('Token', 'x-API-Token'), ('AuthCode', 'x-API-AuthCode')):
                if response_headers.get(header):
                    updates[key] = response_headers[header]
            if auth:
                self._session.update(updates)
                if updates and self._persist:
                    self._persist(dict(self._session))
            return result

    def request(self, path, body):
        """Return business data with credential fields removed. No automatic retries."""
        return redact(self._exchange(path, body))

    def login(self, login=None, password=None):
        """For the GUI/authorized helper only. Never returns credentials to the caller."""
        result = self._exchange('/Users/Authenticate', {
            'Login': login, 'Password': password, 'Version': self.version,
            'Device': {'Identifier': self.device, 'Language': 'Chinese'},
        }, auth=False)
        user = result.get('Data', {}).get('User') or {}
        self._session = {key: result.get(key) for key in ('Token', 'AuthCode')}
        self._session.update({'account_id': user.get('ID'), 'nickname': user.get('Nickname'),
                              'version': self.version, 'device': self.device})
        if self._persist:
            self._persist(dict(self._session))
        return {'account_id': user.get('ID'), 'nickname': user.get('Nickname'),
                'authenticated': bool(self._session.get('Token'))}

    def save(self, store):
        identifier = self._session.get('account_id')
        if not identifier or not self._session.get('Token'):
            raise ValueError('An authenticated account is required for persistence')
        store.save(self.domain, identifier, dict(self._session))
        self._persist = lambda value: store.save(self.domain, identifier, value)

    def get_start_page(self):
        return redact(self._exchange('/Users', None, auth=False, method='GET'))
