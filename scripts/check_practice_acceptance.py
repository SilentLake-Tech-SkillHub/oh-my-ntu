#!/usr/bin/env python3
"""Fail closeout when content review, the actual HTML and browser evidence differ."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_practice_bank import (RENDERER_VERSION, SCHEMA, artifact_bank, audit,
                                 content_identity, file_hash, materialize, read_constant)
from build_practice_page import validate
from check_course_delivery import check as check_delivery, local

BROWSER_CHECKS = ("draft_reload", "submit_gate", "bilingual_feedback", "history_after_reset",
                  "pre_submit_images_loaded", "post_submit_images_loaded", "offline_requests_only",
                  "perfect_score_tested")


def check(bank_path: Path, html_path: Path, review_path: Path,
          verification_path: Path) -> dict:
    bank = materialize(json.loads(bank_path.read_text(encoding="utf-8")), bank_path.resolve().parent)
    validate(bank)
    review = json.loads(review_path.read_text(encoding="utf-8"))
    result = audit(bank, review)
    errors = list(result["errors"])
    source = html_path.read_text(encoding="utf-8")
    actual = artifact_bank(source)
    metadata = read_constant(source, "CONTENT_METADATA")[0]
    if content_identity(actual) != content_identity(bank):
        errors.append("The delivered HTML differs from the reviewed bank and task requirements")
    if (metadata.get("renderer_version") != RENDERER_VERSION
            or metadata.get("content_sha256") != result["content_sha256"]
            or metadata.get("content_reviewed") is not True):
        errors.append("HTML renderer/review metadata is missing, stale or unaccepted")
    evidence = json.loads(verification_path.read_text(encoding="utf-8"))
    if not isinstance(evidence, dict):
        raise ValueError("Browser receipt must be an object")
    if (evidence.get("schema") != SCHEMA or evidence.get("status") != "passed"
            or evidence.get("html_sha256") != file_hash(html_path)
            or evidence.get("content_sha256") != result["content_sha256"]
            or evidence.get("renderer_version") != RENDERER_VERSION):
        errors.append("Browser verification is missing or refers to older/different HTML")
    if evidence.get("questions") != len(bank["questions"]):
        errors.append("Browser question count differs from the bank")
    if evidence.get("max_points") != sum(q.get("points", 1) for q in bank["questions"]):
        errors.append("Browser full-score verification does not cover the bank's point total")
    if evidence.get("prompt_images") != result["prompt_images"]:
        errors.append("Browser figure count differs from the reviewed content")
    for key in BROWSER_CHECKS:
        if evidence.get(key) is not True:
            errors.append(f"Browser acceptance not confirmed: {key}")
    if evidence.get("mobile_overflow") is not False or evidence.get("browser_errors") != []:
        errors.append("Browser overflow/error evidence is failed or incomplete")
    return {**result, "status": "passed" if not errors else "failed", "errors": errors,
            "html_sha256": file_hash(html_path), "renderer_version": RENDERER_VERSION,
            "scope": "content_review_and_browser_acceptance",
            "delivery_acceptance": "not_checked_by_page_check",
            "browser_validation": "passed" if not errors else "failed_or_stale",
            "harness_runtime": "not_executed_by_this_tool"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bank", type=Path)
    parser.add_argument("html", type=Path)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--verification", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--page-only", action="store_true", help="Page diagnostics only; cannot close a collection delivery")
    parser.add_argument("--manifest", type=Path, help="Collection manifest; required for delivery closeout")
    parser.add_argument("--root", type=Path, help="Course root for read-only collection checks")
    parser.add_argument("--delivery-review", type=Path, help="Hash-bound review of current materials and entrypoints")
    parser.add_argument("--previous", type=Path, help="Previous collection manifest for updates")
    args = parser.parse_args()
    if args.root and args.report.resolve().is_relative_to(args.root.resolve()):
        parser.error("Acceptance report must be outside the course root")
    if args.report.resolve() in {p.resolve() for p in (args.bank, args.html, args.review, args.verification,
                                                       args.manifest, args.delivery_review, args.previous) if p}:
        parser.error("Acceptance report must not overwrite input evidence or course files")
    try:
        result = check(args.bank, args.html, args.review, args.verification)
        if args.page_only:
            if any((args.manifest, args.root, args.delivery_review, args.previous)):
                raise ValueError("--page-only cannot be combined with collection closeout arguments")
        else:
            if not all((args.manifest, args.root, args.delivery_review)):
                raise ValueError("Delivery closeout requires --manifest --root --delivery-review; use --page-only only for diagnostics")
            collection = check_delivery(args.manifest, args.root, args.delivery_review, args.previous)
            manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
            if not any(a["status"] == "current" and local(args.root, a["path"]).resolve() == args.html.resolve()
                       for a in manifest["artifacts"]):
                raise ValueError("Checked practice page is not a current artifact in this collection")
            result["collection"] = collection
            result["scope"] = "practice_content_browser_and_collection_delivery"
            result["delivery_acceptance"] = collection["status"]
            if collection["status"] != "passed":
                result["status"] = "failed"
                result["errors"].extend(collection["errors"])
    except (Exception, SystemExit) as exc:
        result = {"schema": SCHEMA, "status": "failed", "errors": [str(exc)],
                  "harness_runtime": "not_executed_by_this_tool"}
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
