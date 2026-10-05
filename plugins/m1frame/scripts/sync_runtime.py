"""Synchronize the plugin's code bundle with repository source; never copy user state."""
import argparse
import shutil
from pathlib import Path

CODE_DIRS = ('agents', 'api', 'gateways', 'm1frame', 'modules', 'optimizers',
             'scientific', 'scripts', 'sensors', 'studio', 'tools')
SUFFIXES = {'.py', '.js', '.cjs', '.html', '.css', '.json'}
ROOT_FILES = ('__main__.py', 'llm_client.py', 'mcp_server.py', 'm1frame-studio.html',
              'config.yaml', 'README.md', 'AUDIT_REPAIRS.md', 'requirements.txt', 'pyproject.toml')


def synchronize(check=False):
    root = Path(__file__).resolve().parents[3]
    bundle = root / 'plugins/m1frame/runtime'
    files = [root / name for name in ROOT_FILES]
    for directory in CODE_DIRS:
        files.extend(path for path in (root / directory).rglob('*')
                     if path.is_file() and path.suffix in SUFFIXES
                     and '__pycache__' not in path.parts)
    differences = []
    for source in sorted(files):
        relative = source.relative_to(root)
        target = bundle / relative
        if target.exists() and target.read_bytes() == source.read_bytes():
            continue
        differences.append(relative.as_posix())
        if not check:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    return differences


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    differences = synchronize(args.check)
    if args.check and differences:
        print('Bundled runtime differs: ' + ', '.join(differences))
        raise SystemExit(1)
    print(f'Runtime bundle {"verified" if args.check else "updated"}: {len(differences)} differences.')
