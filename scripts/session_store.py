"""OS-protected multi-account sessions; no passwords or plaintext fallback."""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import uuid

SERVICE = 'plweb-skill'


def _key(domain, account_id):
    if domain not in ('physics-api-cn.turtlesim.com', 'physics-api-us.turtlesim.com'):
        raise ValueError('Unknown API region')
    if not re.fullmatch(r'[0-9a-fA-F]{24}', account_id or ''):
        raise ValueError('Expected a 24-character account ID')
    return domain + ':' + account_id


class _Blob(ctypes.Structure):
    _fields_ = [('length', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi(value, protect=True):
    buffer = (ctypes.c_ubyte * len(value)).from_buffer_copy(value)
    source, target = _Blob(len(value), buffer), _Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if protect:
        fn = crypt.CryptProtectData
        fn.argtypes = [ctypes.POINTER(_Blob), wintypes.LPCWSTR, ctypes.c_void_p,
                       ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_Blob)]
        ok = fn(ctypes.byref(source), SERVICE, None, None, None, 1, ctypes.byref(target))
    else:
        fn = crypt.CryptUnprotectData
        fn.argtypes = [ctypes.POINTER(_Blob), ctypes.c_void_p, ctypes.c_void_p,
                       ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_Blob)]
        ok = fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target))
    if not ok:
        raise RuntimeError('OS credential protection failed')
    try:
        return ctypes.string_at(target.data, target.length)
    finally:
        kernel.LocalFree(ctypes.cast(target.data, ctypes.c_void_p))


class SessionStore:
    def __init__(self):
        self._windows = os.name == 'nt'
        if self._windows:
            self._directory = Path(os.environ['LOCALAPPDATA']) / SERVICE / 'sessions'
            self._directory.mkdir(parents=True, exist_ok=True)
            # A protected blob alone prevents decryption by other users; also limit access.
            sid = subprocess.run(['whoami', '/user', '/fo', 'csv', '/nh'],
                                 capture_output=True, check=True).stdout.decode('ascii', errors='ignore')
            matches = re.findall(r'S-1-\d+(?:-\d+)+', sid)
            if len(matches) != 1:
                raise RuntimeError('Unable to restrict session directory')
            subprocess.run(['icacls', str(self._directory), '/inheritance:r',
                            '/grant:r', '*' + matches[0] + ':(OI)(CI)F'],
                           capture_output=True, check=True)
        else:
            try:
                import keyring
                backend = keyring.get_keyring()
                module = type(backend).__module__.lower()
                if not any(name in module for name in ('macos', 'secretservice', 'kwallet', 'windows')):
                    raise RuntimeError('A system keyring backend is required')
                self._keyring = keyring
            except ImportError:
                raise RuntimeError('Install keyring and enable a system credential backend') from None

    def _path(self, key):
        return self._directory / (hashlib.sha256(key.encode()).hexdigest() + '.bin')

    def _read(self, key):
        if self._windows:
            return _dpapi(self._path(key).read_bytes(), protect=False).decode()
        value = self._keyring.get_password(SERVICE, key)
        if value is None:
            raise FileNotFoundError('No saved session')
        return value

    def load(self, domain, account_id):
        value = json.loads(self._read(_key(domain, account_id)))
        if value.get('domain') != domain or value.get('account_id') != account_id:
            raise ValueError('Saved account or region mismatch')
        return value

    def save(self, domain, account_id, record):
        key = _key(domain, account_id)
        # Explicit allowlist prevents passwords and arbitrary business payloads being stored.
        value = {field: record.get(field) for field in
                 ('Token', 'AuthCode', 'nickname', 'version', 'device')}
        value.update({'domain': domain, 'account_id': account_id})
        payload = json.dumps(value, ensure_ascii=False)
        if self._windows:
            temp = self._directory / (uuid.uuid4().hex + '.tmp')
            try:
                with temp.open('xb') as stream:
                    stream.write(_dpapi(payload.encode()))
                temp.replace(self._path(key))
            finally:
                temp.unlink(missing_ok=True)
        else:
            self._keyring.set_password(SERVICE, key, payload)
            index = json.loads(self._keyring.get_password(SERVICE, '__accounts__') or '[]')
            if key not in index:
                self._keyring.set_password(SERVICE, '__accounts__', json.dumps(index + [key]))

    def accounts(self):
        if self._windows:
            records = [json.loads(_dpapi(path.read_bytes(), protect=False))
                       for path in self._directory.glob('*.bin')]
        else:
            keys = json.loads(self._keyring.get_password(SERVICE, '__accounts__') or '[]')
            records = [json.loads(self._read(key)) for key in keys]
        return [{key: record.get(key) for key in ('domain', 'account_id', 'nickname')}
                for record in records]

    def forget(self, domain, account_id):
        key = _key(domain, account_id)
        if self._windows:
            self._path(key).unlink(missing_ok=True)
        else:
            if self._keyring.get_password(SERVICE, key) is not None:
                self._keyring.delete_password(SERVICE, key)
            keys = json.loads(self._keyring.get_password(SERVICE, '__accounts__') or '[]')
            self._keyring.set_password(SERVICE, '__accounts__', json.dumps([k for k in keys if k != key]))
