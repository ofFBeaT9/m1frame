"""Regressions for live configuration and explicit demo selection."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
from fastapi.testclient import TestClient

from api import server


class LiveConfigurationTests(unittest.TestCase):
    def test_missing_provider_never_silently_replays_demo(self):
        with patch('api.server._can_run_live', return_value=False):
            client = TestClient(server.create_app())
            for body in ({'goal': 'real task'}, {'goal': 'real task', 'mode': 'live'}):
                response = client.post('/run', json=body)
                self.assertEqual(response.status_code, 503)
                self.assertIn('Configure', response.json()['detail'])
            self.assertEqual(client.get('/config').json()['default_mode'], 'live')

    def test_invalid_patch_does_not_change_backend(self):
        client = TestClient(server.create_app())
        before = client.get('/config').json()
        with patch('api.server._persist_config') as persist:
            response = client.patch('/config', json={'backend': 'openrouter', 'model': 'bad\nmodel'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(client.get('/config').json(), before)
        persist.assert_not_called()

    def test_free_model_and_model_only_patch_persist(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'config.yaml').write_text('backend: openrouter\nopenrouter:\n  model: old\n')
            with patch('api.server.ROOT', root), patch('api.server.load_config', return_value={
                    'backend': 'openrouter', 'openrouter': {'model': 'old'}}):
                client = TestClient(server.create_app())
                response = client.patch('/config', json={'model': 'vendor/model:free'})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['model'], 'vendor/model:free')
                self.assertEqual(yaml.safe_load((root / 'config.yaml').read_text())['openrouter']['model'],
                                 'vendor/model:free')

    def test_new_dotenv_key_detected_without_server_restart(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            root = Path(folder)
            cfg = {'backend': 'openrouter', 'openrouter': {'api_key_env': 'M1_TEST_KEY'}}
            with patch('api.server.ROOT', root):
                self.assertFalse(server._can_run_live(cfg))
                (root / '.env').write_text('M1_TEST_KEY=test-only\n')
                self.assertTrue(server._can_run_live(cfg))

    def test_investigator_uses_actual_tool_observations(self):
        from unittest.mock import MagicMock

        from agents.openplanter import OpenPlanterAgent
        with tempfile.TemporaryDirectory() as folder:
            llm = MagicMock()
            llm.chat.side_effect = ['{"m1frame_tool":"calculator","arguments":{"expression":"6*7"}}',
                                    'Verified answer: 42']
            investigator = OpenPlanterAgent(llm, workspace=folder)
            result = investigator.investigate('Calculate six times seven')
            self.assertIn('42', result.raw_analysis)
            self.assertIn('"result": 42', llm.chat.call_args.kwargs['prompt'])
            self.assertEqual(investigator.mode, 'm1frame-tools')

    def test_invalid_contradiction_response_never_records_clean(self):
        from unittest.mock import MagicMock

        from agents.wiki import LLMWiki
        wiki = object.__new__(LLMWiki)
        wiki._load_all_pages = MagicMock(return_value=[MagicMock(), MagicMock()])
        wiki._write_contradictions = MagicMock()
        wiki.llm = MagicMock()
        for response in ('not json', '{}', '[]', '{"clean":"false","contradictions":[]}'):
            wiki.llm.chat.return_value = response
            with self.assertRaisesRegex(ValueError, 'no clean verdict'):
                wiki.detect_contradictions()
        wiki._write_contradictions.assert_not_called()

    def test_optimizer_can_reach_requested_vocabulary(self):
        from optimizers.tools import skill_optimize
        result = skill_optimize('Check the result.', ['quasar'], rounds=50, seed=7, prefer='local')
        self.assertTrue(result['improved'])
        self.assertIn('quasar', result['after'].lower())

    def test_free_only_rejects_paid_models_and_caps_provider_price(self):
        from llm_client import LLMClient
        client = object.__new__(LLMClient)
        client.backend = 'openrouter'
        client.cfg = {'openrouter': {'free_only': True}}
        with self.assertRaisesRegex(ValueError, 'free_only'):
            client._openai_options('paid/model')
        options = client._openai_options('vendor/model:free')
        self.assertEqual(options['extra_body']['provider']['max_price'], {'prompt': 0, 'completion': 0})

    def test_rejected_workflow_does_not_pollute_wiki(self):
        from unittest.mock import MagicMock

        from agents.council import CouncilVerdict
        from scripts import run_workflow as workflow
        from scripts.qa_validate import MockLLMClient
        rejected = CouncilVerdict(3, 'fail', 'Unsupported claims', ['Use evidence'], 'Unverified draft')
        with patch.object(workflow, 'LLMClient', return_value=MockLLMClient()), \
                patch.object(workflow, 'load_config', return_value={'backend': 'mock', 'scientific': {'enabled': False}}), \
                patch.object(workflow, 'LLMCouncil') as council, \
                patch.object(workflow, 'LLMWiki') as wiki, \
                patch.object(workflow, 'SkillLibrary') as skills, \
                patch.object(workflow, 'PillarLogger'), \
                patch('sensors.tools.sensor_config', return_value={'enabled': False}):
            council.return_value.brainstorm.return_value = MagicMock()
            council.return_value.review.return_value = rejected
            wiki.return_value.search.return_value = []
            skills.return_value.suggest.return_value = []
            skills.return_value.as_context.return_value = ''
            result = workflow.run_workflow('Synthetic audit', verbose=False)
            self.assertFalse(result['approved'])
            self.assertIn('NOT APPROVED', result['output'])
            wiki.return_value.ingest.assert_not_called()
            skills.return_value.learn.assert_not_called()

    def test_wiki_lookup_handles_hyphens_and_heading_only_pages(self):
        from agents.wiki import LLMWiki
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            wiki = LLMWiki(None, {'directory': folder, 'index_file': str(root/'index.md')})
            (root/'concepts/architecture-decisions.md').write_text('# Architecture Decisions\nUse evidence.')
            page = wiki.get_page('Architecture Decisions')
            self.assertIsNotNone(page)
            self.assertEqual(page.title, 'Architecture Decisions')

    def test_unknown_run_backend_rejected_before_start(self):
        response = TestClient(server.create_app()).post('/run', json={'goal': 'task', 'backend': 'missing'})
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
