"""Local module inventory. Availability is not a claim of successful live execution."""
import importlib.util
import os
import sys
from pathlib import Path


def module_status(cfg: dict) -> dict:
    from modules.adhd import ADHDFormatter
    from modules.headroom import HeadroomAdapter
    from optimizers.skillopt import SkillOptAdapter
    from scientific import ScientificLibrary
    from sensors import SentruxClient

    def available(name):
        return importlib.util.find_spec(name) is not None

    backend = cfg.get('backend', 'claude')
    provider = cfg.get(backend) or {}
    key_env = provider.get('api_key_env')
    library = ScientificLibrary((cfg.get('scientific') or {}).get('path'))
    wiki = cfg.get('wiki') or {}
    return {
        'execution_verified': False,
        'runtime': {'source_root': str(Path(__file__).resolve().parent.parent),
                    'working_directory': str(Path.cwd()), 'python': sys.executable},
        'note': 'Inventory only. Run a live workflow and inspect emitted events to verify execution.',
        'provider': {'backend': backend, 'model': provider.get('model'),
                     'key_configured': bool(key_env and os.environ.get(key_env)),
                     'requires_key': bool(key_env), 'live_verified': False},
        'core': {'bmad': 'local implementation', 'council': 'local implementation',
                 'miras': 'local orchestration; external memory is a separate host connection',
                 'karpathy': 'local refinement', 'wiki': 'local knowledge store',
                 'openplanter': 'local investigation with registered tools; upstream engine not invoked',
                 'guardrails': 'local rules; optional classifier needs a running endpoint'},
        'adhd': ADHDFormatter(bool((cfg.get('adhd') or {}).get('enabled', False))).status(),
        'headroom': HeadroomAdapter(cfg.get('headroom')).status(),
        'skillopt': SkillOptAdapter().probe(),
        'sentrux': {'available': SentruxClient().available(), 'measured': False,
                    'verify_with': 'sentrux_scan'},
        'scientific': {'enabled': (cfg.get('scientific') or {}).get('enabled', True),
                       'count': len(library.skills), 'errors': library.errors,
                       'scope': 'Instructions and resources; scientific workflows need their own dependencies and validation'},
        'wiki_paths': {'directory': str(Path(wiki.get('directory', 'wiki')).resolve()),
                       'index': str(Path(wiki.get('index_file', 'wiki/index.md')).resolve()),
                       'purpose': str(Path(wiki.get('purpose_file', 'purpose.md')).resolve())},
        'council': {'backend': backend, 'persona_model': provider.get('model'),
                    'requested_judge_model': (cfg.get('council') or {}).get('judge_model'),
                    'effective_judge_model': ((cfg.get('council') or {}).get('judge_model')
                                             if backend in {'claude', 'claudecli'} else None) or provider.get('model')},
        'semantic_wiki': {'configured': wiki.get('vector_store') == 'lancedb',
                          'lancedb_installed': available('lancedb'),
                          'embeddings_installed': available('sentence_transformers'),
                          'model_configured': bool(wiki.get('embed_model'))},
        'exa': {'package_installed': available('exa_py'), 'key_configured': bool(os.environ.get('EXA_API_KEY'))},
        'voyage': {'package_installed': available('voyageai'), 'key_configured': bool(os.environ.get('VOYAGE_API_KEY'))},
        'shieldgemma': {'enabled': bool((cfg.get('guardrails') or {}).get('shieldgemma', {}).get('enabled', False)),
                        'endpoint_verified': False},
        'external_mcp': 'Explicit MCPClient connection required; host connections are not inherited',
    }
