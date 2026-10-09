#!/usr/bin/env python3
"""Refresh a known literal-bank HTML without changing its scoring or history.

Only the documented renderer signature is supported. Unknown layouts fail before
writing. A successful refresh still requires browser acceptance of the new bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import tempfile
import re
from pathlib import Path

from audit_practice_bank import (RENDERER_VERSION, SCHEMA, audit, content_identity,
                                 file_hash, materialize, read_constant)
from build_practice_page import validate


def replace_constant(source: str, name: str, value) -> str:
    _, start, end = read_constant(source, name)
    return source[:start] + json.dumps(value, ensure_ascii=False).replace('<', '\\u003c') + source[end:]


def score_source(source: str) -> str:
    match = re.search(r'^function score\(', source, re.M)
    start = match.start() if match else -1
    end = source.find('\n', start)
    if start < 0 or end < 0 or source[start:end].count('{') != source[start:end].count('}'):
        raise ValueError('Unsupported scoring signature; inspect and adapt the renderer explicitly')
    return source[start:end]


def refresh(target: Path, bank_path: Path, review_path: Path, backup: Path) -> dict:
    original = target.read_bytes()
    before = hashlib.sha256(original).hexdigest()
    source = original.decode('utf-8')
    bank = materialize(json.loads(bank_path.read_text(encoding='utf-8')), bank_path.resolve().parent)
    validate(bank)
    result = audit(bank, json.loads(review_path.read_text(encoding='utf-8')))
    if result['status'] != 'passed':
        raise ValueError('; '.join(result['errors']))
    if '<h1>' + html.escape(bank['title']) + '</h1>' not in source:
        raise ValueError('Visible title differs; adapt the header explicitly before refresh')
    if bank.get('banner') and html.escape(bank['banner']) not in source:
        raise ValueError('Visible banner differs; adapt the header explicitly before refresh')
    old = read_constant(source, 'QUESTIONS')[0]
    for name, key in (('COURSE', 'course'), ('PAPER', 'paper_id')):
        if read_constant(source, name)[0] != bank[key]:
            raise ValueError('Course/paper identity must be preserved')
    if len(old) != len(bank['questions']):
        raise ValueError('Question count changed; this is not a conservative refresh')
    for a, b in zip(old, bank['questions']):
        if (a.get('points', 1), a.get('type', 'choice'), len(a.get('answer', [])) > 1) != (b.get('points', 1), b.get('type', 'choice'), len(b.get('answer', [])) > 1):
            raise ValueError('Points and question/selection types must be preserved')
    if read_constant(source, 'VERSION')[0] == bank['version']:
        raise ValueError('Use a new content version to keep old attempts separate')
    scoring = score_source(source)
    history = re.search(r'^const HIST=([^;]+);', source, re.M)
    key = re.search(r'^const KEY=([^;]+);', source, re.M)
    if not history or not key or not all(x in source for x in ('function renderHistory()', 'function save()', 'function load()', "id=\"questions\"", "id=\"submit\"", 'function rich(')):
        raise ValueError('Unsupported history/rendering signature; original HTML left untouched')
    prompt = '<p>${rich(q.prompt)}</p>'
    if prompt not in source:
        raise ValueError('Unsupported prompt layout; original HTML left untouched')
    if 'function questionImage(' not in source:
        helper = '\nfunction questionImage(q){return q.prompt_image?`<figure class="evidence"><img src="${esc(q.prompt_image)}" alt="${esc(q.prompt_image_caption||\'Question figure\')}"><figcaption>${esc(q.prompt_image_caption||\'\')}</figcaption></figure>`:\'\';}\n'
        source = source.replace('\nfunction render(', helper + 'function render(', 1)
        source = source.replace(prompt, prompt + '${questionImage(q)}')
    elif source.count(prompt) != source.count(prompt + '${questionImage(q)}'):
        raise ValueError('Unsupported existing figure helper placement')
    metadata = {'renderer_version': RENDERER_VERSION, 'content_sha256': content_identity(bank),
                'content_reviewed': True, 'bank_fields': {k: bank.get(k) for k in ('title', 'banner', 'requirements')}}
    if re.search(r'^const CONTENT_METADATA\s*=', source, re.M):
        source = replace_constant(source, 'CONTENT_METADATA', metadata)
    else:
        insertion = 'const CONTENT_METADATA=' + json.dumps(metadata, ensure_ascii=False).replace('<', '\\u003c') + ';\n'
        source = source.replace(key.group(0), insertion + key.group(0), 1)
    source = replace_constant(source, 'QUESTIONS', bank['questions'])
    source = replace_constant(source, 'VERSION', bank['version'])
    # Keep historical submissions, but start a new attempt for changed content.
    source = source.replace(key.group(0), 'const KEY=`ntu-practice:${COURSE}:${PAPER}:${VERSION}:${CONTENT_METADATA.content_sha256}`;', 1)
    if score_source(source) != scoring or history.group(0) not in source:
        raise ValueError('Scoring/history preservation failed')
    marker = '<p class="meta" data-content-version>' + 'Content version: ' + bank['version'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') + '</p>'
    source = re.sub(r'<p class="meta" data-content-version>.*?</p>', '', source)
    source = source.replace('</header>', marker + '</header>', 1)
    source = source.replace('</style>', '.evidence img{max-width:100%;height:auto}.evidence figcaption{font-size:14px}</style>', 1)
    if backup.resolve() == target.resolve() or backup.exists():
        raise ValueError('Backup must be a new file outside the original target')
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_bytes(original)
    expected = source.encode('utf-8')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.' + target.name + '.', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(expected)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(target.stat().st_mode)
        if file_hash(target) != before:
            raise ValueError('Original changed during refresh; backup retained, no write performed')
        os.replace(temporary, target)
        if target.read_bytes() != expected:
            raise OSError('Refresh readback differs; preserve current file and restore from backup after review')
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {**result, 'status': 'refreshed_pending_browser', 'before_html_sha256': before,
            'html_sha256': file_hash(target), 'backup_sha256': file_hash(backup),
            'scoring_sha256': hashlib.sha256(scoring.encode()).hexdigest(),
            'history_preserved': True, 'browser_validation': 'pending'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('html', type=Path)
    parser.add_argument('--bank', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = refresh(args.html, args.bank, args.review, args.backup)
    except (Exception, SystemExit) as exc:
        result = {'schema': SCHEMA, 'status': 'failed', 'errors': [str(exc)]}
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['status'] == 'refreshed_pending_browser' else 1)


if __name__ == '__main__':
    main()
