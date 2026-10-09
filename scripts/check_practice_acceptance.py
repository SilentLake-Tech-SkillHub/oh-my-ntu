#!/usr/bin/env python3
"""Fail closeout when content review, the actual HTML and browser evidence differ."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_practice_bank import (RENDERER_VERSION, SCHEMA, artifact_bank, audit,
                                 content_identity, file_hash, materialize, read_constant)
from build_practice_page import validate

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
            "browser_validation": "passed" if not errors else "failed_or_stale",
            "harness_runtime": "not_executed_by_this_tool"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bank", type=Path)
    parser.add_argument("html", type=Path)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--verification", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = check(args.bank, args.html, args.review, args.verification)
    except (Exception, SystemExit) as exc:
        result = {"schema": SCHEMA, "status": "failed", "errors": [str(exc)],
                  "harness_runtime": "not_executed_by_this_tool"}
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
