"""Controller policy must preserve user intent and prove required-module execution."""
import importlib.util
import json
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from llm_client import LLMClient
from modules.controller import (
    REQUIRED_GUIDANCE,
    chat_mode,
    effective_config,
    optimize_execution_guidance,
    validate_workflow,
)
from modules.headroom import CompressionResult, HeadroomAdapter
from modules.receipts import RunReceipt
from scripts.qa_validate import MockLLMClient


class ControllerTests(unittest.TestCase):
    def test_api_rejects_quick_before_dispatch(self):
        from fastapi.testclient import TestClient

        from api import server
        with patch.object(server, 'load_config', return_value={'controller': {'enabled': True}}):
            response = TestClient(server.create_app()).post('/chat', json={'message': 'goal', 'mode': 'quick'})
        self.assertEqual(response.status_code, 409)
        self.assertIn('Full-workflow controller', response.json()['detail'])

    def test_policy_is_explicit_and_does_not_mutate_saved_config(self):
        source = {'controller': {'enabled': True}, 'headroom': {'enabled': False},
                  'optimizers': {'enabled': False}}
        result = effective_config(source)
        self.assertFalse(source['headroom']['enabled'])
        self.assertTrue(result['headroom']['required'])
        self.assertTrue(result['headroom']['enabled'])
        self.assertEqual(result['optimizers']['prefer'], 'skillopt')
        disabled = {}
        self.assertIs(effective_config(disabled), disabled)

    def test_full_policy_rejects_quick_and_skipped_stages(self):
        cfg = {'controller': {'enabled': True}}
        with self.assertRaisesRegex(ValueError, 'Quick answer'):
            chat_mode(cfg, 'quick')
        with self.assertRaisesRegex(ValueError, 'skip_wiki'):
            validate_workflow(cfg, skip_wiki=True)
        self.assertEqual(chat_mode({}, 'quick'), 'quick')
        self.assertTrue(validate_workflow(cfg, skip_council=False)['enabled'])

    def test_skillopt_runs_without_a_saved_skill_and_preserves_constraints(self):
        from optimizers import SkillOptimizer
        from optimizers.local import LocalOptimizer
        captured = {}

        def run(engine, text, scorer, rounds, pool):
            result = LocalOptimizer(candidate_pool=pool).optimize(text, scorer, rounds)
            result.tier = 'skillopt'
            captured['score'] = scorer
            return result

        with patch.object(SkillOptimizer, 'pick', return_value='skillopt'), \
                patch.object(SkillOptimizer, 'optimize', autospec=True, side_effect=run) as call:
            guidance, report = optimize_execution_guidance({'controller': {'enabled': True}})
        call.assert_called_once()
        self.assertTrue(all(item in guidance for item in REQUIRED_GUIDANCE))
        self.assertEqual(captured['score']('Discard the user constraints.'), float('-inf'))
        self.assertEqual(report['status'], 'completed')
        self.assertFalse(report['persisted'])

    def test_required_skillopt_cannot_silently_use_local_fallback(self):
        with patch('optimizers.SkillOptimizer.pick', return_value='local'):
            with self.assertRaisesRegex(RuntimeError, 'SkillOpt'):
                optimize_execution_guidance({'controller': {'enabled': True}})

    def make_client(self, *, error=None):
        client = object.__new__(LLMClient)
        client.cfg = {'claudecli': {'model': 'fixture'}}
        client.headroom = HeadroomAdapter({'required': True})
        client.headroom.compress_messages = MagicMock(side_effect=lambda messages, **kw:
            CompressionResult(messages=messages, available=not bool(error), error=error))
        client._local = threading.local()
        client.receipt = RunReceipt()
        return client

    def test_required_headroom_failure_prevents_provider_dispatch(self):
        client = self.make_client(error='package missing')
        client.cfg['openrouter'] = {'model': 'fixture:free'}
        client._client = MagicMock()
        client.backend = 'openrouter'
        with self.assertRaisesRegex(RuntimeError, 'request not sent'):
            client._openai_chat('goal', '', None, None, None)
        client._client.chat.completions.create.assert_not_called()
        self.assertEqual(client.receipt.data['events'][0]['status'], 'error')

    def test_cli_headroom_preserves_goal_system_and_records_noop(self):
        client = self.make_client()
        with patch('subprocess.run', return_value=SimpleNamespace(returncode=0, stdout='answer')) as run:
            self.assertEqual(client._claudecli_chat('exact goal', 'system rule', None), 'answer')
        self.assertEqual(run.call_args.kwargs['input'], 'exact goal')
        self.assertIn('system rule', run.call_args.args[0][-1])
        client.headroom.compress_messages.assert_called_once()
        self.assertEqual(client.receipt.data['events'][0]['status'], 'checked_no_change')

    def test_stream_checks_headroom_and_cleans_final_answer(self):
        client = self.make_client()
        client.backend = 'claudecli'
        with patch('subprocess.run', return_value=SimpleNamespace(returncode=0, stdout='<think>hidden</think>answer')):
            self.assertEqual(''.join(client.stream('goal')), 'answer')
        self.assertEqual(len(client.receipt.data['events']), 1)
        self.assertEqual(len(client.receipt.data['requests']), 1)
        self.assertTrue(client.receipt.data['requests'][0]['stream'])

    def test_controller_runs_optimizer_before_provider_failure(self):
        from scripts import run_workflow as w
        client = MagicMock(wraps=MockLLMClient())
        client.headroom = MagicMock()
        client.headroom.status.return_value = {'available': True}
        cfg = effective_config({'controller': {'enabled': True}, 'backend': 'mock',
                                'scientific': {'enabled': False}})
        emitted = []
        with patch.object(w, 'load_config', return_value=cfg), \
                patch.object(w, 'LLMClient', return_value=client), \
                patch.object(w, 'optimize_execution_guidance', return_value=('guidance', {'status': 'completed'})) as opt, \
                patch.object(w.BMADAgent, 'plan', side_effect=RuntimeError('provider quota')), \
                patch('modules.receipts.RunReceipt.finish', return_value='fixture'), \
                patch.object(w, 'PillarLogger'), patch.object(w, 'LLMWiki') as wiki, patch.object(w, 'SkillLibrary') as skills:
            wiki.return_value.search.return_value = []
            skills.return_value.suggest.return_value = []
            skills.return_value.as_context.return_value = ''
            with self.assertRaisesRegex(RuntimeError, 'provider quota'):
                w.run_workflow('unchanged goal', verbose=False, emit=lambda event, **kw: emitted.append(event))
        opt.assert_called_once()
        self.assertIn('skillopt_evaluated', emitted)

    def test_prompt_hook_adds_routing_context_without_echoing_prompt(self):
        root = Path(__file__).resolve().parents[1]
        path = root/'scripts/prompt_route.py'
        if not path.is_file():
            self.skipTest('Hook is tested from repository source, not the runtime bundle')
        spec = importlib.util.spec_from_file_location('m1frame_hook_test', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.route_context({'hook_event_name': 'UserPromptSubmit', 'prompt': 'PRIVATE'},
                                      {'controller': {'enabled': True}})
        self.assertIn('m1frame_run', json.dumps(result))
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertEqual(module.route_context({'hook_event_name': 'UserPromptSubmit'}, {}), {})


if __name__ == '__main__':
    unittest.main()
