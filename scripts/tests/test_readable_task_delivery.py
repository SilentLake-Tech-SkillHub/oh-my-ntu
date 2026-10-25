"""Synthetic regressions for directory usability and complete requested scope.

Review stubs below are test inputs, not evidence of a real user/content review.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_course_delivery as delivery
import check_course_task as task
import test_course_delivery as existing


class ReadableDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = existing.DeliveryTests()
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def test_week_six_carriers_are_readable_and_share_topic(self):
        ident = dict(self.fixture.ident, purpose="逐页中英对照",
                     presentation=dict(topic="生成式AI课件", sequence="01"))
        self.assertEqual(delivery.filename(ident, ".html"), "01_生成式AI课件_逐页中英对照_阅读版.html")
        self.assertEqual(delivery.filename(ident, ".ipynb"), "01_生成式AI课件_逐页中英对照_可编辑笔记.ipynb")
        revised = dict(ident, date="20261231", revision="v8", artifact_id="reader-v8")
        self.assertEqual(delivery.filename(ident, ".html"), delivery.filename(revised, ".html"))
        self.assertNotEqual(delivery.html_identity(ident), delivery.html_identity(revised))

    def test_code_explanation_and_slides_cannot_be_confused(self):
        slides = dict(self.fixture.ident, purpose="逐页中英对照", presentation=dict(topic="生成式AI课件", sequence="01"))
        code = dict(slides, purpose="代码讲解", presentation=dict(topic="大模型预训练与LoRA微调", sequence="02"))
        self.assertNotEqual(delivery.filename(slides, ".html"), delivery.filename(code, ".html"))
        self.assertTrue(delivery.filename(code, ".html").startswith("02_大模型预训练与LoRA微调_代码讲解"))

    def test_required_context_and_real_class_date_are_supported(self):
        ident = dict(self.fixture.ident, presentation=dict(topic="数据治理", context="周二20260102", carriers={".html": "作答页"}))
        self.assertEqual(delivery.filename(ident, ".html"), "周二20260102_数据治理_完整复习_作答页.html")
        english = dict(ident, presentation=dict(topic="Linear Regression", context="Quiz2"))
        self.assertIn("Linear Regression", delivery.filename(english, ".html"))

    def test_missing_or_opaque_presentation_is_not_silently_accepted(self):
        for value in (None, dict(topic="ch6"), dict(topic="20260102版本"), dict(topic="../outside")):
            ident = dict(self.fixture.ident, presentation=value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                delivery.filename(ident, ".html")

    def test_paired_carriers_have_explicit_relationship_and_complete_coverage(self):
        f = self.fixture
        notebook = dict(f.ident, artifact_id="notebook-v1")
        f.add_current(notebook, ".ipynb")
        f.m["required"].append(["完整复习", "总册", ".ipynb"])
        f.m["objects"] = [dict(id="lesson-six", artifacts=["notes-v1", "notebook-v1"])]
        f.entry(); f.save()
        self.assertEqual(f.run_gate()["status"], "passed")
        f.m["objects"][0]["artifacts"].pop()
        f.save()
        f.assert_fails("object map omits")

    def test_wrong_notebook_cannot_be_grouped_under_same_topic(self):
        f = self.fixture
        other = copy.deepcopy(f.ident)
        other.update(artifact_id="other-notebook")
        other["presentation"]["topic"] = "文本预处理"
        f.add_current(other, ".ipynb")
        f.m["required"].append(["完整复习", "总册", ".ipynb"])
        f.m["objects"] = [dict(id="lesson-six", artifacts=["notes-v1", "other-notebook"])]
        f.entry(); f.save()
        f.assert_fails("paired carriers need")

    def test_multiple_notebooks_can_feed_one_aggregate_without_forced_pairs(self):
        f = self.fixture
        for n, topic in enumerate(("治理原则", "安全存储"), 1):
            ident = copy.deepcopy(f.ident)
            ident.update(artifact_id=f"part{n}", variant=f"部分{n}")
            ident["presentation"]["topic"] = topic
            f.add_current(ident, ".ipynb")
            f.m["required"].append(["完整复习", f"部分{n}", ".ipynb"])
        f.m["objects"] = [dict(id="bundle", artifacts=["notes-v1"], source_objects=["part1", "part2"]),
                          dict(id="part1", artifacts=["part1"]), dict(id="part2", artifacts=["part2"])]
        f.entry(); f.save()
        self.assertEqual(f.run_gate()["status"], "passed")
        f.m["objects"][1]["source_objects"] = ["bundle"]
        f.save(); f.assert_fails("aggregate object cycle")

    def test_relationship_opt_out_needs_a_reason(self):
        f = self.fixture
        f.m["objects"] = [dict(id="lesson-six", artifacts=["notes-v1"], shared_presentation=False)]
        f.save()
        with self.assertRaisesRegex(ValueError, "relation_basis"):
            f.run_gate()

    def test_usability_requires_actual_representation_answers_not_only_passed_flag(self):
        f = self.fixture
        f.save()
        r = json.loads(f.review.read_text())
        r["usability"]["notes-v1"]["open_with"] = ""
        f.review.write_text(json.dumps(r))
        f.assert_fails("usability open_with missing")

    def test_legacy_collection_cannot_reuse_new_completion_claim(self):
        f = self.fixture
        f.m["schema"] = "ntu-course-delivery-v2"
        f.save()
        f.assert_fails("requires v3 migration")

    def test_collection_success_is_explicitly_not_whole_task_success(self):
        f = self.fixture
        f.save()
        result = f.run_gate()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["acceptance_level"], "collection_only")
        self.assertEqual(result["task_coverage"], "not_checked_use_check_course_task")

    def test_revision_can_change_without_changing_readable_filename(self):
        f=self.fixture;f.save();previous=f.work/"before.json";previous.write_bytes(f.manifest.read_bytes())
        old=f.m["artifacts"][0];(f.root/old["path"]).unlink();f.m["artifacts"].clear()
        revised=copy.deepcopy(f.ident);revised.update(artifact_id="notes-v2",revision="v2",date="20260103")
        newer=f.add_current(revised);self.assertEqual(old["path"],newer["path"])
        f.m.update(operation="update",previous_sha256=delivery.sha(previous));f.entry();f.save()
        self.assertEqual(f.run_gate(previous)["status"],"passed")


class TaskCoverageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="course-task-regression-")
        self.base = Path(self.tmp.name)
        self.root = self.base / "course"
        self.work = self.base / "work"
        self.work.mkdir()
        for name in ("03", "04"):
            (self.root/name).mkdir(parents=True)
        (self.root/"03/lesson.ipynb").write_text(json.dumps(dict(cells=[], metadata={}, nbformat=4, nbformat_minor=5)))
        (self.root/"04/notes.html").write_text("<h1>合成复习资料</h1><p>Only a synthetic test file.</p>")
        self.request = self.work/"request.json"
        self.request.write_text(json.dumps(dict(reference="Synthetic request: both folders, every file", locator="unit test specification",
            requested_roots=["03", "04"], required_dimensions=list(task.DIMENSIONS))))
        self.before = self.work/"before.json"
        self.before.write_text(json.dumps(task.snapshot(self.root, self.request)))
        self.m = dict(schema=task.SCHEMA, request="request.json", before="before.json", before_sha256=delivery.sha(self.before), records=[])
        for n, name in enumerate(("03/lesson.ipynb", "04/notes.html")):
            self.m["records"].append(dict(id=str(n), role="derived", action="keep_verified", reason="Synthetic existing content retained and checked",
                before_path=name, path=name, fingerprint=task.fingerprint(self.root/name)))
        self.manifest = self.work/"task.json"
        self.review = self.work/"review.json"

    def tearDown(self):
        self.tmp.cleanup()

    def save(self):
        self.manifest.write_text(json.dumps(self.m))
        r = task.review_template(self.manifest)
        r["reviewer"] = "Synthetic test stub, not a real content or browser review"
        for record in r["records"].values():
            for dim in task.DIMENSIONS:
                record[dim] = dict(status="passed", note=f"Synthetic {dim} scenario as specified in this test", evidence_locator="isolated fixture; not real acceptance")
        self.review.write_text(json.dumps(r))

    def run_gate(self):
        return task.check(self.manifest, self.root, self.review)

    def assert_fails(self, needle):
        r = self.run_gate()
        self.assertEqual(r["status"], "failed")
        self.assertIn(needle, "; ".join(r["errors"]))
        return r

    def test_complete_requested_scope_passes_and_reports_each_dimension(self):
        self.save(); r = self.run_gate()
        self.assertEqual(r["status"], "passed")
        self.assertEqual(r["coverage"]["current_files"], 2)
        self.assertEqual(set(r["dimensions"].values()), {"passed"})
        self.assertEqual(r["user_acceptance"], "not_established_by_this_tool")

    def test_omitting_prestudy_folder_fails_even_when_selected_records_are_green(self):
        self.m["records"] = self.m["records"][1:]
        self.save(); r = self.assert_fails("03/lesson.ipynb")
        self.assertEqual(r["coverage"]["status"], "failed")

    def test_real_green_collection_does_not_cover_unlisted_prestudy_directory(self):
        f=existing.DeliveryTests();f.setUp()
        try:
            f.save();self.assertEqual(f.run_gate()["status"],"passed")
            (f.root/"03").mkdir();(f.root/"03/lesson.ipynb").write_text('{"cells":[]}')
            req=f.work/"request.json";req.write_text(json.dumps(dict(reference="Synthetic whole-course request",locator="regression specification",requested_roots=["."],required_dimensions=["naming_organization"])))
            before=f.work/"task-before.json";before.write_text(json.dumps(task.snapshot(f.root,req)))
            records=[]
            for name,p in task.files(f.root,["."]).items():
                if name.startswith("03/"):continue
                records.append(dict(id=str(len(records)),role="entrypoint" if name=="index.html" else "derived",action="keep_verified",reason="Selected collection inspected",before_path=name,path=name,fingerprint=task.fingerprint(p)))
            manifest=f.work/"task.json";manifest.write_text(json.dumps(dict(schema=task.SCHEMA,request="request.json",before="task-before.json",before_sha256=delivery.sha(before),records=records,collections=[dict(manifest="delivery.json",review="review.json",root=".")])))
            review=task.review_template(manifest);review["reviewer"]="Synthetic regression stub"
            for item in review["records"].values():item["naming_organization"]=dict(status="passed",note="Only selected synthetic collection checked",evidence_locator="green fixture")
            path=f.work/"task-review.json";path.write_text(json.dumps(review));result=task.check(manifest,f.root,path)
            self.assertEqual(result["status"],"failed");self.assertIn("03/lesson.ipynb","; ".join(result["errors"]))
        finally:
            f.tearDown()

    def test_shrinking_the_request_after_snapshot_cannot_hide_prestudy(self):
        req = json.loads(self.request.read_text()); req["requested_roots"] = ["04"]
        self.request.write_text(json.dumps(req)); self.m["records"] = self.m["records"][1:]
        self.save(); self.assert_fails("cannot narrow scope")

    def test_new_file_unregistered_in_selected_collections_is_detected(self):
        (self.root/"03/old-copy.html").write_text("Synthetic leftover")
        self.save(); self.assert_fails("current files without disposition")

    def test_body_retained_does_not_excuse_unchecked_naming(self):
        self.save(); r = json.loads(self.review.read_text())
        r["records"]["0"]["naming_organization"]["status"] = "not_checked"
        self.review.write_text(json.dumps(r)); self.assert_fails("naming_organization unresolved")

    def test_naming_does_not_allow_blanket_not_applicable_for_generated_files(self):
        self.save(); r = json.loads(self.review.read_text())
        r["records"]["0"]["naming_organization"] = dict(status="not_applicable", note="Content unchanged", evidence_locator="")
        self.review.write_text(json.dumps(r)); self.assert_fails("naming_organization unresolved")

    def test_source_can_keep_original_filename_with_specific_evidence(self):
        self.m["records"][0].update(role="source", source_basis="Synthetic teacher filename, exact unchanged fixture bytes")
        self.save(); r = json.loads(self.review.read_text())
        for dim in ("content", "naming_organization", "display"):
            r["records"]["0"][dim] = dict(status="not_applicable", note="Original source preserved; generated naming does not apply", evidence_locator="")
        self.review.write_text(json.dumps(r)); self.assertEqual(self.run_gate()["status"], "passed")

    def test_missing_evidence_or_stale_current_file_fails(self):
        self.save(); r = json.loads(self.review.read_text());r["records"]["0"]["display"]["evidence_locator"] = ""
        self.review.write_text(json.dumps(r)); self.assert_fails("display evidence missing")
        self.save();(self.root/"04/notes.html").write_text("Unreviewed change")
        self.assert_fails("current fingerprint differs")

    def test_removed_path_must_be_gone(self):
        self.m["records"][0].update(action="remove");del self.m["records"][0]["path"]
        self.save(); self.assert_fails("removed file still exists")

    def test_replaced_path_is_accounted_and_old_name_must_disappear(self):
        old = self.root/"03/lesson.ipynb"; new = old.with_name("生成式AI_可编辑笔记.ipynb")
        old.rename(new);self.m["records"][0].update(action="replace", path="03/"+new.name, fingerprint=task.fingerprint(new))
        self.save();self.assertEqual(self.run_gate()["status"], "passed")
        old.write_bytes(new.read_bytes());self.save();self.assert_fails("replaced old path remains")

    def test_learning_page_cannot_hide_as_resource_or_auxiliary(self):
        for role in ("resource", "auxiliary"):
            self.m["records"][0].update(role=role, used_by=["04/notes.html"])
            self.save(); self.assert_fails("learning page cannot be classified")

    def test_large_media_metadata_is_reported_as_metadata_not_a_hash(self):
        p=self.root/"03/media.bin";p.write_bytes(b"synthetic media")
        fp=task.fingerprint(p, hash_limit=1)
        self.assertEqual(fp["method"], "size_mtime");self.assertNotIn("value", fp)
        self.assertTrue(task.matches(p, fp));p.write_bytes(b"different media")
        self.assertFalse(task.matches(p, fp))

    def test_large_file_report_names_the_weaker_fingerprint(self):
        p=self.root/"03/media.bin"
        with p.open("wb") as stream:stream.truncate(20_000_001)
        self.before.write_text(json.dumps(task.snapshot(self.root,self.request)));self.m["before_sha256"]=delivery.sha(self.before)
        self.m["records"].append(dict(id="media",role="resource",action="keep_verified",reason="Synthetic sparse media fixture",before_path="03/media.bin",path="03/media.bin",fingerprint=task.fingerprint(p),used_by=["03/lesson.ipynb"]))
        self.save();result=self.run_gate();self.assertEqual(result["status"],"passed")
        self.assertEqual(result["large_files"],{"03/media.bin":"size_mtime"})

    def test_internal_metadata_cannot_pollute_course_inventory(self):
        internal=self.root/"request.json";internal.write_bytes(self.request.read_bytes())
        with self.assertRaisesRegex(ValueError,"outside course root"):
            task.snapshot(self.root,internal)

    def test_snapshot_and_cli_are_read_only_for_course_content(self):
        self.save();before={str(p):delivery.sha(p) for p in self.root.rglob("*") if p.is_file()}
        script=Path(task.__file__)
        result=subprocess.run([sys.executable,str(script),str(self.manifest),"--root",str(self.root),"--review",str(self.review),"--report",str(self.work/"result.json")],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(before,{str(p):delivery.sha(p) for p in self.root.rglob("*") if p.is_file()})
        result=subprocess.run([sys.executable,str(script),"--snapshot","--request",str(self.request),"--root",str(self.root),"--report",str(self.root/"bad.json")],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertFalse((self.root/"bad.json").exists())

    def test_missing_review_and_template_never_pass(self):
        self.save();self.assertEqual(task.check(self.manifest,self.root)["status"],"failed")
        self.assertTrue(all(item["status"]=="not_checked" for record in task.review_template(self.manifest)["records"].values() for item in record.values()))


class ReaderGenerationTests(unittest.TestCase):
    def test_reader_builds_from_multiple_unchanged_notebooks_and_encoded_images(self):
        from build_course_reader import build
        with tempfile.TemporaryDirectory(prefix="reader-contract-") as directory:
            root=Path(directory);asset=root/"【勿删】课件原图";asset.mkdir()
            (asset/"page.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="30"><rect width="40" height="30" fill="white"/></svg>')
            ident=dict(collection_id="demo",subject_id="lesson",artifact_id="reader-v1",course="DEMO",subject_label="第6周",purpose="逐页中英对照",variant="总册",scope_revision="s1",scope_label="本周两份材料",date="20260102",revision="v1",review_state="审阅版",presentation=dict(topic="本周课件",sequence="01"))
            inputs=[]
            image_uri=quote("【勿删】课件原图/page.svg",safe="/")
            for n in range(2):
                p=root/f"part{n}.ipynb"
                cells=[dict(cell_type="markdown",source=[f"# 部分{n}"]),
                       dict(cell_type="markdown",source=["## 原始第1页\n![]("+image_uri+")"]),
                       dict(cell_type="markdown",source=["### 中文\n合成说明，无真实课程内容。"])]
                p.write_text(json.dumps(dict(metadata={},cells=cells),ensure_ascii=False));inputs.append(p)
            before={p:delivery.sha(p) for p in inputs};output=root/delivery.filename(ident,".html")
            build(None,output,inputs,ident)
            actual,heading=delivery.embedded(output)
            self.assertEqual(actual,ident);self.assertEqual(heading,delivery.title(ident))
            self.assertEqual(output.read_text().count('class="page-card"'),2)
            self.assertEqual(before,{p:delivery.sha(p) for p in inputs})
            with self.assertRaisesRegex(ValueError,"filename differs"):
                build(None,root/"opaque.html",inputs,ident)
            with self.assertRaisesRegex(ValueError,"identity/presentation"):
                build("Loose title",root/"preview.html",inputs)
            build(None,output,inputs,ident,diagnostic=True)
            self.assertIn("临时诊断预览",output.read_text())
            with self.assertRaisesRegex(ValueError,"one identity block"):
                delivery.embedded(output)


if __name__ == "__main__":
    unittest.main()
