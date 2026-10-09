#!/usr/bin/env python3
"""Exercise reviewed offline content in Chrome and bind evidence to exact HTML."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_practice_bank import SCHEMA, RENDERER_VERSION, file_hash, materialize, audit
from check_practice_acceptance import check
from build_practice_page import validate


def exercise(args, result: dict) -> None:
    if not __debug__:
        raise RuntimeError("Browser acceptance requires assertions; do not use python -O")
    from playwright.sync_api import sync_playwright

    target = args.html.resolve(strict=True)
    bank = materialize(json.loads(args.bank.read_text(encoding='utf-8')), args.bank.resolve().parent)
    validate(bank)
    reviewed = audit(bank, json.loads(args.review.read_text(encoding='utf-8')))
    assert reviewed['status'] == 'passed', reviewed['errors']
    count = len(bank['questions'])
    total = sum(q.get('points', 1) for q in bank['questions'])
    assert args.questions is None or args.questions == count, 'Question count argument differs from bank'
    assert args.max_points is None or args.max_points == total, 'Point total argument differs from bank'
    result.update(html_sha256=file_hash(target), content_sha256=reviewed['content_sha256'],
                  renderer_version=RENDERER_VERSION, questions=count, max_points=total,
                  prompt_images=reviewed['prompt_images'])
    errors, external = [], []
    with sync_playwright() as playwright:
        options = dict(headless=True, args=['--allow-file-access-from-files', '--no-sandbox'])
        if args.browser_executable:
            options['executable_path'] = args.browser_executable
        else:
            options['channel'] = 'chrome'
        browser = playwright.chromium.launch(**options)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        def route_request(route):
            url = route.request.url
            if not url.startswith(('file:', 'data:', 'about:', 'blob:')):
                external.append(url)
                route.abort()
            else:
                route.continue_()
        context.route('**/*', route_request)
        page = context.new_page()
        page.on('pageerror', lambda err: errors.append(str(err)))
        response = page.goto(target.as_uri())
        assert response is not None and response.ok, response
        assert page.locator('h1').inner_text() == bank['title'], 'Visible title differs from bank'
        assert bank.get('banner') is None or bank['banner'] in page.locator('header').inner_text(), 'Visible banner differs from bank'
        assert bank['version'] in page.locator('header').inner_text(), 'Content version not visible'
        assert page.locator('base').count() == 0, 'Base URL redirection is not offline content'
        assert page.locator('article.card').count() == count
        assert page.evaluate('QUESTIONS') == bank['questions'], 'Rendered questions differ from reviewed bank'
        assert page.evaluate('CONTENT_METADATA.content_reviewed') is True
        assert page.evaluate('CONTENT_METADATA.content_sha256') == reviewed['content_sha256']
        assert page.locator('.feedback .result').count() == 0
        assert page.locator('#submit').is_disabled()
        assert page.evaluate('new Set([...document.querySelectorAll("[id]")].map(e=>e.id)).size === document.querySelectorAll("[id]").length'), 'Duplicate element IDs'
        def images(selector, expected):
            items = page.locator(selector)
            assert items.count() == expected, f'Image count: {selector}'
            for item in items.all():
                item.scroll_into_view_if_needed()
                item.evaluate('(img) => new Promise((resolve,reject) => {if(img.complete) return img.naturalWidth>0?resolve():reject("broken image");img.onload=resolve;img.onerror=()=>reject("broken image");})')
                assert item.evaluate('(img) => img.complete && img.naturalWidth > 0 && img.src.startsWith("data:image/")')
        images('#questions .card > .evidence img', reviewed['prompt_images'])
        result['pre_submit_images_loaded'] = True
        page.evaluate('window.scrollTo(0,0)')
        def capture(name):
            viewport = dict(page.viewport_size)
            height = page.evaluate('document.documentElement.scrollHeight')
            page.set_viewport_size({'width': viewport['width'], 'height': max(viewport['height'], height)})
            page.evaluate('window.scrollTo(0,0)')
            page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
            page.screenshot(path=str(args.evidence / name), full_page=False)
            page.set_viewport_size(viewport)
        capture('01_blank_and_figures.png')
        if reviewed['prompt_images']:
            card = page.locator('#questions .card').filter(has=page.locator('.evidence img')).first
            card.evaluate('(el) => window.scrollTo(0, Math.max(0, scrollY + el.getBoundingClientRect().top - 20))')
            page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
            card.screenshot(path=str(args.evidence / '05_question_figure.png'))
        def answer_first(number):
            box = page.locator(f'#q{number} input').first
            if box.get_attribute('type') == 'text':
                box.fill('draft answer')
            else:
                box.check()
        answer_first(1)
        if count > 1:
            assert page.locator('#submit').is_disabled()
        page.reload()
        first = page.locator('#q1 input').first
        assert (first.input_value() == 'draft answer') if first.get_attribute('type') == 'text' else first.is_checked()
        result['draft_reload'] = True
        for number in range(2, count + 1):
            answer_first(number)
        assert page.locator('#submit').is_enabled()
        result['submit_gate'] = True
        page.locator('#submit').click()
        assert page.locator('.feedback .result').count() == count
        for feedback in page.locator('.feedback').all():
            assert feedback.get_by_text('Explanation (EN):', exact=False).count() == 1
            assert feedback.get_by_text('解析（中文）：', exact=False).count() == 1
        result['bilingual_feedback'] = True
        images('.feedback .evidence img', sum(bool(q.get('image')) for q in bank['questions']))
        result['post_submit_images_loaded'] = True
        assert page.locator('#history li').count() == 1
        capture('02_feedback.png')
        page.reload()
        assert page.locator('.feedback .result').count() == count
        page.on('dialog', lambda dialog: dialog.accept())
        page.locator('#reset').click()
        assert page.locator('#history li').count() == 1
        assert page.locator('.feedback .result').count() == 0
        assert page.locator('#submit').is_disabled()
        result['history_after_reset'] = True
        page.set_viewport_size({'width': 390, 'height': 844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        result['mobile_overflow'] = False
        images('#questions .card > .evidence img', reviewed['prompt_images'])
        capture('03_mobile.png')
        for number, q in enumerate(bank['questions'], 1):
            if q.get('type') == 'fill':
                page.locator(f'#q{number} input').first.fill(q['accept'][0])
            else:
                for index in q['answer']:
                    page.locator(f'#q{number} input').nth(index).check()
        assert page.locator('#submit').is_enabled()
        page.locator('#submit').click()
        assert page.locator('#summary').get_by_text(f'Score: {total:.2f} / {total:g}', exact=False).count() == 1
        assert page.locator('#history li').count() == 2
        result['perfect_score_tested'] = True
        capture('04_perfect_score.png')
        assert file_hash(target) == result['html_sha256'], 'HTML changed during verification'
        assert not errors, errors
        assert not external, 'External network requests attempted'
        result.update(browser_errors=errors, offline_requests_only=True)
        context.close()
        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('html', type=Path)
    parser.add_argument('--bank', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--questions', type=int)
    parser.add_argument('--max-points', type=float)
    parser.add_argument('--browser-executable')
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    receipt = args.evidence / 'verification.json'
    result = {'schema': SCHEMA, 'status': 'failed', 'errors': []}
    # Invalidate any earlier receipt before opening the browser.
    receipt.write_text(json.dumps(result) + '\n', encoding='utf-8')
    try:
        exercise(args, result)
        result['status'] = 'passed'
        receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        combined = check(args.bank, args.html, args.review, receipt)
        assert combined['status'] == 'passed', combined['errors']
    except (Exception, SystemExit) as exc:
        result.update(status='failed', errors=[str(exc)])
    receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['status'] == 'passed' else 1)


if __name__ == '__main__':
    main()
