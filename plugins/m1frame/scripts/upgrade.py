"""Explicit runtime code upgrades with backups; user data is never selected."""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

CODE_DIRS = {'agents', 'api', 'modules', 'tools', 'sensors', 'optimizers', 'scientific', 'scripts', 'gateways', 'studio', 'm1frame'}
CODE_SUFFIXES = {'.py', '.html', '.js', '.cjs', '.css'}


def upgrade_runtime(bundle: Path, root: Path) -> dict:
    bundle, root = bundle.resolve(), root.resolve()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = root / '.runtime-backups' / stamp
    changed = []
    for source in sorted(bundle.rglob('*')):
        relative = source.relative_to(bundle)
        if not source.is_file() or source.suffix not in CODE_SUFFIXES:
            continue
        if len(relative.parts) > 1 and relative.parts[0] not in CODE_DIRS:
            continue
        target = root / relative
        if not target.resolve().is_relative_to(root):
            raise RuntimeError(f'Runtime path escapes its directory: {relative}')
        if target.exists() and target.read_bytes() == source.read_bytes():
            continue
        if target.exists():
            saved = backup / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + '.upgrade-tmp')
        shutil.copy2(source, temporary)
        temporary.replace(target)
        changed.append(relative.as_posix())
    result = {'changed': changed, 'backup': str(backup) if backup.exists() else None,
              'preserved': ['.env', 'config.yaml', 'wiki', 'workspace', 'logs', '.external', '.venv']}
    (root / '.runtime-upgrade.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    import sys

    from filelock import FileLock
    destination = Path(sys.argv[1]).resolve()
    with FileLock(str(destination) + '.init.lock', timeout=60):
        report = upgrade_runtime(Path(__file__).resolve().parent.parent / 'runtime', destination)
    print(json.dumps(report, indent=2))
