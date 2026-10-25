#!/usr/bin/env python3
"""Compare the user-requested scope with disk, not with a union of selected collections.

Only explicit metadata/report outputs are written, outside the course root. This
checker cannot prove a reviewer's semantic claims or infer scope from a prompt.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from check_course_delivery import local, sha, text, check as check_collection

SCHEMA = "ntu-course-task-v1"
DIMENSIONS = ("content", "naming_organization", "file_integrity", "display")
ACTIONS = {"keep_verified", "refresh", "replace", "remove", "blocked"}
ROLES = {"derived", "source", "resource", "entrypoint", "auxiliary"}


def inside(root: Path, relative: str) -> Path:
    if relative == ".":
        if root.is_symlink():
            raise ValueError("symlink root is not an inventory")
        return root
    return local(root, relative)


def files(root: Path, requested: list[str]) -> dict[str, Path]:
    if not requested or len(requested) != len(set(requested)):
        raise ValueError("request needs distinct nonempty requested_roots")
    observed = {}
    for relative in requested:
        directory = inside(root, relative)
        if not directory.is_dir():
            raise ValueError(f"requested directory missing: {relative}")
        for p in directory.rglob("*"):
            if p.is_symlink():
                raise ValueError(f"symlink in requested inventory: {p.relative_to(root)}")
            if p.is_file():
                observed[p.relative_to(root).as_posix()] = p
    return observed


def fingerprint(path: Path, hash_limit: int = 20_000_000) -> dict:
    st = path.stat()
    if st.st_size <= hash_limit:
        return {"method": "sha256", "value": sha(path)}
    return {"method": "size_mtime", "size": st.st_size, "mtime_ns": st.st_mtime_ns}


def matches(path: Path, value: dict) -> bool:
    if value.get("method") == "sha256":
        return sha(path) == value.get("value")
    if value.get("method") == "size_mtime":
        st = path.stat()
        return (st.st_size, st.st_mtime_ns) == (value.get("size"), value.get("mtime_ns"))
    return False


def request_value(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    text(value.get("reference"), "request.reference")
    text(value.get("locator"), "request.locator")
    required = value.get("required_dimensions")
    if not isinstance(required, list) or not required or len(set(required)) != len(required) or not set(required) <= set(DIMENSIONS):
        raise ValueError("request.required_dimensions must name the actual requested quality dimensions")
    if not isinstance(value.get("requested_roots"), list):
        raise ValueError("request.requested_roots required")
    return value


def snapshot(root: Path, request_path: Path) -> dict:
    if request_path.resolve().is_relative_to(root.resolve()):
        raise ValueError("request metadata belongs outside course root")
    request = request_value(request_path)
    return {"schema": SCHEMA, "root": str(root.resolve()), "request_sha256": sha(request_path),
            "requested_roots": request["requested_roots"],
            "files": {name: fingerprint(p) for name, p in sorted(files(root, request["requested_roots"]).items())}}


def review_template(manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {"schema": SCHEMA, "manifest_sha256": sha(manifest_path), "reviewer": "",
            "records": {r["id"]: {dimension: {"status": "not_checked", "note": "", "evidence_locator": ""}
                                  for dimension in DIMENSIONS}
                        for r in manifest.get("records", [])}}


def check(manifest_path: Path, root: Path, review_path: Path | None = None) -> dict:
    if manifest_path.resolve().is_relative_to(root.resolve()) or (review_path and review_path.resolve().is_relative_to(root.resolve())):
        raise ValueError("task metadata/review belongs outside course root")
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    work = manifest_path.resolve().parent
    errors = []
    dimensions = {d: "not_requested" for d in DIMENSIONS}

    def require(condition, message):
        if not condition:
            errors.append(message)

    require(m.get("schema") == SCHEMA, "unknown task schema")
    req_path = local(work, m["request"])
    request = request_value(req_path)
    before_path = local(work, m["before"])
    if any(p.resolve().is_relative_to(root.resolve()) for p in (req_path, before_path)):
        raise ValueError("request/baseline metadata belongs outside course root")
    before = json.loads(before_path.read_text(encoding="utf-8"))
    require(before.get("schema") == SCHEMA and before.get("root") == str(root.resolve()), "baseline belongs to another root/schema")
    require(m.get("before_sha256") == sha(before_path), "task baseline hash changed")
    require(before.get("request_sha256") == sha(req_path), "request changed after snapshot; cannot narrow scope to selected collections")
    require(before.get("requested_roots") == request["requested_roots"], "requested roots changed")
    current = files(root, request["requested_roots"])
    prior = before.get("files", {})
    rows = m.get("records", [])
    before_seen, current_seen, ids = set(), set(), set()
    for row in rows:
        rid = text(row.get("id"), "record.id")
        require(rid not in ids, f"duplicate record id: {rid}")
        ids.add(rid)
        text(row.get("reason"), "record.reason")
        require(row.get("role") in ROLES, f"unknown file role: {rid}")
        action = row.get("action")
        require(action in ACTIONS, f"unknown disposition: {rid}")
        bp, cp = row.get("before_path"), row.get("path")
        if bp:
            inside(root, bp)
            require(bp in prior and bp not in before_seen, f"unknown/duplicate baseline file: {bp}")
            before_seen.add(bp)
        if cp:
            inside(root, cp)
            require(cp in current and cp not in current_seen, f"unknown/duplicate current file: {cp}")
            current_seen.add(cp)
            require(cp in current and matches(current[cp], row.get("fingerprint", {})), f"current fingerprint differs: {cp}")
        require(bool(bp or cp), f"record has no physical file: {rid}")
        if action == "remove":
            require(bool(bp) and not cp, f"removal needs only a baseline file: {rid}")
            require(bp not in current, f"removed file still exists: {bp}")
        else:
            require(bool(cp), f"current path required: {rid}")
        if action == "keep_verified":
            require(bp == cp and bp in prior and cp in current and matches(current[cp], prior[bp]), f"kept file changed or has no baseline: {rid}")
        if action == "replace" and bp and bp != cp:
            require(bp not in current, f"replaced old path remains: {bp}")
        if action == "blocked":
            require(False, f"unresolved file: {rid}")
        if row.get("role") == "source":
            text(row.get("source_basis"), "source.source_basis")
            require(action == "keep_verified" or bool(row.get("source_update_basis")), f"source change needs explicit basis: {rid}")
        if row.get("role") == "auxiliary":
            require(Path(cp or bp).suffix.lower() not in {".html", ".htm", ".md", ".ipynb"}, f"learning page cannot be classified as auxiliary: {rid}")
        if row.get("role") == "resource" and action != "remove":
            require(Path(cp or bp).suffix.lower() not in {".html", ".htm", ".md", ".ipynb"}, f"learning page cannot be classified as resource: {rid}")
            users = row.get("used_by", [])
            require(bool(users) and all(p in current for p in users), f"resource needs existing consumers: {rid}")
    require(before_seen == set(prior), f"baseline files without disposition: {sorted(set(prior)-before_seen)}")
    require(current_seen == set(current), f"current files without disposition: {sorted(set(current)-current_seen)}")
    coverage_errors = list(errors)
    # Collection receipts supplement the filesystem-wide coverage check; they do
    # not define or reduce its requested roots.
    for item in m.get("collections", []):
        args = {key: local(work, item[key]) for key in ("manifest", "review")}
        previous = local(work, item["previous"]) if item.get("previous") else None
        result = check_collection(args["manifest"], inside(root, item["root"]), args["review"], previous)
        require(result["status"] == "passed", f"collection failed: {item['manifest']}: {result['errors']}")
    requested = request["required_dimensions"]
    if review_path:
        review = json.loads(review_path.read_text(encoding="utf-8"))
        require(review.get("schema") == SCHEMA and review.get("manifest_sha256") == sha(manifest_path), "task review stale")
        text(review.get("reviewer"), "task reviewer")
        require(set(review.get("records", {})) == ids, "task review omits dispositions")
        for dimension in requested:
            start = len(errors)
            for row in rows:
                item = review.get("records", {}).get(row["id"], {}).get(dimension, {})
                status = item.get("status")
                # Original sources and resources need not acquire generated
                # filenames; non-applicability must be justified for this file.
                applicable = row["action"] != "remove" and row["role"] in {"derived", "entrypoint"}
                if dimension == "file_integrity":
                    applicable = row["action"] != "remove"
                allowed = {"passed"} if applicable else {"passed", "not_applicable"}
                require(status in allowed, f"{dimension} unresolved for {row['id']}: {status}")
                require(isinstance(item.get("note"), str) and bool(item["note"].strip()), f"{dimension} reason missing: {row['id']}")
                if status == "passed":
                    require(isinstance(item.get("evidence_locator"), str) and bool(item["evidence_locator"].strip()), f"{dimension} evidence missing: {row['id']}")
            dimensions[dimension] = "passed" if len(errors) == start else "failed_or_unchecked"
    else:
        errors.append("task review missing; per-file dispositions and quality checks are not automatic semantic acceptance")
        for dimension in requested:
            dimensions[dimension] = "not_checked"
    return {"schema": SCHEMA, "status": "failed" if errors else "passed", "scope": "requested_course_task",
            "request_sha256": sha(req_path), "manifest_sha256": sha(manifest_path),
            "coverage": {"status": "failed" if coverage_errors else "passed", "before_files": len(prior),
                         "current_files": len(current), "classified_before": len(before_seen), "classified_current": len(current_seen)},
            "dimensions": dimensions, "errors": errors,
            "large_files": {p: "size_mtime" for p, f in current.items() if f.stat().st_size > 20_000_000},
            "user_acceptance": "not_established_by_this_tool", "semantic_review": "recorded_not_independently_proven",
            "harness_runtime": "not_executed_by_this_tool"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, nargs="?")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--request", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--review-template", type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    for output in (args.report, args.review_template):
        if output and output.resolve().is_relative_to(args.root.resolve()):
            parser.error("metadata/report must be outside course root")
        if output and output.resolve() in {p.resolve() for p in (args.manifest, args.request, args.review) if p}:
            parser.error("report must not overwrite input evidence")
    try:
        if args.snapshot:
            if not args.request or args.manifest or args.review_template:
                parser.error("snapshot needs --request; no delivery manifest or review template")
            result = snapshot(args.root, args.request)
        else:
            if not args.manifest:
                parser.error("task manifest required")
            if args.review_template:
                args.review_template.write_text(json.dumps(review_template(args.manifest), ensure_ascii=False, indent=2) + "\n")
            result = check(args.manifest, args.root, args.review)
    except Exception as exc:
        result = {"schema": SCHEMA, "status": "failed", "scope": "requested_course_task", "errors": [str(exc)]}
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if (args.snapshot and "files" in result) or result.get("status") == "passed" else 1)


if __name__ == "__main__":
    main()
