#!/usr/bin/env python3
"""Check task constraints and bind explicit semantic review to exact content.

Automated checks identify objective omissions; they do not judge subject-matter
correctness or certify that a reviewer's explanations are true.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree

SCHEMA = "ntu-practice-acceptance-v1"
RENDERER_VERSION = "2026.10.10.1"
KINDS = {"concept", "analysis", "calculation", "code"}
CLASSROOM = re.compile(
    r"\b(?:lecture['’]s|according to (?:the )?(?:lecture|notebook)|"
    r"(?:in|from|during) the lecture|as (?:discussed|shown|taught) in "
    r"(?:the )?(?:lecture|notebook)|(?:lecture|slide|notebook)\s*\d+)\b", re.I)
CODE = re.compile(r"```|(?:^|\n|`)\s*import\s+[A-Za-z_]\w*|\b(?:from\s+\w+\s+import|"
                  r"(?:pd|np|df)\.[A-Za-z_]\w*|print\s*\(|"
                  r"(?:fit_transform|train_test_split|CountVectorizer)\s*\(|"
                  r"(?:code|snippet)\s+(?:below|above|outputs?|returns?|prints?)|"
                  r"(?:complete|debug|execute|run)\s+(?:the\s+)?(?:code|program|snippet))", re.I)
VISUAL = re.compile(r"\b(?:figure|chart|plot|diagram|image|table)\b.{0,40}"
                    r"\b(?:above|below|shown|pictured)\b|"
                    r"\b(?:pictured|displayed)\b.{0,30}"
                    r"\b(?:figure|chart|plot|diagram|image|table)\b", re.I)


REQUIRED = ("prompt", "options", "answer", "en", "zh", "source", "topic")
REQUIRED_FILL = ("prompt", "accept", "en", "zh", "source", "topic")

def validate(bank: dict) -> list[dict]:
    if not isinstance(bank, dict):
        raise SystemExit("bank must be an object")
    for key in ("course", "paper_id", "version", "title", "questions"):
        if not bank.get(key):
            raise SystemExit(f"bank is missing {key!r}")
    for key in ("course", "paper_id", "version", "title"):
        if not isinstance(bank[key], str) or not bank[key].strip():
            raise SystemExit(f"{key} must be nonempty text")
    questions = bank["questions"]
    if not isinstance(questions, list) or not questions:
        raise SystemExit("questions must be a nonempty list")
    for n, q in enumerate(questions, 1):
        if not isinstance(q, dict):
            raise SystemExit(f"question {n} must be an object")
        points = q.get("points", 1)
        if isinstance(points, bool) or not isinstance(points, (int, float)) or not (0 < points < float("inf")):
            raise SystemExit(f"question {n} points must be a finite positive number")
        if q.get("type") == "fill":
            missing = [k for k in REQUIRED_FILL if k not in q]
            if (missing or not isinstance(q.get("accept"), list) or not q["accept"]
                    or any(not isinstance(s, str) or not s.strip() for s in q["accept"])):
                raise SystemExit(f"fill question {n} is missing {missing or ['accept']}")
            continue
        missing = [k for k in REQUIRED if k not in q]
        if missing:
            raise SystemExit(f"question {n} is missing {missing}")
        if (not isinstance(q["options"], list) or len(q["options"]) < 2
                or any(not isinstance(s, str) or not s.strip() for s in q["options"])
                or not isinstance(q["answer"], list) or not q["answer"]):
            raise SystemExit(f"question {n} needs at least two options and one answer")
        if any(isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < len(q["options"])
               for i in q["answer"]) or len(set(q["answer"])) != len(q["answer"]):
            raise SystemExit(f"question {n} has an invalid answer index")
    return questions


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def materialize(bank: dict, base: Path) -> dict:
    if not isinstance(bank, dict):
        raise ValueError("bank must be an object")
    result = copy.deepcopy(bank)
    questions = result.get("questions", [])
    if not isinstance(questions, list):
        raise ValueError("questions must be a list")
    for n, q in enumerate(questions, 1):
        if not isinstance(q, dict):
            raise ValueError(f"Q{n}: question must be an object")
        for key in ("prompt_image", "image"):
            value = q.get(key)
            if not value:
                continue
            if not isinstance(value, str):
                raise ValueError(f"Q{n}: {key} must be an image path or data URI")
            if not value.startswith("data:"):
                if re.match(r"[a-zA-Z][\w+.-]*:", value):
                    raise ValueError(f"Q{n}: remote images are not offline resources")
                path = (base / value).resolve(strict=True)
                mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                        ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml"}.get(path.suffix.lower())
                if mime is None:
                    raise ValueError(f"Q{n}: unsupported image extension")
                value = f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")
            match = re.fullmatch(r"data:(image/(?:png|jpeg|gif|webp|svg\+xml));base64,([A-Za-z0-9+/=\s]+)", value)
            if not match:
                raise ValueError(f"Q{n}: invalid embedded image URI")
            raw = base64.b64decode(match[2], validate=True)
            mime = match[1]
            valid = {"image/png": raw.startswith(b"\x89PNG\r\n\x1a\n"),
                     "image/jpeg": raw.startswith(b"\xff\xd8\xff"),
                     "image/gif": raw.startswith((b"GIF87a", b"GIF89a")),
                     "image/webp": raw.startswith(b"RIFF") and raw[8:12] == b"WEBP"}
            if mime == "image/svg+xml":
                valid[mime] = ElementTree.fromstring(raw).tag.split("}")[-1] == "svg"
            if not raw or not valid.get(mime):
                raise ValueError(f"Q{n}: image bytes do not match their format")
            q[key] = f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")
    return result


def content_identity(bank: dict) -> str:
    return digest({k: bank.get(k) for k in (
        "course", "paper_id", "version", "title", "banner", "requirements", "questions")})


def question_id(q: dict, number: int) -> str:
    return str(q.get("id", f"Q{number}"))


def review_template(bank: dict) -> dict:
    return {"schema": SCHEMA, "content_sha256": content_identity(bank), "reviewer": "",
            "questions": [{"id": question_id(q, n), "question_sha256": digest(q),
                           "self_contained": False, "source_verified": False,
                           "answer_verified": False, "contains_code": None,
                           "figure_not_answer_leaking": False if q.get("prompt_image") else None,
                           "conditions_note": "", "source_note": "", "answer_note": "",
                           "figure_note": ""}
                          for n, q in enumerate(bank["questions"], 1)]}


def audit(bank: dict, review: dict | None = None) -> dict:
    errors = []
    try:
        validate(bank)
    except SystemExit as exc:
        errors.append(str(exc))
    requirements = bank.get("requirements")
    if not isinstance(requirements, dict):
        requirements = {}
        errors.append("Declare requirements.allow_code and requirements.minimum_visual_questions for this task")
    allow_code = requirements.get("allow_code")
    minimum = requirements.get("minimum_visual_questions")
    if not isinstance(allow_code, bool):
        errors.append("requirements.allow_code must be a boolean")
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 0:
        errors.append("requirements.minimum_visual_questions must be a nonnegative integer")
        minimum = 0
    questions = bank.get("questions", [])
    if not isinstance(questions, list) or not questions:
        raise ValueError("questions must be a nonempty list")
    ids, visual_count = set(), 0
    for n, q in enumerate(questions, 1):
        if not isinstance(q, dict):
            raise ValueError(f"Q{n}: question must be an object")
        ident = question_id(q, n)
        if ident in ids:
            errors.append(f"{ident}: duplicate question ID")
        ids.add(ident)
        if q.get("kind") not in KINDS:
            errors.append(f"{ident}: declare kind as concept, analysis, calculation or code")
        if not isinstance(q.get("requires_figure"), bool):
            errors.append(f"{ident}: declare requires_figure")
        for field in ("prompt", "en", "zh", "source", "topic"):
            if not isinstance(q.get(field), str) or not q[field].strip():
                errors.append(f"{ident}: {field} must be nonempty text")
        text = str(q.get("prompt", "")) + "\n" + "\n".join(map(str, q.get("options", [])))
        if CLASSROOM.search(text):
            errors.append(f"{ident}: classroom-dependent wording needs explicit question conditions")
        if allow_code is False and (q.get("kind") == "code" or q.get("code") or CODE.search(text)):
            errors.append(f"{ident}: code questions are forbidden for this task")
        if q.get("requires_figure") or VISUAL.search(str(q.get("prompt", ""))):
            if not q.get("prompt_image"):
                errors.append(f"{ident}: necessary pre-submission figure is missing")
        if q.get("prompt_image"):
            visual_count += int(q.get("requires_figure") is True)
            if not isinstance(q.get("prompt_image_caption"), str) or not q["prompt_image_caption"].strip():
                errors.append(f"{ident}: figure needs a descriptive caption")
    if visual_count < minimum:
        errors.append(f"Task requires at least {minimum} visual questions, found {visual_count}")
    automatic_errors = list(errors)
    if not review:
        errors.append("Semantic review is missing; automatic checks are not content acceptance")
    else:
        if not isinstance(review, dict):
            raise ValueError("review must be an object")
        if review.get("schema") != SCHEMA or review.get("content_sha256") != content_identity(bank):
            errors.append("Semantic review is stale or belongs to different task requirements/content")
        if not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
            errors.append("Semantic review needs a named reviewer")
        entries = review.get("questions", [])
        if not isinstance(entries, list):
            entries = []
        records = {str(r.get("id")): r for r in entries if isinstance(r, dict)}
        if len(records) != len(entries) or set(records) != ids:
            errors.append("Semantic review must cover each question exactly once")
        for n, q in enumerate(questions, 1):
            ident = question_id(q, n)
            r = records.get(ident, {})
            if r.get("question_sha256") != digest(q):
                errors.append(f"{ident}: reviewed question fingerprint does not match")
            for flag in ("self_contained", "source_verified", "answer_verified"):
                if r.get(flag) is not True:
                    errors.append(f"{ident}: semantic reviewer must confirm {flag}")
            if not isinstance(r.get("contains_code"), bool):
                errors.append(f"{ident}: reviewer must classify text AND picture code content")
            elif allow_code is False and r["contains_code"]:
                errors.append(f"{ident}: reviewed picture or question contains prohibited code")
            for note in ("conditions_note", "source_note", "answer_note"):
                if not isinstance(r.get(note), str) or not r[note].strip():
                    errors.append(f"{ident}: substantive {note} is missing")
            if q.get("prompt_image"):
                if (r.get("figure_not_answer_leaking") is not True
                        or not isinstance(r.get("figure_note"), str) or not r["figure_note"].strip()):
                    errors.append(f"{ident}: review the figure's necessity, legibility and answer leakage")
    return {"schema": SCHEMA, "status": "passed" if not errors else "failed", "errors": errors,
            "automatic_errors": automatic_errors,
            "content_sha256": content_identity(bank), "requirements": requirements,
            "question_count": len(questions), "visual_questions": visual_count,
            "prompt_images": sum(bool(q.get("prompt_image")) for q in questions),
            "semantic_review": "recorded" if review and not errors else "pending_or_invalid",
            "scope": "content_constraints_and_recorded_semantic_review", "browser_validation": "pending"}


def read_constant(source: str, name: str):
    match = re.search(r"^\s*const\s+" + re.escape(name) + r"\s*=\s*", source, re.M)
    if not match:
        raise ValueError(f"Missing JSON literal constant {name}")
    try:
        value, length = json.JSONDecoder().raw_decode(source[match.end():])
    except json.JSONDecodeError as exc:
        raise ValueError(f"Unsupported non-JSON {name}; do not guess legacy content") from exc
    return value, match.end(), match.end() + length


def artifact_bank(source: str) -> dict:
    return {"questions": read_constant(source, "QUESTIONS")[0],
            **{k: read_constant(source, const)[0] for k, const in
               (("course", "COURSE"), ("paper_id", "PAPER"), ("version", "VERSION"))},
            **read_constant(source, "CONTENT_METADATA")[0]["bank_fields"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bank", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--review-template", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        bank = materialize(json.loads(args.bank.read_text(encoding="utf-8")), args.bank.resolve().parent)
        if args.review_template:
            args.review_template.write_text(json.dumps(review_template(bank), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        review = json.loads(args.review.read_text(encoding="utf-8")) if args.review else None
        result = audit(bank, review)
    except (Exception, SystemExit) as exc:
        result = {"schema": SCHEMA, "status": "failed", "errors": [str(exc)]}
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
