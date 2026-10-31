"""Offline regression tests. Never read real credentials or write to the community."""
import ast
from email.message import Message
import gzip
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import community_reads as reads
from community_client import CommunityClient, CommunityError, redact
from experiment_view import overview, page
from session_store import SessionStore


class HelpersTest(unittest.TestCase):
    def test_boundary_pagination_reaches_requested_count(self):
        for kind in ('comments', 'works'):
            calls = []
            def request(path, body):
                query = body.get('Query', body)
                cursor = query.get('From') or query.get('CommentID')
                start = int(cursor) if cursor else 1
                calls.append(query)
                rows = [{'ID': str(index)} for index in range(start, min(6, start + query['Take']))]
                return {'Data': {'Comments': {'$values': rows}} if kind == 'comments' else {'$values': rows}}
            client = reads.CommunityReads(request)
            with patch.object(reads, 'sleep'), patch.object(reads, '_next_start', 0):
                result = client.fetch_comments('target', 'User', 5, page_size=3) if kind == 'comments' else client.fetch_works('Experiment', 5, page_size=3)
            self.assertTrue(result['complete'])
            self.assertEqual([row['ID'] for row in result['items']], ['1', '2', '3', '4', '5'])
            self.assertTrue(all(call['Skip'] == 0 for call in calls))

    def test_repeated_page_stops(self):
        client = reads.CommunityReads(lambda *_: {'Data': [{'ID': 'a'}]})
        with patch.object(reads, 'sleep'), patch.object(reads, '_next_start', 0):
            result = client.fetch_works('Experiment', 3)
        self.assertEqual(result['stopReason'], 'no_progress')
        self.assertFalse(result['complete'])
        self.assertEqual(result['pages'], 2)

    def test_limits_checked_before_requests(self):
        client = reads.CommunityReads(lambda *_: self.fail('Invalid batch made a request'))
        jobs = [lambda: client.fetch_works_batch([{'category': 'Experiment', 'count': 11}] * 2),
                lambda: client.fetch_comments_batch([{'target_id': 'x', 'target_type': 'User', 'count': 501}] * 2),
                lambda: client.get_users(['x'] * 21),
                lambda: client.call_batch('/Contents/QueryExperiments', [{'Query': {'Take': -10}}]),
                lambda: client.call_batch('/Contents/QueryExperiments', [{'Query': {'Take': True}}]),
                lambda: client.call_batch('/Contents/QueryExperiments', [{'Query': {'Take': 2, 'Skip': 2}}]),
                lambda: client.call_batch('/Messages/GetMessages', [{}]),
                lambda: client.call_batch('/Contents/GetExperiment', [{}]),
                lambda: client.call_batch('/Messages/SendMessages', [{'TargetID': ['x'] * 11}] * 2, write=True)]
        for job in jobs:
            with self.assertRaises(ValueError):
                job()

    def test_at_most_two_concurrent_requests(self):
        active = maximum = 0
        lock = threading.Lock()
        def request(*_):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
            time.sleep(0.02)
            with lock:
                active -= 1
            return {'Status': 200, 'Data': {}}
        client = reads.CommunityReads(request)
        with patch.object(reads, 'sleep'), patch.object(reads, '_next_start', 0):
            result = client.get_users([str(index) for index in range(8)])
        self.assertEqual(len(result), 8)
        self.assertLessEqual(maximum, 2)

    def test_rate_limit_stops_pending_jobs(self):
        calls = []
        def request(*args):
            calls.append(args)
            raise CommunityError(429)
        with patch.object(reads, 'sleep'), patch.object(reads, '_next_start', 0):
            result = reads.CommunityReads(request).get_users([str(index) for index in range(20)])
        self.assertLessEqual(len(calls), 2)
        self.assertTrue(any(row.get('skipped') for row in result))

    def test_tags_preserve_availability_and_normalize_wrappers(self):
        tag = {'Identifier': 'demo', 'Available': False, 'Flags': {'$values': ['Experiment']}, 'Conflicts': {'$values': ['other']}}
        result = reads.CommunityReads(lambda *_: {'Data': {'ContentTags': {'$values': [tag]}}}).get_available_tags()
        self.assertEqual(result['total'], 1)
        self.assertFalse(result['tags'][0]['Available'])
        self.assertEqual(result['tags'][0]['Conflicts'], ['other'])

    def test_large_experiment_output_is_bounded(self):
        payload = {'Data': {'StatusSave': json.dumps({'Elements': [{'Identifier': str(i), 'ModelID': 'demo', 'text': 'x' * 100000} for i in range(100)], 'Wires': []})}}
        result = overview(payload)
        self.assertEqual(result['collections'][0]['count'], 100)
        self.assertLess(len(json.dumps(result)), 5000)
        result = page(payload, 'Elements', 95, 20)
        self.assertEqual(result['returned'], 5)
        self.assertIsNone(result['nextOffset'])
        self.assertLess(len(json.dumps(result)), 20000)
        self.assertTrue(result['items'][0]['text']['truncated'])
        with self.assertRaises(ValueError):
            overview({'Data': {'Subject': 'model unavailable'}})
        with self.assertRaises(ValueError):
            page(payload, 'Elements', 0, 21)

    def test_credentials_removed_from_business_output(self):
        data = {'Token': 'dummy-secret', 'Data': {'UserToken': {'AuthCode': 'dummy'}, 'Name': 'demo'}}
        self.assertEqual(redact(data), {'Data': {'Name': 'demo'}})

    def test_transport_anonymous_header_rotation_and_gzip(self):
        captured, persisted = [], []
        class Opener:
            def open(self, request, timeout):
                captured.append(request)
                response = io.BytesIO(gzip.compress(json.dumps({'Status': 200, 'Token': 'not-output', 'Data': {}}).encode()))
                response.status = 200
                response.headers = Message()
                response.headers['Content-Encoding'] = 'gzip'
                response.headers['x-API-AuthCode'] = 'rotated-dummy'
                return response
        client = CommunityClient(session={'Token': None, 'AuthCode': 'anonymous-dummy'}, persist=persisted.append)
        client._opener = Opener()
        result = client.request('/Users/GetUser', {'Name': 'demo'})
        self.assertEqual(captured[0].get_header('X-api-authcode'), 'anonymous-dummy')
        self.assertNotIn('Token', result)
        self.assertEqual(persisted[0]['AuthCode'], 'rotated-dummy')
        with self.assertRaises(ValueError):
            client.request('https://unrelated.example/Users/GetUser', {})

    @unittest.skipUnless(os.name == 'nt', 'Windows DPAPI test')
    def test_os_store_multiple_accounts_and_no_plaintext(self):
        # Only dummy sessions in an isolated directory; never touches saved user sessions.
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {'LOCALAPPDATA': folder}):
                store = SessionStore()
                a, b = 'a' * 24, 'b' * 24
                domain = 'physics-api-cn.turtlesim.com'
                for identifier in (a, b):
                    store.save(domain, identifier, {'Token': 'DUMMY_SECRET_FOR_TEST', 'AuthCode': 'dummy', 'Password': 'MUST_NOT_SAVE'})
                self.assertEqual(len(store.accounts()), 2)
                for blob in Path(folder).rglob('*.bin'):
                    self.assertNotIn(b'DUMMY_SECRET_FOR_TEST', blob.read_bytes())
                self.assertNotIn('Password', store.load(domain, a))
                store.forget(domain, a)
                self.assertEqual(store.accounts()[0]['account_id'], b)

    def test_document_python_examples_compile(self):
        import re
        for path in (ROOT / 'docs').glob('*.md'):
            for index, text in enumerate(re.findall(r'```python\n(.*?)\n```', path.read_text(encoding='utf-8'), re.S)):
                ast.parse(text, filename=f'{path.name}:block{index}')

    def test_login_window_has_only_account_password_and_login(self):
        import tkinter as tk
        import login_gui
        try:
            window = tk.Tk()
        except tk.TclError:
            self.skipTest('Tk display unavailable; login must not fall back to chat passwords')
        window.withdraw()
        try:
            with patch.object(login_gui.tk, 'Tk', return_value=window), patch.object(window, 'mainloop'), patch.object(sys, 'argv', ['login_gui.py']):
                login_gui.main()  # Do not submit or enter any account/password.
            frame = window.winfo_children()[0]
            entries = [child for child in frame.winfo_children() if child.winfo_class() == 'TEntry']
            buttons = [child for child in frame.winfo_children() if child.winfo_class() == 'TButton']
            self.assertEqual(len(entries), 2)
            self.assertTrue(entries[1].cget('show'))
            self.assertEqual(len(buttons), 1)
        finally:
            window.destroy()


if __name__ == '__main__':
    unittest.main()
