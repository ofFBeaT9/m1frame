"""Adversarial regression cases; no providers, credentials or external network."""
import concurrent.futures
import json
import os
import socket
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agents.council import CouncilVerdict, LLMCouncil
from agents.net import public_request
from agents.scheduler import InvestigationScheduler
from agents.skills import SkillLibrary
from modules.headroom import HeadroomAdapter
from tools.builtin import _safe_path, calculator, regex_extract
from tools.extra import base_convert, grep_files, random_string


class RedTeamTests(unittest.TestCase):
    def test_calculator_resource_limits(self):
        for expression in ('9**999999999', '9**9**9', '(-1)**0.5', '1e300*1e300', '__import__("os")'):
            with self.subTest(expression=expression), self.assertRaises((ValueError, OverflowError)):
                calculator(expression)
        self.assertEqual(calculator('2*(3+4)'), 14)

    def test_base_conversion_invalid_bases(self):
        for base in (-1, 0, 1, 37):
            with self.subTest(base=base), self.assertRaises(ValueError):
                base_convert('100', to_base=base)
        self.assertEqual(base_convert('-255'), '-ff')

    def test_random_allocation_bounded(self):
        self.assertEqual(len(random_string(100000000)), 10000)
        self.assertEqual(random_string(-1), '')

    def test_regex_timeout(self):
        self.assertIn('regex error', str(regex_extract('(a+)+$', 'a' * 50000 + '!')))

    def test_sensitive_paths_denied(self):
        for name in ('.env', '.git/config', '.codex/config.toml', 'id.key', '../outside', 'data.txt:secret'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                _safe_path(name)

    def test_recursive_search_cannot_read_secrets(self):
        with tempfile.TemporaryDirectory() as temp, patch('tools.builtin._ROOT', Path(temp).resolve()):
            Path(temp, '.env').write_text('unique-secret')
            Path(temp, 'public.txt').write_text('public example')
            self.assertEqual(grep_files('unique-secret'), [])
            self.assertEqual(len(grep_files('public')), 1)

    def test_dns_private_addresses_blocked_before_connect(self):
        for address in ('127.0.0.1', '10.0.0.1', '169.254.169.254', '::1'):
            with patch('socket.getaddrinfo', return_value=[(socket.AF_INET, 1, 6, '', (address, 80))]), \
                    patch('socket.socket') as connect, self.assertRaises(ValueError):
                public_request('http://example.test')
            connect.assert_not_called()

    def test_request_pins_validated_address_and_does_not_redirect(self):
        with patch('socket.getaddrinfo', return_value=[(socket.AF_INET, 1, 6, '', ('8.8.8.8', 80))]), \
                patch('socket.socket') as sock, patch('http.client.HTTPConnection') as connection:
            response = connection.return_value.getresponse.return_value
            response.status = 302
            response.read.return_value = b'redirect'
            self.assertEqual(public_request('http://example.test'), (302, b'redirect'))
            sock.return_value.connect.assert_called_once_with(('8.8.8.8', 80))
            connection.return_value.request.assert_called_once()

    def test_council_custom_threshold(self):
        llm = SimpleNamespace(chat=lambda **kwargs: json.dumps({
            'verdict': 'pass', 'consensus_score': 8, 'approved_output': 'ok'}))
        council = LLMCouncil(llm, {'personas': [], 'red_team': False,
                                  'max_debate_rounds': 1, 'consensus_threshold': 9})
        self.assertFalse(council.review('task', 'output').passed)
        council.threshold = 6
        self.assertTrue(council.review('task', 'output').passed)
        self.assertFalse(CouncilVerdict(float('inf'), 'pass', '', [], '').passed)

    def test_redteam_parse_failure_cannot_approve(self):
        llm = SimpleNamespace(chat=lambda **kwargs: json.dumps({'verdict': 'pass', 'consensus_score': 9})
                              if 'Synthesiser' in kwargs.get('system', '') else '[]')
        council = LLMCouncil(llm, {'personas': [], 'max_debate_rounds': 1})
        self.assertFalse(council.review('task', 'output').passed)

    def test_headroom_mutation_failure_preserves_original(self):
        adapter = HeadroomAdapter()
        adapter.enabled = True
        def broken(messages, **kwargs):
            messages[0]['content'] = 'corrupt'
            raise RuntimeError('bad plugin')
        adapter._compress = broken
        original = [{'role': 'user', 'content': 'keep me'}]
        self.assertEqual(adapter.compress_messages(original).messages, original)
        self.assertEqual(original[0]['content'], 'keep me')

    def test_headroom_cannot_drop_request(self):
        adapter = HeadroomAdapter()
        adapter.enabled = True
        adapter._compress = lambda *a, **kw: SimpleNamespace(messages=[{'role': 'user', 'content': 'other'}])
        original = [{'role': 'user', 'content': 'keep me'}]
        result = adapter.compress_messages(original)
        self.assertEqual(result.messages, original)
        self.assertTrue(result.error)

    def test_scheduler_rejects_paths_and_intervals(self):
        with tempfile.TemporaryDirectory() as temp:
            scheduler = InvestigationScheduler(None, temp)
            for job, interval in (('../escape', 1), ('valid', 0), ('valid', float('nan')), ('valid', -1)):
                with self.subTest(job=job, interval=interval), self.assertRaises(ValueError):
                    scheduler.add(job, 'task', interval)

    def test_scheduler_stop_during_execution_does_not_rearm(self):
        with tempfile.TemporaryDirectory() as temp, patch('agents.scheduler.threading.Timer') as timer:
            scheduler = InvestigationScheduler(None, temp)
            scheduler.add('job', 'task')
            scheduler.start()
            scheduler.start()
            self.assertEqual(timer.call_count, 1)
            scheduler._execute = lambda job: scheduler.stop() or 'result'
            scheduler._fire('job')
            self.assertEqual(timer.call_count, 1)

    def test_skill_concurrent_writers_preserve_both(self):
        with tempfile.TemporaryDirectory() as temp:
            path = str(Path(temp, 'skills.json'))
            first, second = SkillLibrary(path), SkillLibrary(path)
            with concurrent.futures.ThreadPoolExecutor(2) as pool:
                futures = [pool.submit(lib.learn, goal, SimpleNamespace(), 9)
                           for lib, goal in ((first, 'astronomy stars'), (second, 'biology cells'))]
                for future in futures:
                    future.result()
            self.assertEqual(len(SkillLibrary(path).all()), 2)

    def test_api_access_policy_and_bounds(self):
        from fastapi.testclient import TestClient

        from api.server import app
        with patch.dict(os.environ, {'M1FRAME_API_TOKEN': ''}):
            client = TestClient(app)
            self.assertEqual(client.get('/health').status_code, 200)
            self.assertEqual(client.get('/health', headers={'Origin': 'https://evil.test'}).status_code, 403)
            self.assertEqual(client.get('/health', headers={'Host': 'evil.test'}).status_code, 403)
            self.assertEqual(client.post('/chat', content='x' * 262145).status_code, 413)
            self.assertEqual(client.post('/schedule', json={'job_id': '../escape', 'task': 'x'}).status_code, 422)
        with patch.dict(os.environ, {'M1FRAME_API_TOKEN': 'test-token'}):
            self.assertEqual(client.get('/health').status_code, 401)
            self.assertEqual(client.get('/health', headers={'Authorization': 'Bearer test-token'}).status_code, 200)

    def test_persisted_sse_replays_and_terminates(self):
        from fastapi.testclient import TestClient

        from api import server
        with patch.dict(server._RUNS, {'persisted': {'bus': None, 'events': [{'type': 'final', 'data': {}}]}}):
            response = TestClient(server.app).get('/run/persisted/events')
            self.assertEqual(response.status_code, 200)
            self.assertIn('"type": "done"', response.text)

    def test_static_server_denies_secrets_and_directory_listing(self):
        import functools
        import threading
        import urllib.error
        import urllib.request
        from http.server import ThreadingHTTPServer

        from studio.static_server import ROOT, PublicHandler
        server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(PublicHandler, directory=str(ROOT)))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f'http://127.0.0.1:{server.server_port}'
            for path in ('/.env', '/.git/config', '/config.yaml', '/wiki/', '/%2eenv'):
                with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(base + path)
                self.assertEqual(error.exception.code, 404)
            with urllib.request.urlopen(base + '/') as response:
                self.assertEqual(response.status, 200)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
