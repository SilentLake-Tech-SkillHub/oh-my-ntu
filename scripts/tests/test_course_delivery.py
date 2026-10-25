"""Behavioral regressions using isolated synthetic documents and receipt-shaped stubs.

No fixture is an actual course source, user review, or browser receipt.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_course_delivery import (SCHEMA, REVIEW_CHECKS, check, filename, title,
                                   html_identity, review_template, sha)
from build_practice_page import render
from audit_practice_bank import content_identity, artifact_bank
from check_practice_acceptance import BROWSER_CHECKS
from test_practice_acceptance import fixture as practice_fixture, reviewed
from refresh_practice_page import refresh


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="course-delivery-test-")
        self.base = Path(self.tmp.name)
        self.root = self.base / "course"
        self.work = self.base / "work"
        for p in (self.root / "active", self.work):
            p.mkdir(parents=True)
        self.manifest = self.work / "delivery.json"
        self.review = self.work / "review.json"
        self.ident = dict(collection_id="demo-term-assessment2", subject_id="assessment2", artifact_id="notes-v1",
                          course="DEMO", subject_label="Quiz2", purpose="完整复习", variant="总册", scope_revision="scope1",
                          scope_label="第4-6章", date="20260102", revision="v1", review_state="审阅版", presentation=dict(topic="算法基础", context="Quiz2"))
        self.m = dict(schema=SCHEMA, collection_id=self.ident["collection_id"], course="DEMO", period="demo-term",
                      subject=dict(id="assessment2", label="Quiz2", provenance=dict(kind="user_confirmed", reference="Synthetic request", locator="fixture specification")),
                      scope=dict(revision="scope1", label="第4-6章", basis="Synthetic scope, not a real course"),
                      operation="create", inventory_roots=["active"], active_dirs=["active"],
                      required=[["完整复习", "总册", ".html"]], artifacts=[], entrypoints=["index.html"])
        self.add_current(self.ident)
        self.entry()

    def tearDown(self):
        self.tmp.cleanup()

    def add_current(self, ident, suffix=".html"):
        ident = copy.deepcopy(ident)
        relative = "active/" + filename(ident, suffix)
        p = self.root / relative
        if suffix == ".html":
            p.write_text(f'<!doctype html><html><title>{title(ident)}</title>{html_identity(ident)}<h1>{title(ident)}</h1><p>Synthetic text.</p></html>')
        elif suffix == ".md":
            p.write_text('<!-- course-delivery-identity ' + json.dumps(ident) + ' -->\n# ' + title(ident) + '\nSynthetic text.\n')
        elif suffix == ".ipynb":
            p.write_text(json.dumps(dict(nbformat=4, nbformat_minor=5, metadata=dict(course_delivery=ident),
                                        cells=[dict(cell_type="markdown", metadata={}, source=["# " + title(ident)])])))
        artifact = dict(id=ident["artifact_id"], kind="document", identity=ident, path=relative, sha256=sha(p), status="current")
        self.m["artifacts"].append(artifact)
        return artifact

    def entry(self, extra=""):
        links = "".join(f'<a href="{a["path"]}">{a["id"]}</a>' for a in self.m["artifacts"] if a["status"] == "current")
        (self.root / "index.html").write_text('<!doctype html><html><title>Study index</title>'
            f'<section data-delivery-collection="{self.m["collection_id"]}" data-delivery-status="current">{links}</section>{extra}</html>')

    def save(self, review=True):
        self.manifest.write_text(json.dumps(self.m, ensure_ascii=False))
        if review:
            r = review_template(self.manifest, self.root)
            r["reviewer"] = "Synthetic fixture test stub; not an actual course review"
            for key in REVIEW_CHECKS:
                r["checks"][key] = dict(passed=True, note=f"Synthetic scenario specification checked for {key}.")
            for a in self.m["artifacts"]:
                r["usability"][a["id"]] = dict(topic=a["identity"]["presentation"]["topic"], purpose=a["identity"]["purpose"],
                    open_with="Synthetic browser/editor", first_action="Read the labelled synthetic text", evidence_locator="Fixture DOM and filenames; not real usability evidence")
            self.review.write_text(json.dumps(r))

    def run_gate(self, previous=None):
        return check(self.manifest, self.root, self.review, previous)

    def assert_fails(self, needle, previous=None):
        result = self.run_gate(previous)
        self.assertEqual(result["status"], "failed")
        self.assertIn(needle, "; ".join(result["errors"]))

    def prepare_update(self):
        self.save()
        old_manifest = self.work / "before.json"
        old_manifest.write_bytes(self.manifest.read_bytes())
        old = self.m["artifacts"][0]
        (self.root / old["path"]).unlink()
        self.m["artifacts"].clear()
        newer = copy.deepcopy(self.ident)
        newer.update(artifact_id="notes-v2", revision="v2", date="20260103")
        newer["presentation"]["topic"] = "算法复习与重点"
        self.add_current(newer)
        self.m.update(operation="update", previous_sha256=sha(old_manifest))
        self.entry()
        self.save()
        return old_manifest

    def test_complete_new_collection_passes(self):
        self.save()
        self.assertEqual(self.run_gate()["status"], "passed")

    def test_missing_review_cannot_pass(self):
        self.save()
        r = check(self.manifest, self.root)
        self.assertEqual(r["status"], "failed")
        self.assertFalse(r["automatic_errors"])

    def test_template_is_unapproved(self):
        self.save(False)
        r = review_template(self.manifest, self.root)
        self.assertTrue(all(not v["passed"] for v in r["checks"].values()))
        self.assertFalse(r["reviewer"])

    def test_all_supported_text_formats_are_bound(self):
        for suffix in (".md", ".ipynb"):
            ident = copy.deepcopy(self.ident)
            ident["artifact_id"] += suffix
            self.add_current(ident, suffix)
            self.m["required"].append(["完整复习", "总册", suffix])
        self.entry()
        self.save()
        self.assertEqual(self.run_gate()["status"], "passed")

    def test_different_papers_are_not_duplicate_versions(self):
        for variant in ("A", "B", "C"):
            ident = copy.deepcopy(self.ident)
            ident.update(artifact_id="mock-" + variant, purpose="本地模拟", variant=variant)
            self.add_current(ident)
            self.m["required"].append(["本地模拟", variant, ".html"])
        self.entry()
        self.save()
        self.assertEqual(self.run_gate()["status"], "passed")

    def test_two_current_revisions_fail(self):
        newer = copy.deepcopy(self.ident)
        newer.update(artifact_id="notes-v2", revision="v2")
        self.add_current(newer)
        self.entry()
        self.save()
        self.assert_fails("exactly one current revision")

    def test_old_revision_must_disappear_instead_of_being_archived(self):
        previous = self.prepare_update()
        prior = json.loads(previous.read_text())["artifacts"][0]
        (self.root / prior["path"]).write_text("Leftover original revision")
        self.save()
        self.assert_fails("obsolete revision still exists", previous)

    def test_empty_archive_directory_also_fails(self):
        (self.root / "active" / "99_历史版本").mkdir()
        self.save()
        self.assert_fails("version archive remains")

    def test_archive_cannot_be_hidden_by_exclusions(self):
        (self.root / "active" / "archive").mkdir()
        self.m["exclusions"] = [dict(path="active/archive", reason="Invalid attempt to hide previous revisions")]
        self.save()
        self.assert_fails("cannot exclude a version archive")

    def test_old_historical_directory_configuration_fails(self):
        self.m["historical_dirs"] = ["active/history"]
        self.save()
        self.assert_fails("forbids historical directories")

    def test_removed_inventory_directory_must_really_be_gone(self):
        previous = self.prepare_update()
        before = json.loads(previous.read_text())
        before["inventory_roots"].append("old-area")
        previous.write_text(json.dumps(before))
        self.m["previous_sha256"] = sha(previous)
        self.m["inventory_removals"] = [dict(path="old-area", reason="Old derivative versions removed")]
        self.save()
        self.assertEqual(self.run_gate(previous)["status"], "passed")
        (self.root / "old-area").mkdir()
        self.save()
        self.assert_fails("removed inventory root still exists", previous)

    def test_missing_required_paper_fails(self):
        self.m["required"].append(["本地模拟", "B", ".html"])
        self.save()
        self.assert_fails("exactly one current revision")

    def test_filename_drift_fails_with_fresh_review(self):
        a = self.m["artifacts"][0]
        p = self.root / a["path"]
        q = p.with_name(p.name.replace("Quiz2", "Final"))
        p.rename(q)
        a["path"] = q.relative_to(self.root).as_posix()
        self.entry()
        self.save()
        self.assert_fails("filename differs")

    def test_exam_folder_drift_fails_even_with_correct_filename(self):
        (self.root / "active").rename(self.root / "Final")
        self.m["inventory_roots"][0] = "Final"
        self.m["active_dirs"] = ["Final"]
        self.m["artifacts"][0]["path"] = self.m["artifacts"][0]["path"].replace("active/", "Final/")
        self.entry()
        self.save()
        self.assert_fails("exam directory name differs")

    def test_title_drift_fails_even_after_hash_and_review_update(self):
        a = self.m["artifacts"][0]
        p = self.root / a["path"]
        p.write_text(p.read_text().replace('<h1>' + title(self.ident), '<h1>Different exam'))
        a["sha256"] = sha(p)
        self.save()
        self.assert_fails("title and h1 differ")

    def test_scope_drift_fails_with_fresh_review(self):
        self.m["scope"].update(revision="scope2", label="第4-5章")
        self.save()
        self.assert_fails("scope_revision differs")

    def test_omitted_old_file_is_found_by_real_directory_scan(self):
        (self.root / "active" / "old-paper.html").write_text("Old exam")
        self.save()
        self.assert_fails("unregistered file")

    def test_learning_page_cannot_be_hidden_as_resource(self):
        p = self.root / "active" / "old-paper.html"
        p.write_text("Old exam")
        self.m["resources"] = [dict(path="active/old-paper.html", sha256=sha(p), reason="Synthetic invalid resource")]
        self.save()
        self.assert_fails("learning pages must be registered")

    def test_update_passes_with_latest_revision_only(self):
        previous = self.prepare_update()
        self.assertEqual(self.run_gate(previous)["status"], "passed")
        self.assertEqual(len(list((self.root / "active").glob("*.html"))), 1)

    def test_history_navigation_is_forbidden_even_without_old_files(self):
        previous = self.prepare_update()
        self.entry(f'<details data-delivery-collection="{self.m["collection_id"]}" data-delivery-status="history"><summary>Old versions</summary></details>')
        self.save()
        self.assert_fails("history/draft navigation section forbidden", previous)

    def test_registered_superseded_copy_fails_even_in_archive(self):
        previous = self.prepare_update()
        prior = json.loads(previous.read_text())["artifacts"][0]
        (self.root / "active" / "history").mkdir()
        old = self.root / "active/history/old.html"
        old.write_text("Synthetic previous revision")
        prior.update(status="superseded", path="active/history/old.html", sha256=sha(old))
        self.m["artifacts"].append(prior)
        self.save()
        self.assert_fails("latest-only delivery permits current artifacts only", previous)

    def test_update_cannot_omit_baseline(self):
        self.prepare_update()
        self.assert_fails("requires --previous")

    def test_changed_content_cannot_reuse_original_revision_id(self):
        previous = self.prepare_update()
        self.m["artifacts"][0]["id"] = "notes-v1"
        self.m["artifacts"][0]["identity"]["artifact_id"] = "notes-v1"
        self.save()
        self.assert_fails("changed content must receive a new revision id", previous)

    def test_update_cannot_hide_previous_entrypoint(self):
        previous = self.prepare_update()
        (self.root / "other.html").write_bytes((self.root / "index.html").read_bytes())
        self.m["entrypoints"] = ["other.html"]
        self.save()
        self.assert_fails("previous entrypoint omitted", previous)

    def test_baseline_hash_is_bound(self):
        previous = self.prepare_update()
        previous.write_text(previous.read_text() + "\n")
        self.assert_fails("previous manifest fingerprint differs", previous)

    def test_update_cannot_drop_an_old_inventory_directory(self):
        previous = self.prepare_update()
        old = json.loads(previous.read_text())
        (self.root / "old-area").mkdir()
        old["inventory_roots"].append("old-area")
        previous.write_text(json.dumps(old))
        self.m["previous_sha256"] = sha(previous)
        self.save()
        self.assert_fails("previous inventory root silently omitted", previous)

    def test_scope_change_requires_new_scope_revision(self):
        previous = self.prepare_update()
        old = json.loads(previous.read_text())
        old["scope"]["label"] = "先前范围"
        previous.write_text(json.dumps(old))
        self.m["previous_sha256"] = sha(previous)
        self.save()
        self.assert_fails("changed scope must advance scope revision", previous)

    def test_stale_review_on_changed_index_fails(self):
        self.save()
        p = self.root / "index.html"
        p.write_text(p.read_text() + "<p>New unreviewed claim</p>")
        self.assert_fails("review omits a current artifact")

    def test_missing_or_duplicate_current_navigation_blocks_fail(self):
        self.save()
        p = self.root / "index.html"
        source = p.read_text()
        for updated in (source.replace('data-delivery-status="current"', 'data-delivery-status="history"'), source + source):
            p.write_text(updated)
            self.save()
            self.assert_fails("exactly one current collection block")

    def test_all_current_materials_must_be_discoverable(self):
        self.entry()
        p = self.root / "index.html"
        p.write_text(p.read_text().replace('<a href=', '<span data-unused=').replace('</a>', '</span>'))
        self.save()
        self.assert_fails("complete current set")

    def test_dependency_cannot_point_to_removed_revision(self):
        previous = self.prepare_update()
        self.m["artifacts"][0]["depends_on"] = ["notes-v1"]
        self.save()
        self.assert_fails("unknown dependency", previous)

    def test_bad_links_fail(self):
        for link in ("missing.html", "../outside.html", "%2e%2e/outside.html"):
            self.entry(f'<a href="{link}">Synthetic bad link</a>')
            self.save()
            result = self.run_gate()
            self.assertEqual(result["status"], "failed")

    def test_symlink_inventory_rejected(self):
        (self.root / "active" / "alias.html").symlink_to(self.root / self.m["artifacts"][0]["path"])
        self.save()
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.run_gate()

    def test_one_practice_cannot_reuse_another_pages_receipt(self):
        a = self.m["artifacts"][0]
        a["kind"] = "practice"
        self.save()
        self.assert_fails("practice evidence missing/invalid")

    def practice_collection(self):
        a = self.m["artifacts"][0]
        bank = practice_fixture()
        bank.update(delivery_identity=copy.deepcopy(a["identity"]), title=title(a["identity"]))
        qreview = reviewed(bank)
        p = self.root / a["path"]
        p.write_text(render(bank, review=qreview))
        a.update(kind="practice", sha256=sha(p), practice_check=dict(bank="bank.json", review="qreview.json", verification="browser.json"))
        (self.work / "bank.json").write_text(json.dumps(bank))
        (self.work / "qreview.json").write_text(json.dumps(qreview))
        # This is deliberately a test stub, never claimed as a real browser run.
        receipt = dict(schema="ntu-practice-acceptance-v1", status="passed", html_sha256=sha(p),
                       content_sha256=qreview["content_sha256"], renderer_version="2026.10.10.1",
                       questions=3, max_points=6, prompt_images=1, mobile_overflow=False, browser_errors=[])
        receipt.update({key: True for key in BROWSER_CHECKS})
        (self.work / "browser.json").write_text(json.dumps(receipt))
        self.save()
        return p

    def practice_cli(self, args):
        script = Path(__file__).resolve().parents[1] / "check_practice_acceptance.py"
        p = self.root / self.m["artifacts"][0]["path"]
        return subprocess.run([sys.executable, str(script), str(self.work / "bank.json"), str(p),
            "--review", str(self.work / "qreview.json"), "--verification", str(self.work / "browser.json"),
            "--report", str(self.work / "practice-result.json"), *args], capture_output=True, text=True)

    def test_integrated_cli_requires_collection_by_default(self):
        self.practice_collection()
        result = self.practice_cli([])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Delivery closeout requires", result.stdout)

    def test_page_only_is_explicit_and_cannot_claim_collection(self):
        self.practice_collection()
        result = self.practice_cli(["--page-only"])
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads((self.work / "practice-result.json").read_text())
        self.assertEqual(report["scope"], "content_review_and_browser_acceptance")
        self.assertEqual(report["delivery_acceptance"], "not_checked_by_page_check")

    def test_integrated_collection_and_page_cli_pass_together(self):
        self.practice_collection()
        result = self.practice_cli(["--manifest", str(self.manifest), "--root", str(self.root), "--delivery-review", str(self.review)])
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads((self.work / "practice-result.json").read_text())
        self.assertEqual(report["scope"], "practice_content_browser_and_collection_delivery")
        self.assertEqual(report["delivery_acceptance"], "passed")

    def test_collection_rechecks_each_practice_receipt_hash(self):
        self.practice_collection()
        p = self.work / "browser.json"
        receipt = json.loads(p.read_text())
        receipt["html_sha256"] = "0" * 64
        p.write_text(json.dumps(receipt))
        self.assert_fails("practice content/browser acceptance failed")

    def test_practice_page_cannot_skip_its_gate_by_changing_kind(self):
        self.practice_collection()
        self.m["artifacts"][0]["kind"] = "document"
        del self.m["artifacts"][0]["practice_check"]
        self.save()
        self.assert_fails("practice renderer cannot be declared")

    def test_new_revision_must_advance_not_just_rename(self):
        previous = self.prepare_update()
        a = self.m["artifacts"][0]
        (self.root / a["path"]).unlink()
        self.m["artifacts"].clear()
        self.add_current(dict(a["identity"], revision="v1"))
        self.entry()
        self.save()
        self.assert_fails("revision did not advance", previous)

    def test_identity_is_bound_to_question_review_and_actual_page(self):
        bank = practice_fixture()
        ident = copy.deepcopy(self.ident)
        bank.update(delivery_identity=ident, course=ident["course"], title=title(ident))
        review = reviewed(bank)
        page = render(bank, review=review)
        self.assertEqual(content_identity(artifact_bank(page)), content_identity(bank))
        bank["delivery_identity"]["subject_id"] = "different-subject"
        with self.assertRaisesRegex(ValueError, "Content acceptance failed"):
            render(bank, review=review)

    def test_builder_cli_rejects_missing_structured_identity(self):
        bank = practice_fixture()
        (self.work / "bank.json").write_text(json.dumps(bank))
        (self.work / "qreview.json").write_text(json.dumps(reviewed(bank)))
        script = Path(__file__).resolve().parents[1] / "build_practice_page.py"
        result = subprocess.run([sys.executable, str(script), str(self.work / "bank.json"), str(self.work / "paper.html"), "--review", str(self.work / "qreview.json")], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.work / "paper.html").exists())

    def test_refresh_cli_path_creates_new_revision_and_preserves_original(self):
        bank = practice_fixture()
        old = self.work / "old.html"
        old.write_text(render(bank, review=reviewed(bank)))
        original = old.read_bytes()
        ident = dict(self.ident, revision="v2")
        bank.update(delivery_identity=ident, title=title(ident), version="v2")
        (self.work / "bank.json").write_text(json.dumps(bank))
        (self.work / "qreview.json").write_text(json.dumps(reviewed(bank)))
        out = self.work / filename(ident, ".html")
        result = refresh(old, self.work / "bank.json", self.work / "qreview.json", self.work / "backup.html", out)
        self.assertTrue(result["original_unchanged"])
        self.assertEqual(old.read_bytes(), original)
        self.assertEqual((self.work / "backup.html").read_bytes(), original)
        self.assertIn(html_identity(ident), out.read_text())
        self.assertEqual(result["delivery_acceptance"], "pending")

    def test_refresh_does_not_require_a_saved_previous_version(self):
        bank = practice_fixture()
        original = self.work / "source.html"
        original.write_text(render(bank, review=reviewed(bank)))
        ident = dict(self.ident, revision="v2")
        bank.update(delivery_identity=ident, title=title(ident), version="v2")
        (self.work / "bank.json").write_text(json.dumps(bank))
        (self.work / "qreview.json").write_text(json.dumps(reviewed(bank)))
        result = refresh(original, self.work / "bank.json", self.work / "qreview.json", None,
                         self.work / filename(ident, ".html"))
        self.assertIsNone(result["backup_sha256"])
        self.assertEqual(result["status"], "staged_revision_pending_replacement")
        self.assertEqual(result["obsolete_cleanup"], "required_before_delivery")

    def test_read_only_cli_refuses_to_write_report_into_course(self):
        self.save()
        report = self.root / "danger.json"
        script = Path(__file__).resolve().parents[1] / "check_course_delivery.py"
        result = subprocess.run([sys.executable, str(script), str(self.manifest), "--root", str(self.root), "--report", str(report)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report.exists())

    def test_cli_failure_is_nonzero_and_does_not_change_documents(self):
        self.save()
        before = {p.relative_to(self.root).as_posix(): sha(p) for p in self.root.rglob("*") if p.is_file()}
        script = Path(__file__).resolve().parents[1] / "check_course_delivery.py"
        result = subprocess.run([sys.executable, str(script), str(self.manifest), "--root", str(self.root), "--report", str(self.work / "report.json")], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, {p.relative_to(self.root).as_posix(): sha(p) for p in self.root.rglob("*") if p.is_file()})


if __name__ == "__main__":
    unittest.main()
