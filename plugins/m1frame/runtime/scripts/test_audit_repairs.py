"""Regression cases for the operational audit's observed failure modes."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from agents.karpathy import KarpathyEngine
from agents.wiki import LLMWiki
from agents.wiki_contract import split_page
from modules.output import clean_answer, delivery_text
from scripts.qa_validate import MockLLMClient


class AuditRepairTests(unittest.TestCase):
    def test_generated_date_and_unquoted_links_are_normalized(self):
        with tempfile.TemporaryDirectory() as folder:
            llm = MagicMock()
            llm.chat.side_effect = ['{}', '---\ntitle: Fixture\ncreated: YYYY-MM-DD\nrelated: [[Unknown]]\npage_type: source\n---\nEvidence.']
            page = LLMWiki(llm, {'directory': folder}).ingest('Evidence.', page_type='source')
            fm, _ = split_page(page.content)
            import datetime
            self.assertEqual(fm['created'], str(datetime.date.today()))
            self.assertEqual(fm['related'], [])
            self.assertEqual(llm.chat.call_count, 2)

    def test_reasoning_blocks_never_survive(self):
        cases = [('<thought>PRIVATE', ''), ('<think>PRIVATE</think>42', '42'),
                 ('<thought>a</thought><thought>PRIVATE</thought>42', '42'),
                 ('<THOUGHT>PRIVATE</THOUGHT>42', '42'),
                 ('<analysis>a<think>PRIVATE</think>b</analysis>42', '42'),
                 ('PRIVATE</thought>42', '42')]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(clean_answer(raw), expected)
                self.assertEqual(KarpathyEngine(None)._parse(raw).answer, expected)
        with self.assertRaises(ValueError):
            delivery_text('<thought>PRIVATE')

    def test_two_pass_synthesis_has_real_source_chain(self):
        with tempfile.TemporaryDirectory() as folder:
            llm = MagicMock(wraps=MockLLMClient())
            wiki = LLMWiki(llm, {'directory': folder})
            page = wiki.ingest('Evidence: 2+2=4.', 'audit', page_type='synthesis', project='audit')
            fm, body = split_page(page.content)
            self.assertEqual(llm.chat.call_count, 2)
            self.assertEqual(fm['page_type'], 'synthesis')
            self.assertIn('audit', fm['tags'])
            self.assertTrue(fm['confidence'])
            for source in fm['sources']:
                self.assertTrue(Path(folder, 'sources', source + '.md').exists())
            self.assertIn('Source Evidence', body)
            self.assertFalse(wiki.lint().recommendations)

    def test_fifth_ingest_lints_without_extra_model_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            llm = MagicMock(wraps=MockLLMClient())
            wiki = LLMWiki(llm, {'directory': folder})
            with patch.object(wiki, 'lint', wraps=wiki.lint) as lint:
                for _ in range(5):
                    wiki.ingest('Evidence')
                self.assertEqual(lint.call_count, 1)
            self.assertEqual(llm.chat.call_count, 10)

    def test_lint_covers_page_after_thirty(self):
        with tempfile.TemporaryDirectory() as folder:
            wiki = LLMWiki(None, {'directory': folder})
            for i in range(35):
                Path(folder, 'concepts', f'{i:02}.md').write_text(
                    f'---\ntitle: Page {i}\npage_type: concept\n---\n[[Missing {i}]]')
            self.assertTrue(any('Missing 34' in p for p in wiki.lint().missing_pages))

    def test_learning_waits_for_output_guard(self):
        from agents.council import CouncilVerdict
        from agents.guardrails import GuardResult
        from scripts import run_workflow as w
        with patch.object(w, 'LLMClient', return_value=MockLLMClient()), \
                patch.object(w, 'load_config', return_value={'backend': 'mock', 'scientific': {'enabled': False}}), \
                patch.object(w, 'LLMCouncil') as council, patch.object(w, 'LLMWiki') as wiki, \
                patch.object(w, 'SkillLibrary') as skills, patch.object(w, 'PillarLogger'), \
                patch.object(w, 'GuardrailEngine') as guard, \
                patch('modules.receipts.RunReceipt.finish', return_value='fixture'), \
                patch('sensors.tools.sensor_config', return_value={'enabled': False}):
            council.return_value.review.return_value = CouncilVerdict(9, 'pass', 'ok', [], 'blocked output')
            guard.return_value.check_input.return_value = GuardResult(True, 'allow', 'goal', 'input')
            guard.return_value.check_output.return_value = GuardResult(False, 'block', '', 'output')
            guard.return_value.refusal_text.return_value = 'Blocked'
            wiki.return_value.search.return_value = []
            skills.return_value.suggest.return_value = []
            skills.return_value.as_context.return_value = ''
            result = w.run_workflow('Synthetic task', verbose=False)
            self.assertFalse(result['approved'])
            skills.return_value.learn.assert_not_called()
            wiki.return_value.ingest.assert_not_called()

    def test_tool_receipt_contains_real_observation(self):
        from agents.tool_loop import run_with_tools
        llm = MagicMock()
        llm.chat.side_effect = ['{"m1frame_tool":"calculator","arguments":{"expression":"2*(3+4)"}}', '14']
        emitted = []
        run_with_tools(llm, 'Task', 'System', emit=lambda *a, **kw: emitted.append(kw))
        self.assertEqual(json.loads(emitted[0]['observation'])['result'], 14)
        self.assertTrue(emitted[0]['receipt_id'])

    def test_provider_denial_is_explicit_without_fallback(self):
        from llm_client import LLMClient
        client = object.__new__(LLMClient)
        client.cfg = {'openrouter': {'model': 'vendor/model:free'}}
        client.backend = 'openrouter'
        error = RuntimeError('denied')
        error.status_code = 403
        client._openai_chat = MagicMock(side_effect=error)
        with self.assertRaisesRegex(RuntimeError, 'No model or paid-provider fallback'):
            client.chat('test')
        self.assertEqual(client._openai_chat.call_count, 1)

    def test_daily_quota_is_not_retried_but_transient_failure_is(self):
        from llm_client import LLMClient
        client = object.__new__(LLMClient)
        client.cfg = {'openrouter': {'model': 'vendor/model:free', 'max_retries': 2}}
        client.backend = 'openrouter'
        daily = RuntimeError('free-models-per-day')
        daily.status_code = 429
        client._openai_chat = MagicMock(side_effect=daily)
        with self.assertRaisesRegex(RuntimeError, 'daily free-model quota exhausted'):
            client.chat('test')
        self.assertEqual(client._openai_chat.call_count, 1)
        transient = RuntimeError('temporary service failure')
        transient.status_code = 503
        client._openai_chat = MagicMock(side_effect=[transient, 'answer'])
        with patch('llm_client.time.sleep'):
            self.assertEqual(client.chat('test'), 'answer')
        self.assertEqual(client._openai_chat.call_count, 2)

    def test_confirmation_prevents_false_confidence_decay(self):
        import datetime

        from agents.wiki_contract import render_page
        with tempfile.TemporaryDirectory() as folder:
            wiki = LLMWiki(None, {'directory': folder})
            Path(folder, 'sources', 'confirmation.md').write_text(render_page(
                {'title': 'Confirmation', 'page_type': 'source', 'confidence': 'high',
                 'created': str(datetime.date.today())}, 'Evidence'))
            page = Path(folder, 'concepts', 'old.md')
            page.write_text(render_page({'title': 'Old', 'page_type': 'concept', 'confidence': 'high',
                                         'created': '2000-01-01', 'last_confirmed': str(datetime.date.today()),
                                         'confirming_sources': ['confirmation']}, 'Supported'))
            wiki.decay_confidence()
            self.assertEqual(split_page(page.read_text())[0]['confidence'], 'high')

    def test_model_status_does_not_claim_claude_judge_on_openrouter(self):
        from agents.council import LLMCouncil
        client = SimpleNamespace(backend='openrouter', cfg={'openrouter': {'model': 'free-model'}})
        status = LLMCouncil(client, {'judge_model': 'claude-judge'}).model_status()
        self.assertEqual(status['effective_judge_model'], 'free-model')
        self.assertFalse(status['judge_override_applied'])

    def test_passing_council_cannot_replace_reviewed_answer(self):
        from agents.council import LLMCouncil
        llm = MagicMock()
        llm.chat.return_value = json.dumps({'verdict': 'pass', 'consensus_score': 9,
                                           'approved_output': 'Unreviewed replacement'})
        verdict = LLMCouncil(llm, {'personas': [], 'red_team': False}).review('Calculate', '14')
        self.assertEqual(verdict.approved_output, '14')

    def test_redteam_judges_candidate_without_council_anchoring(self):
        from agents.council import CouncilVerdict, LLMCouncil
        llm = MagicMock()
        llm.chat.return_value = json.dumps({'verdict': 'pass', 'score': 9})
        council = LLMCouncil(llm)
        council._red_team('Task', 'Candidate answer', CouncilVerdict(4, 'fail', 'WRONG_REVIEW', [], 'Edited draft'))
        prompt = llm.chat.call_args.kwargs['prompt']
        self.assertIn('Candidate answer', prompt)
        self.assertNotIn('WRONG_REVIEW', prompt)


if __name__ == '__main__':
    unittest.main()
