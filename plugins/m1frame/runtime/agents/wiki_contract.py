"""Deterministic wiki structure checks; semantic truth still needs evidence review."""
from __future__ import annotations

import datetime
import json
import re

import yaml

PAGE_TYPES = {'source', 'entity', 'concept', 'synthesis', 'query'}
LINK = re.compile(r'\[\[([^\]]+)\]\]')


def split_page(text):
    match = re.match(r'^\s*---\s*\n(.*?)\n---\s*\n?', text, re.S)
    if not match:
        raise ValueError('Wiki generation must return YAML frontmatter')
    frontmatter = match.group(1)
    # Models often emit unquoted WikiLinks as YAML flow sequences. Preserve
    # their exact titles while making only this known syntactic repair.
    frontmatter = re.sub(r'^related:[ \t]*([^\n]*\[\[[^\n]*)$',
                         lambda m: 'related: ' + json.dumps(['[[' + title + ']]' for title in LINK.findall(m.group(1))]),
                         frontmatter, flags=re.M)
    frontmatter = re.sub(r'^(\s*-\s*)\[\[([^\]]+)\]\]\s*$',
                         lambda m: m.group(1) + json.dumps('[[' + m.group(2) + ']]'),
                         frontmatter, flags=re.M)
    try:
        fm = yaml.safe_load(frontmatter)
    except yaml.YAMLError as exc:
        raise ValueError('Invalid wiki YAML frontmatter') from exc
    if not isinstance(fm, dict) or not isinstance(fm.get('title'), str) or not fm['title'].strip():
        raise ValueError('Wiki page needs a nonempty title')
    return fm, text[match.end():].strip()


def render_page(fm, body):
    return '---\n' + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip() + '\n---\n\n' + body.strip() + '\n'


def normalize_page(text, known_titles, *, page_type=None, sources=None, project='', raw_source=None):
    fm, body = split_page(text)
    kind = page_type or fm.get('page_type', 'source')
    if kind not in PAGE_TYPES:
        raise ValueError('Invalid wiki page_type')
    title = fm['title'].strip()
    if '[[' in title or ']]' in title or '\n' in title:
        raise ValueError('Invalid wiki title')
    fm.update(title=title, page_type=kind)
    for field in ('tags', 'sources', 'related'):
        if field in fm and (not isinstance(fm[field], list) or not all(isinstance(x, str) for x in fm[field])):
            raise ValueError(f'Wiki {field} must be a list of strings')
    fm['tags'] = list(dict.fromkeys((fm.get('tags') or []) + ([project] if project else [])))
    fm['confidence'] = fm.get('confidence', 'medium')
    if fm['confidence'] not in {'high', 'medium', 'low'}:
        raise ValueError('Invalid confidence')
    try:
        fm['created'] = datetime.date.fromisoformat(str(fm.get('created', datetime.date.today()))).isoformat()
    except ValueError as exc:
        raise ValueError('Invalid created date') from exc
    fm['sources'] = list(sources if sources is not None else fm.get('sources', []))
    if kind != 'source' and not fm['sources']:
        raise ValueError('Non-source pages require source provenance')
    if raw_source:
        fm['raw_source'] = raw_source
    # Unknown links remain readable text; never invent a page to satisfy a link.
    known = set(known_titles) | {title}
    body = LINK.sub(lambda m: m.group(0) if m.group(1) in known else m.group(1), body)
    # Link mentions outside existing WikiLinks and code spans/fences.
    for candidate in sorted(set(known_titles) - {title}, key=len, reverse=True):
        pieces = re.split(r'(\[\[[^\]]+\]\]|```[\s\S]*?```|`[^`]*`)', body)
        for i in range(0, len(pieces), 2):
            pieces[i] = re.sub(r'(?<![\w\[])' + re.escape(candidate) + r'(?![\w\]])',
                               lambda m: '[[' + m.group(0) + ']]', pieces[i])
        body = ''.join(pieces)
    fm['related'] = ['[[' + name + ']]' for name in dict.fromkeys(LINK.findall(body)) if name != title]
    return render_page(fm, body)


def inspect_pages(pages, index):
    titles = {p.title for p in pages}
    sources = {p.filename.rsplit('/', 1)[-1].removesuffix('.md') for p in pages if p.page_type == 'source'}
    missing, orphans, issues = [], [], []
    for page in pages:
        try:
            fm, body = split_page(page.content)
        except ValueError as exc:
            issues.append(f'{page.filename}: {exc}')
            continue
        for key in ('title', 'tags', 'related', 'created', 'page_type', 'confidence'):
            if key not in fm:
                issues.append(f'{page.title}: missing {key}')
        refs = set(LINK.findall(body)) - {page.title}
        if set(fm.get('related') or []) != {'[[' + t + ']]' for t in refs}:
            issues.append(f'{page.title}: related/body mismatch')
        missing += [f'{page.title} -> {t}' for t in refs - titles]
        if '[[' + page.title + ']]' not in index:
            orphans.append(page.title)
        if page.page_type != 'source':
            if not page.sources:
                issues.append(f'{page.title}: missing sources')
            for source in page.sources:
                if source not in sources:
                    issues.append(f'{page.title}: unresolved source {source}')
    return sorted(set(missing)), sorted(set(orphans)), sorted(set(issues))
