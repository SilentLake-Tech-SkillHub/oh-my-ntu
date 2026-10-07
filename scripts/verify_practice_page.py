#!/usr/bin/env python3
"""Exercise one offline assessment in Chrome and capture visible evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('html', type=Path)
    parser.add_argument('--questions', type=int, required=True)
    parser.add_argument('--max-points', type=int)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    target = args.html.resolve(strict=True)
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            headless=True,
            args=['--allow-file-access-from-files', '--no-sandbox'],
        )
        context = browser.new_context(viewport={'width': 1440, 'height': 900})
        page = context.new_page()
        page.on('pageerror', lambda err: errors.append(str(err)))
        response = page.goto(target.as_uri())
        assert response is not None and response.ok, response
        assert page.locator('article.card').count() == args.questions
        assert page.locator('.feedback .result').count() == 0
        assert page.locator('#submit').is_disabled()
        page.screenshot(path=str(evidence / '01_空白卷.png'))
        def answer_first(number: int) -> None:
            box = page.locator(f'#q{number} input').first
            if box.get_attribute('type') == 'text':
                box.fill('draft answer')
            else:
                box.check()

        answer_first(1)
        if args.questions > 1:
            assert page.locator('#submit').is_disabled()
        page.reload()
        first = page.locator('#q1 input').first
        assert (first.input_value() == 'draft answer') if first.get_attribute('type') == 'text' else first.is_checked()
        for number in range(2, args.questions + 1):
            answer_first(number)
        assert page.locator('#submit').is_enabled()
        page.screenshot(path=str(evidence / '02_全答待提交.png'))
        page.locator('#submit').click()
        assert page.locator('.feedback .result').count() == args.questions
        if args.max_points is not None:
            assert page.locator('#summary').get_by_text(f'/ {args.max_points}', exact=False).count() == 1
        assert page.locator('#history li').count() == 1
        assert page.locator('.feedback').first.get_by_text('Correct answer:').count() == 1
        page.screenshot(path=str(evidence / '03_提交与双语解析.png'))
        page.reload()
        assert page.locator('.feedback .result').count() == args.questions
        page.on('dialog', lambda dialog: dialog.accept())
        page.locator('#reset').click()
        assert page.locator('#history li').count() == 1
        assert page.locator('.feedback .result').count() == 0
        assert page.locator('#submit').is_disabled()
        page.set_viewport_size({'width': 390, 'height': 844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(evidence / '04_手机空白卷.png'))
        if args.max_points is not None:
            keys = page.evaluate("QUESTIONS.map(q => q.type === 'fill' ? {fill: q.accept[0]} : {idx: q.answer})")
            for number, key in enumerate(keys, 1):
                if 'fill' in key:
                    page.locator(f'#q{number} input').first.fill(key['fill'])
                else:
                    for index in key['idx']:
                        page.locator(f'#q{number} input').nth(index).check()
            assert page.locator('#submit').is_enabled()
            page.locator('#submit').click()
            assert page.locator('#summary').get_by_text(
                f'Score: {args.max_points:.2f} / {args.max_points}', exact=False
            ).count() == 1
            assert page.locator('#history li').count() == 2
            page.screenshot(path=str(evidence / '05_满分评分.png'))
        assert not errors, errors
        context.close()
        browser.close()
    result = {'html': str(target), 'questions': args.questions, 'browser_errors': errors,
              'draft_reload': True, 'submit_gate': True, 'bilingual_feedback': True,
              'history_after_reset': True, 'perfect_score_tested': args.max_points is not None,
              'mobile_overflow': False}
    (evidence / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
