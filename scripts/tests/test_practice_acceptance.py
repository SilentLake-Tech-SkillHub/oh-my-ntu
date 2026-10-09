"""Synthetic content only: no course questions, teacher figures or personal paths."""
import base64
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_practice_bank import audit, materialize, review_template, file_hash
from build_practice_page import render, validate
from check_practice_acceptance import check, BROWSER_CHECKS
from refresh_practice_page import refresh, score_source


def fixture():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="220" viewBox="0 0 480 220"><rect width="480" height="220" fill="white"/><text x="30" y="30" font-size="20">Two measured quantities (units)</text><line x1="60" y1="175" x2="420" y2="175" stroke="black"/><rect x="110" y="115" width="75" height="60" fill="#4779a8"/><rect x="270" y="55" width="75" height="120" fill="#4779a8"/><text x="137" y="105" font-size="20">3</text><text x="299" y="45" font-size="20">6</text><text x="137" y="205" font-size="20">A</text><text x="299" y="205" font-size="20">B</text></svg>'
    image = 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode()
    common = dict(kind='concept', requires_figure=False, points=2, source='Synthetic fixture specification', topic='Elementary comparisons')
    bank = dict(course='DEMO', paper_id='Acceptance', version='v1', title='Synthetic acceptance preview',
                banner='Synthetic fixture; local practice only', requirements=dict(allow_code=False, minimum_visual_questions=1),
                questions=[
                    dict(common, type='fill', prompt='A triangle has how many sides? Enter an integer.', accept=['3'], en='A triangle has three sides by definition.', zh='三角形的定义包含三条边。'),
                    dict(common, kind='analysis', requires_figure=True, prompt='The chart shows measured quantities in the same units. Which category has the greater quantity?', options=['A', 'B'], answer=[1], prompt_image=image, prompt_image_caption='Measured quantities for categories A and B.', image=image, image_caption='The measurement chart used for the comparison.', en='B is 6 units and A is 3, so B is greater.', zh='B 为 6，A 为 3，因此 B 更大。'),
                    dict(common, prompt='Which of these numbers are strictly greater than zero? Select all that apply.', options=['1', '2', '-1'], answer=[0, 1], en='1 and 2 are positive; -1 is negative.', zh='1 和 2 是正数，-1 是负数。')])
    return bank


def reviewed(bank):
    # Specific reasons for these three hand-reviewed synthetic questions only.
    review = review_template(bank)
    review['reviewer'] = 'Synthetic fixture author review'
    conditions = ['The prompt specifies a triangle and asks for its side count as an integer.',
                  'The embedded chart labels both categories, quantities and shared units.',
                  'Strictly greater than zero distinguishes positive from negative values.']
    answers = ['Three sides is the defining property; accepted response 3 is exact.',
               'B=6 and A=3; option B is greater and option A is smaller.',
               'Options 1 and 2 satisfy >0; option -1 does not.']
    for i, r in enumerate(review['questions']):
        r.update(self_contained=True, source_verified=True, answer_verified=True, contains_code=False,
                 conditions_note=conditions[i], source_note='Checked against the synthetic specification and its stated values.', answer_note=answers[i])
        if bank['questions'][i].get('prompt_image'):
            r.update(figure_not_answer_leaking=True, figure_note='The figure supplies A=3 and B=6, uses labelled units, readable contrasting bars, and does not mark a correct option.')
    return review


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.bank = fixture()
        self.review = reviewed(self.bank)

    def test_synthetic_content_passes(self):
        self.assertEqual(audit(self.bank, self.review)['status'], 'passed')
        self.assertIn('CONTENT_METADATA', render(self.bank, review=self.review))

    def test_classroom_dependency_fails_even_with_fresh_review(self):
        self.bank['questions'][1]['prompt'] = "Which option follows the lecture's golden rule?"
        self.assertTrue(audit(self.bank, reviewed(self.bank))['automatic_errors'])

    def test_necessary_figure_missing(self):
        del self.bank['questions'][1]['prompt_image']
        self.assertTrue(audit(self.bank, reviewed(self.bank))['automatic_errors'])

    def test_decorative_figure_does_not_count(self):
        self.bank['questions'][1]['requires_figure'] = False
        self.assertEqual(audit(self.bank, reviewed(self.bank))['visual_questions'], 0)
        self.assertTrue(audit(self.bank, reviewed(self.bank))['automatic_errors'])

    def test_ordinary_prose_and_mathematical_notation_are_not_code(self):
        self.bank['questions'][2]['prompt'] = 'A data operator may import data. If x = 1, which listed numbers are strictly greater than zero? Select all that apply.'
        self.assertFalse(audit(self.bank, reviewed(self.bank))['automatic_errors'])

    def test_task_code_ban(self):
        # Type declaration only; no code question is authored.
        self.bank['questions'][0]['kind'] = 'code'
        self.assertTrue(audit(self.bank, reviewed(self.bank))['automatic_errors'])

    def test_code_in_picture_review_is_rejected(self):
        self.review['questions'][1]['contains_code'] = True
        self.assertEqual(audit(self.bank, self.review)['status'], 'failed')

    def test_changed_prompt_option_image_or_requirements_invalidates_review(self):
        variants = []
        for field, value in [('prompt', 'A revised complete question.'), ('options', ['B', 'A']), ('prompt_image', fixture()['questions'][1]['prompt_image'] + 'x')]:
            bank = copy.deepcopy(self.bank)
            bank['questions'][1][field] = value
            variants.append(bank)
        bank = copy.deepcopy(self.bank)
        bank['requirements']['allow_code'] = True
        variants.append(bank)
        for bank in variants:
            with self.subTest(bank=bank['requirements']):
                self.assertEqual(audit(bank, self.review)['status'], 'failed')

    def test_image_bytes_are_part_of_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            image = base / 'plot.svg'
            image.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>')
            self.bank['questions'][1]['prompt_image'] = 'plot.svg'
            embedded = materialize(self.bank, base)
            review = reviewed(embedded)
            image.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"/>')
            self.assertEqual(audit(materialize(self.bank, base), review)['status'], 'failed')

    def test_default_requires_review_and_draft_closes_submit(self):
        with self.assertRaises(ValueError):
            render(self.bank)
        draft = render(self.bank, draft=True)
        self.assertIn('Draft preview', draft)
        self.assertIn('"content_reviewed": false', draft)
        self.assertIn('disabled=!CONTENT_METADATA.content_reviewed', draft)

    def test_invalid_points_and_answer_indices(self):
        for value in [True, 0.5, -1, 99]:
            bank = copy.deepcopy(self.bank)
            bank['questions'][1]['answer'] = [value]
            with self.assertRaises(SystemExit):
                validate(bank)
        for value in [True, 0, -1, float('inf'), float('nan')]:
            bank = copy.deepcopy(self.bank)
            bank['questions'][1]['points'] = value
            with self.assertRaises(SystemExit):
                validate(bank)

    def test_remote_or_corrupt_images_fail(self):
        for value in ['https://example.invalid/plot.png', 'data:image/png;base64,eA==']:
            bank = copy.deepcopy(self.bank)
            bank['questions'][1]['prompt_image'] = value
            with self.assertRaises(ValueError):
                materialize(bank, Path('.'))

    def test_refresh_preserves_scoring_and_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            old = render(self.bank, review=self.review)
            old = old.replace('function questionImage(q){', 'function retiredImage(q){').replace('${questionImage(q)}', '')
            html = base / 'old.html'
            html.write_text(old)
            original = html.read_bytes()
            bank = copy.deepcopy(self.bank)
            bank['version'] = 'v2'
            bank['questions'][1]['prompt'] += ' Select one option.'
            (base / 'bank.json').write_text(json.dumps(bank))
            (base / 'review.json').write_text(json.dumps(reviewed(bank)))
            result = refresh(html, base / 'bank.json', base / 'review.json', base / 'backup.html')
            self.assertEqual(result['status'], 'refreshed_pending_browser')
            self.assertEqual((base / 'backup.html').read_bytes(), original)
            self.assertEqual(score_source(old), score_source(html.read_text()))
            self.assertIn('${questionImage(q)}', html.read_text())

    def test_unknown_renderer_or_type_change_leaves_original(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for variant in ['unknown', 'types', 'version']:
                old = render(self.bank, review=self.review)
                bank = copy.deepcopy(self.bank)
                if variant != 'version':
                    bank['version'] = 'v2'
                if variant == 'unknown':
                    old = old.replace('<p>${rich(q.prompt)}</p>', '<p>unrecognized layout</p>')
                if variant == 'types':
                    bank['questions'][2]['answer'] = [0]
                html = base / 'old.html'
                html.write_text(old)
                (base / 'bank.json').write_text(json.dumps(bank))
                (base / 'review.json').write_text(json.dumps(reviewed(bank)))
                with self.assertRaises(ValueError):
                    refresh(html, base / 'bank.json', base / 'review.json', base / 'backup.html')
                self.assertEqual(html.read_text(), old)
                self.assertFalse((base / 'backup.html').exists())

    def test_stale_browser_receipt_does_not_pass_final_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / 'bank.json').write_text(json.dumps(self.bank))
            (base / 'review.json').write_text(json.dumps(self.review))
            html = base / 'paper.html'
            html.write_text(render(self.bank, review=self.review))
            # Receipt-shaped stub for hash-binding tests, not browser evidence.
            receipt = dict(schema='ntu-practice-acceptance-v1', status='passed', html_sha256=file_hash(html),
                           content_sha256=self.review['content_sha256'], renderer_version='2026.10.10.1',
                           questions=3, max_points=6, prompt_images=1, mobile_overflow=False, browser_errors=[])
            receipt.update({key: True for key in BROWSER_CHECKS})
            path = base / 'verification.json'
            path.write_text(json.dumps(receipt))
            self.assertEqual(check(base / 'bank.json', html, base / 'review.json', path)['status'], 'passed')
            html.write_text(html.read_text() + '\n<!-- changed bytes -->')
            self.assertEqual(check(base / 'bank.json', html, base / 'review.json', path)['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
