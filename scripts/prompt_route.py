"""Trusted Codex prompt hook: route through the main agent, never export prompts."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

CONTEXT = (
    'The user enabled the m1frame full-workflow controller. Act as the main agent: '
    'preserve the user goal and constraints, consult m1frame_context when needed, '
    'and invoke m1frame_run for substantive goals with all pillars enabled. '
    'The runtime requires Headroom on every model request and SkillOpt execution-guidance '
    'evaluation on every admitted goal; persistence still requires approval. '
    'Use actual file, shell and test tools for implementation and verification. '
    'Never recursively invoke m1frame from inside its own workflow. '
    'Do not send credentials or unapproved private material in a workflow goal. '
    'Respect explicit user opt-outs and ordinary tool permissions. '
    'Use offline tools for status/recall; if the provider or required modules are blocked, '
    'report that and continue authorized local work without claiming full live execution. '
    'Return the final result with actual approval/storage status and execution receipt.'
)


def route_context(event: dict, cfg: dict) -> dict:
    if event.get('hook_event_name') != 'UserPromptSubmit':
        return {}
    if not (cfg.get('controller') or {}).get('enabled', False):
        return {}
    return {'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit',
                                  'additionalContext': CONTEXT}}


def main():
    if os.environ.get('M1FRAME_INTERNAL_CALL'):
        return
    raw = sys.stdin.read(262145)
    if len(raw) > 262144:
        return
    try:
        event = json.loads(raw)
    except (ValueError, TypeError):
        return
    if not isinstance(event, dict):
        return
    root = Path(os.environ.get('M1FRAME_HOME') or Path.home() / 'Documents/Codex/m1frame-data')
    if not root.is_absolute() or not (root / 'config.yaml').is_file():
        return
    # Use the already-installed environment; do not install dependencies in a hook.
    interpreter = root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if interpreter.is_file() and Path(sys.executable).resolve() != interpreter.resolve():
        if os.environ.get('M1FRAME_HOOK_CHILD'):
            return
        result = subprocess.run([str(interpreter), str(Path(__file__).resolve())],
                                input=raw, capture_output=True, text=True, timeout=5,
                                env={**os.environ, 'M1FRAME_HOOK_CHILD': '1'},
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        if result.returncode == 0:
            sys.stdout.write(result.stdout)
        return
    try:
        import yaml
        cfg = yaml.safe_load((root / 'config.yaml').read_text(encoding='utf-8')) or {}
        result = route_context(event, cfg)
    except (ImportError, OSError, ValueError, AttributeError):
        return
    if result:
        print(json.dumps(result))


if __name__ == '__main__':
    main()
