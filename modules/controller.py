"""One admission policy for user goals; it never rewrites the user's goal."""
from __future__ import annotations

from copy import deepcopy

DEFAULTS = {
    'enabled': False,
    'require_full_workflow': True,
    'headroom_required': True,
    'skillopt_required': True,
    'investigate_every_goal': True,
}


def controller_policy(cfg: dict) -> dict:
    supplied = cfg.get('controller') or {}
    return {key: bool(supplied.get(key, default)) for key, default in DEFAULTS.items()}


def effective_config(cfg: dict) -> dict:
    """Enable the requested layers consistently for CLI, MCP and API clients."""
    policy = controller_policy(cfg)
    if not policy['enabled']:
        return cfg
    result = deepcopy(cfg)
    if policy['headroom_required']:
        result.setdefault('headroom', {}).update(enabled=True, required=True)
    if policy['skillopt_required']:
        result.setdefault('optimizers', {}).update(enabled=True, prefer='skillopt')
    result.setdefault('adhd', {})['enabled'] = True
    result.setdefault('scientific', {})['enabled'] = True
    result.setdefault('sensors', {})['enabled'] = True
    return result


def validate_workflow(cfg: dict, **options) -> dict:
    policy = controller_policy(cfg)
    if policy['enabled'] and policy['require_full_workflow']:
        skipped = [key for key, value in options.items() if key.startswith('skip_') and value]
        if skipped:
            raise ValueError('Controller requires the full workflow; requested bypasses: '
                             + ', '.join(skipped) + '. Change controller policy explicitly to allow bypasses.')
    return policy


def chat_mode(cfg: dict, requested: str) -> str:
    policy = controller_policy(cfg)
    if requested == 'quick' and policy['enabled'] and policy['require_full_workflow']:
        raise ValueError('Full-workflow controller is enabled. Select Full workflow; Quick answer is disabled.')
    return requested


# This is procedural guidance, not a replacement or summary of the user request.
# Candidates cannot remove these constraints. No generated facts enter this loop.
REQUIRED_GUIDANCE = (
    'Keep the user goal and constraints unchanged.',
    'Use observed evidence and report blocked or unavailable steps.',
    'Never bypass tool authorization or final output checks.',
)
CHECKS = (
    'Recall relevant wiki evidence and vetted skills before planning.',
    'Define acceptance criteria and dependencies in the BMAD plan.',
    'Check assumptions through investigation and tool observations.',
    'Carry verified outputs through Miras handoffs.',
    'Select scientific instructions only when they match the goal.',
    'Review the final answer with the council and report structural measurements separately.',
    'Persist wiki knowledge and learned skills only after approval.',
)


def optimize_execution_guidance(cfg: dict) -> tuple[str, dict]:
    """Run bounded SkillOpt on every admitted controller goal, even with no saved skill.

    The deterministic objective measures procedural checklist coverage, not answer
    accuracy. Guidance stays transient; existing approval gates govern learning.
    """
    from optimizers import SkillOptimizer

    policy = controller_policy(cfg)
    settings = cfg.get('optimizers') or {}
    required = policy['enabled'] and policy['skillopt_required']
    if not required and not settings.get('enabled', True):
        return '', {'status': 'disabled', 'persisted': False}
    engine = SkillOptimizer(seed=int(settings.get('seed', 1337)),
                            prefer='skillopt' if required else settings.get('prefer', 'auto'))
    if required and engine.pick() != 'skillopt':
        raise RuntimeError('Controller requires the installed SkillOpt adapter; it is unavailable. '
                           'Install the optional SkillOpt package or change controller policy explicitly.')
    base = ' '.join(REQUIRED_GUIDANCE)

    def score(text):
        if any(sentence not in text for sentence in REQUIRED_GUIDANCE):
            return float('-inf')
        return sum(sentence in text for sentence in CHECKS) - 0.001 * len(text.split())

    result = engine.optimize(base, score, rounds=max(1, min(50, int(settings.get('rounds', 12)))),
                             pool=list(CHECKS))
    if required and (result.tier != 'skillopt' or result.error):
        raise RuntimeError('Required SkillOpt execution failed; no fallback was accepted.')
    if any(sentence not in result.after for sentence in REQUIRED_GUIDANCE):
        raise RuntimeError('Optimizer failed to preserve execution constraints.')
    return result.after, {'status': 'completed', 'tier': result.tier,
                          'before_score': result.before_score, 'after_score': result.after_score,
                          'rounds': result.rounds, 'accepted': result.accepted,
                          'improved': result.improved, 'persisted': False,
                          'objective': 'procedural checklist coverage; not answer accuracy',
                          'error': result.error or None}
