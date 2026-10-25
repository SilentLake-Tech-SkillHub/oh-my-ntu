#!/usr/bin/env python3
"""Read-only collection gate: identity, unique current revisions, inventory and links.

The manifest and review belong outside the delivered course directory. Automated
checks cannot establish the truth of course facts or a human reviewer's claims.
"""
from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import unquote, urlsplit

SCHEMA = "ntu-course-delivery-v3"
REVIEW_CHECKS = ("source_identity", "scope_consistency", "entry_clarity", "usability", "obsolete_removed")
STATUSES = {"current"}
CARRIERS = {".html": "阅读版", ".ipynb": "可编辑笔记", ".md": "文字说明"}


def obsolete_directory(path: str) -> bool:
    """Recognize version archives, not official past-question collections."""
    return any(re.fullmatch(r"(?:history|archive|archives|backup|backups|历史版本|旧版本|旧版|历史区|归档|备份)",
                            re.sub(r"^\d+[_-]", "", part), re.I)
               for part in PurePosixPath(path).parts)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: nonempty text required")
    return value


def token(value: object, name: str) -> str:
    value = text(value, name)
    if re.search(r'[\\/:*?"<>|\x00-\x1f_]', value) or value in {".", ".."}:
        raise ValueError(f"{name}: unsafe filename token")
    return value


def local(root: Path, relative: str) -> Path:
    text(relative, "relative path")
    p = PurePosixPath(relative)
    if p.is_absolute() or ".." in p.parts or "\\" in relative or relative == ".":
        raise ValueError(f"unsafe relative path: {relative}")
    candidate = root / relative
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"path escapes root: {relative}")
    for part in (candidate, *candidate.parents):
        if part == root:
            break
        if part.is_symlink():
            raise ValueError(f"symlink is not an entity: {relative}")
    return candidate


def under(path: str, directory: str) -> bool:
    return PurePosixPath(path).is_relative_to(PurePosixPath(directory))


def identity(value: dict) -> dict:
    """Validate the data shared by filename, page heading and collection manifest."""
    if not isinstance(value, dict):
        raise ValueError("delivery_identity must be an object")
    for key in ("collection_id", "subject_id", "scope_revision", "artifact_id"):
        text(value.get(key), key)
    for key in ("course", "subject_label", "purpose", "variant", "scope_label", "revision", "review_state"):
        token(value.get(key), key)
    from datetime import datetime
    date = text(value.get("date"), "date")
    if not re.fullmatch(r"\d{8}", date):
        raise ValueError("date must be YYYYMMDD")
    datetime.strptime(date, "%Y%m%d")
    if not re.fullmatch(r"v[1-9]\d*", value["revision"]):
        raise ValueError("revision must be v1, v2, ...")
    if value["review_state"] not in {"审阅版", "已验收版"}:
        raise ValueError("review_state must distinguish review from user acceptance")
    return value


def filename(value: dict, suffix: str) -> str:
    identity(value)
    display = presentation(value)
    carrier = display.get("carriers", {}).get(suffix, CARRIERS.get(suffix))
    token(carrier, "presentation carrier")
    parts = [display.get("sequence"), display.get("context"), display["topic"], value["purpose"]]
    if value["variant"] not in {"总册", "总览"}:
        parts.append(value["variant"])
    return "_".join(p for p in [*parts, carrier] if p) + suffix


def title(value: dict) -> str:
    identity(value)
    display = presentation(value)
    parts = [display.get("context"), display["topic"], value["purpose"]]
    if value["variant"] not in {"总册", "总览"}:
        parts.append(value["variant"])
    return " · ".join(p for p in parts if p)


def presentation(value: dict) -> dict:
    """Readable labels are separate from source, scope, date and revision metadata."""
    display = value.get("presentation")
    if not isinstance(display, dict):
        raise ValueError("readable naming requires identity.presentation; legacy names need explicit migration")
    topic = token(display.get("topic"), "presentation.topic")
    if re.fullmatch(r"(?:ch(?:apter)?|wk|week|nb)[ -]?\d+", topic, re.I) or re.match(r"^\d{8}(?:\D|$)", topic):
        raise ValueError("presentation.topic must explain the subject, not only an opaque code/date")
    for field in ("context", "sequence"):
        if display.get(field):
            token(display[field], f"presentation.{field}")
    if display.get("sequence") and not re.fullmatch(r"\d{2,3}", display["sequence"]):
        raise ValueError("sequence is a reading-order number, not a revision")
    carriers = display.get("carriers", {})
    if not isinstance(carriers, dict):
        raise ValueError("presentation.carriers must map extensions to opening-purpose labels")
    for suffix, label in carriers.items():
        if not re.fullmatch(r"\.[a-z0-9]+", suffix):
            raise ValueError("unsafe carrier extension")
        token(label, "presentation.carrier")
    return display


def html_identity(value: dict) -> str:
    identity(value)
    return ('<script type="application/json" id="course-delivery-identity">'
            + json.dumps(value, ensure_ascii=False).replace("<", "\\u003c") + '</script>')


class Page(HTMLParser):
    def __init__(self, source: str):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.titles, self.headings, self.identities, self.links, self.blocks = [], [], [], [], []
        self.capture = None
        self.buffer = []
        self.base = False
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "base":
            self.base = True
        state = self.stack[-1][1:] if self.stack else (None, None)
        if "data-delivery-collection" in a:
            state = (a["data-delivery-collection"], a.get("data-delivery-status"))
            self.blocks.append(state)
        if tag == "a" and a.get("href"):
            self.links.append((a["href"], *state))
        if tag in {"title", "h1"} or (tag == "script" and a.get("id") == "course-delivery-identity"):
            self.capture, self.buffer = tag, []
        if tag not in {"meta", "link", "img", "input", "br", "hr", "source", "wbr", "area", "embed", "param", "track", "col", "base"}:
            self.stack.append((tag, *state))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self.stack and self.stack[-1][0] == tag:
            self.handle_endtag(tag)

    def handle_data(self, data):
        if self.capture:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag == self.capture:
            content = "".join(self.buffer).strip()
            {"title": self.titles, "h1": self.headings, "script": self.identities}[tag].append(content)
            self.capture, self.buffer = None, []
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


def embedded(path: Path) -> tuple[dict, str]:
    suffix = path.suffix.lower()
    source = path.read_text(encoding="utf-8")
    if suffix == ".html":
        page = Page(source)
        if page.base or len(page.identities) != 1 or len(page.titles) != 1 or len(page.headings) != 1:
            raise ValueError("HTML needs one identity block, one title, one h1 and no base tag")
        if page.titles[0] != page.headings[0]:
            raise ValueError("HTML title and h1 differ")
        return json.loads(page.identities[0]), page.titles[0]
    if suffix == ".ipynb":
        notebook = json.loads(source)
        headings = [line[2:].strip() for c in notebook.get("cells", []) if c.get("cell_type") == "markdown"
                    for line in ("".join(c.get("source", []))).splitlines() if line.startswith("# ")]
        if not headings:
            raise ValueError("Notebook needs a visible first-level title")
        return notebook.get("metadata", {}).get("course_delivery", {}), headings[0]
    if suffix == ".md":
        match = re.search(r'<!-- course-delivery-identity\s*(\{.*?\})\s*-->', source, re.S)
        heading = re.search(r'^# (.+)$', source, re.M)
        if not match or not heading:
            raise ValueError("Markdown needs identity JSON comment and visible title")
        return json.loads(match[1]), heading[1].strip()
    raise ValueError(f"unsupported derived format {suffix}; supply an adapter before claiming acceptance")


def review_template(manifest_path: Path, root: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    paths = {a["path"] for a in manifest["artifacts"] if a["status"] == "current"}
    paths.update(manifest["entrypoints"])
    return {"schema": SCHEMA, "manifest_sha256": sha(manifest_path), "reviewer": "",
            "files": {p: sha(local(root, p)) for p in sorted(paths)},
            "checks": {k: {"passed": False, "note": ""} for k in REVIEW_CHECKS},
            "usability": {a["id"]: {"topic": "", "purpose": "", "open_with": "",
                                      "first_action": "", "evidence_locator": ""}
                          for a in manifest["artifacts"] if a["status"] == "current"}}


def check(manifest_path: Path, root: Path, review_path: Path | None = None,
          previous_path: Path | None = None) -> dict:
    errors = []
    observed = {}

    def require(condition, message):
        if not condition:
            errors.append(message)

    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    if m.get("schema") != SCHEMA:
        return {"schema": SCHEMA, "status": "failed", "scope": "course_collection_delivery",
                "errors": ["collection schema requires v3 migration; legacy receipts do not establish readable naming"],
                "automatic_errors": ["collection schema requires v3 migration"],
                "task_coverage": "not_checked", "user_acceptance": "not_established_by_this_tool"}
    for key in ("collection_id", "course", "period"):
        text(m.get(key), key)
    subject = m["subject"]
    text(subject.get("id"), "subject.id")
    token(subject.get("label"), "subject.label")
    provenance = subject["provenance"]
    require(provenance.get("kind") in {"official", "classroom", "user_confirmed"}, "subject identity needs named evidence")
    text(provenance.get("reference"), "subject provenance.reference")
    text(provenance.get("locator"), "subject provenance.locator")
    scope = m["scope"]
    text(scope.get("revision"), "scope.revision")
    token(scope.get("label"), "scope.label")
    text(scope.get("basis"), "scope.basis")
    for field in ("inventory_roots", "active_dirs", "required", "artifacts", "entrypoints"):
        require(isinstance(m.get(field), list) and bool(m[field]), f"{field} must be nonempty")
    inventory, active = m["inventory_roots"], m["active_dirs"]
    require(not m.get("historical_dirs"), "latest-only delivery forbids historical directories")
    for directory in inventory + active:
        require(local(root, directory).is_dir(), f"directory missing: {directory}")
    for a in active:
        require(not obsolete_directory(a), f"latest artifact cannot live in a version archive: {a}")
        require(any(under(a, r) for r in inventory), f"active directory outside inventory: {a}")
        for component in PurePosixPath(a).parts:
            if re.fullmatch(r"(?:Quiz\s*#?\s*\d+|Final|Midterm)", component, re.I):
                normalized = lambda value: re.sub(r"[\s#]+", "", value).casefold()
                require(normalized(component) == normalized(subject["label"]), f"exam directory name differs from subject: {a}")
    artifacts, by_id, by_path, currents = m["artifacts"], {}, {}, {}
    for a in artifacts:
        aid, path = text(a.get("id"), "artifact.id"), text(a.get("path"), "artifact.path")
        require(aid not in by_id and path not in by_path, f"duplicate artifact id/path: {aid}")
        by_id[aid], by_path[path] = a, a
        require(a.get("kind") in {"document", "practice"}, f"unknown artifact kind: {aid}")
        require(a.get("status") in STATUSES, f"latest-only delivery permits current artifacts only: {aid}")
        p = local(root, path)
        require(p.is_file(), f"missing artifact: {path}")
        require(any(under(path, r) for r in inventory), f"artifact outside declared inventory: {path}")
        if p.is_file():
            observed[path] = sha(p)
            require(a.get("sha256") == observed[path], f"artifact hash differs: {path}")
            if a["status"] == "current" and p.suffix.lower() == ".html":
                page_source = p.read_text(encoding="utf-8")
                if re.search(r"\bconst\s+QUESTIONS\s*=", page_source) and "CONTENT_METADATA" in page_source:
                    require(a.get("kind") == "practice", f"practice renderer cannot be declared as ordinary document: {path}")
        if a["status"] == "current":
            require(not obsolete_directory(path) and any(under(path, d) for d in active), f"current artifact outside active area: {path}")
            ident = identity(a["identity"])
            if ident["review_state"] == "已验收版":
                acceptance = a.get("user_acceptance", {})
                text(acceptance.get("reference"), "user_acceptance.reference")
                text(acceptance.get("locator"), "user_acceptance.locator")
            key = (ident["purpose"], ident["variant"], p.suffix.lower())
            currents.setdefault(key, []).append(aid)
            for field, expected in (("collection_id", m["collection_id"]), ("subject_id", subject["id"]),
                                    ("course", m["course"]), ("subject_label", subject["label"]),
                                    ("scope_revision", scope["revision"]), ("scope_label", scope["label"]), ("artifact_id", aid)):
                require(ident[field] == expected, f"{aid}: {field} differs from collection")
            require(p.name == filename(ident, p.suffix), f"filename differs from structured identity: {path}")
            if p.is_file():
                try:
                    actual, heading = embedded(p)
                    require(actual == ident, f"embedded identity differs: {path}")
                    require(heading == title(ident), f"visible title differs from identity: {path}")
                except (ValueError, KeyError, TypeError) as exc:
                    errors.append(f"{path}: {exc}")
            if a.get("kind") == "practice":
                # Re-run each paper's real gate, rather than accepting an unrelated green report.
                from check_practice_acceptance import check as check_practice
                evidence = a.get("practice_check", {})
                try:
                    inputs = [local(manifest_path.resolve().parent, evidence[k]) for k in ("bank", "review", "verification")]
                    require(all(not v.resolve().is_relative_to(root.resolve()) for v in inputs), "practice evidence belongs outside course content")
                    page_result = check_practice(inputs[0], p, inputs[1], inputs[2])
                    require(page_result["status"] == "passed", f"practice content/browser acceptance failed: {aid}: {page_result['errors']}")
                except (KeyError, ValueError, OSError, SystemExit) as exc:
                    errors.append(f"practice evidence missing/invalid for {aid}: {exc}")
    required = [tuple(k) for k in m["required"]]
    require(len(set(required)) == len(required), "duplicate required family")
    for key in set(required) | set(currents):
        require(len(currents.get(key, [])) == 1, f"family must have exactly one current revision: {key}")
        require(key in required, f"current family absent from required list: {key}")
    for a in artifacts:
        for dependency in a.get("depends_on", []):
            target = by_id.get(dependency)
            require(target is not None, f"unknown dependency: {dependency}")
            if a["status"] == "current" and target:
                require(target["status"] == "current", f"current artifact depends on retired content: {a['id']}")
    # A lesson may have several carriers or aggregate other lesson objects. Never
    # infer pairing from file order, modification time or a similar basename.
    memberships = {}
    objects = m.get("objects", [])
    object_ids = [obj.get("id") for obj in objects]
    require(len(object_ids) == len(set(object_ids)), "duplicate stable object id")
    for obj in objects:
        oid = text(obj.get("id"), "object.id")
        members = obj.get("artifacts", [])
        require(bool(members) and len(members) == len(set(members)), f"object needs unique representations: {oid}")
        for aid in members:
            require(aid in by_id, f"unknown object representation: {aid}")
            require(aid not in memberships, f"representation belongs to multiple objects: {aid}")
            memberships[aid] = oid
        for path in obj.get("resources", []):
            require(any(r["path"] == path for r in m.get("resources", [])), f"object resource not registered: {path}")
        if obj.get("shared_presentation", True):
            labels = {(by_id[aid]["identity"]["presentation"]["topic"],
                       by_id[aid]["identity"]["purpose"], by_id[aid]["identity"]["variant"])
                      for aid in members if aid in by_id}
            require(len(labels) == 1, f"paired carriers need a shared topic/purpose/variant: {oid}")
        else:
            text(obj.get("relation_basis"), "object.relation_basis")
        for source in obj.get("source_objects", []):
            require(source != oid and any(v.get("id") == source for v in objects), f"unknown/self aggregate source: {source}")
    if objects:
        require(set(memberships) == set(by_id), "object map omits a current representation")
        graph = {o["id"]: o.get("source_objects", []) for o in objects}
        def acyclic(node, trail):
            return node not in trail and all(acyclic(v, trail | {node}) for v in graph.get(node, []))
        require(all(acyclic(node, set()) for node in graph), "aggregate object cycle")
    entries = {p: local(root, p) for p in m["entrypoints"]}
    accounted = set(by_path) | set(entries)
    for item in m.get("resources", []):
        p = local(root, item["path"])
        require(p.is_file() and sha(p) == item["sha256"], f"missing/changed resource: {item['path']}")
        require(item["path"] not in accounted, f"resource masks an artifact: {item['path']}")
        require(p.suffix.lower() not in {".html", ".htm", ".md", ".ipynb"}, "learning pages must be registered as artifacts")
        text(item.get("reason"), "resource.reason")
        accounted.add(item["path"])
    exclusions = m.get("exclusions", [])
    for item in exclusions:
        p = local(root, item["path"])
        text(item.get("reason"), "exclusion.reason")
        require(p.exists(), f"exclusion missing: {item['path']}")
        require(not any(under(ap, item["path"]) for ap in by_path), f"exclusion masks registered artifacts: {item['path']}")
        require(item["path"] not in inventory, "cannot exclude an entire inventory root")
        require(not obsolete_directory(item["path"]), "cannot exclude a version archive to bypass latest-only checks")
    for directory in inventory:
        require(not obsolete_directory(directory), f"version archive remains in delivery: {directory}")
        for p in local(root, directory).rglob("*"):
            rel = p.relative_to(root).as_posix()
            require(not obsolete_directory(rel), f"version archive remains in delivery: {rel}")
            if p.is_file() or p.is_symlink():
                local(root, rel)
                if any(under(rel, item["path"]) for item in exclusions):
                    continue
                require(rel in accounted, f"unregistered file in delivery inventory: {rel}")
    for path, p in entries.items():
        require(p.is_file(), f"missing entrypoint: {path}")
    # Inspect navigation and current HTML cross-links, including links outside marked sections.
    pages = dict(entries)
    pages.update({p: local(root, p) for p, a in by_path.items() if a["status"] == "current" and p.endswith(".html")})
    for path, p in pages.items():
        if not p.is_file():
            continue
        observed[path] = sha(p)
        page = Page(p.read_text(encoding="utf-8"))
        require(not page.base, f"base tag changes navigation resolution: {path}")
        require(not any(c == m["collection_id"] and state != "current" for c, state in page.blocks), f"history/draft navigation section forbidden: {path}")
        if path in entries:
            require(page.blocks.count((m["collection_id"], "current")) == 1, f"entry needs exactly one current collection block: {path}")
        linked = set()
        for href, collection, state in page.links:
            url = urlsplit(href)
            if url.scheme or url.netloc or not url.path:
                continue
            dest = (p.parent / unquote(url.path)).resolve()
            require(dest.is_relative_to(root.resolve()), f"local link escapes root: {path}: {href}")
            if not dest.is_relative_to(root.resolve()):
                continue
            require(dest.exists(), f"broken local link: {path}: {href}")
            rel = dest.relative_to(root.resolve()).as_posix()
            target = by_path.get(rel)
            if target:
                if target["status"] != "current":
                    require(False, f"obsolete artifact link forbidden: {path}: {href}")
                elif path in entries:
                    require(collection == m["collection_id"] and state == "current", f"current link outside current block: {path}: {href}")
                    linked.add(target["id"])
            elif collection == m["collection_id"] and state == "current" and dest.suffix.lower() in {".html", ".htm", ".md", ".ipynb"}:
                require(False, f"current entry links unregistered learning material: {path}: {href}")
        if path in entries:
            require(linked == {a["id"] for a in artifacts if a["status"] == "current"}, f"entry does not expose the complete current set: {path}")
    if m.get("operation") == "update":
        require(previous_path is not None, "update requires --previous; cannot reset to a fresh collection")
        if previous_path:
            old = json.loads(previous_path.read_text(encoding="utf-8"))
            require(m.get("previous_sha256") == sha(previous_path), "previous manifest fingerprint differs")
            for key in ("collection_id", "course", "period"):
                require(old.get(key) == m[key], f"update changed stable collection identity: {key}")
            require(old["subject"]["id"] == subject["id"], "update changed stable subject id")
            if old["subject"]["label"] != subject["label"]:
                text(subject.get("rename_basis"), "subject.rename_basis")
            if (old["scope"]["label"], old["scope"]["basis"]) != (scope["label"], scope["basis"]):
                require(old["scope"]["revision"] != scope["revision"], "changed scope must advance scope revision")
            for directory in old["inventory_roots"]:
                if directory not in inventory:
                    removal = next((v for v in m.get("inventory_removals", []) if v.get("path") == directory), None)
                    if removal:
                        text(removal.get("reason"), "inventory removal reason")
                        require(not local(root, directory).exists(), f"removed inventory root still exists: {directory}")
                        continue
                    transitions = m.get("inventory_transitions", [])
                    transition = next((v for v in transitions if v.get("from") == directory), None)
                    require(transition is not None, f"previous inventory root silently omitted: {directory}")
                    if transition:
                        text(transition.get("reason"), "inventory transition reason")
                        require(transition.get("to") in inventory and not local(root, directory).exists(),
                                f"inventory move incomplete; retain and scan old root: {directory}")
            for prior in old["artifacts"]:
                retained = by_id.get(prior["id"])
                if retained:
                    require(retained["sha256"] == prior["sha256"], f"changed content must receive a new revision id: {prior['id']}")
                    require(retained["kind"] == prior["kind"], f"prior artifact kind changed: {prior['id']}")
                elif prior["path"] not in by_path:
                    require(not local(root, prior["path"]).exists(), f"obsolete revision still exists: {prior['path']}")
            # A new current entity in an existing family must advance its revision.
            for a in artifacts:
                if a["status"] != "current":
                    continue
                ident = a["identity"]
                for prior in old["artifacts"]:
                    pi = prior.get("identity")
                    if (pi and prior["id"] != a["id"]
                            and (pi["purpose"], pi["variant"], Path(prior["path"]).suffix.lower())
                            == (ident["purpose"], ident["variant"], Path(a["path"]).suffix.lower())):
                        require(int(ident["revision"][1:]) > int(pi["revision"][1:]), f"revision did not advance: {a['id']}")
            for path in old["entrypoints"]:
                require(path in entries, f"previous entrypoint omitted: {path}")
            for obj in old.get("objects", []):
                if obj["id"] not in object_ids:
                    removal = next((v for v in m.get("removed_objects", []) if v.get("id") == obj["id"]), None)
                    require(bool(removal and removal.get("reason")), f"stable object silently removed: {obj['id']}")
            removed = m.get("removed_families", [])
            for item in removed:
                text(item.get("reason"), "removed family reason")
            for key in old["required"]:
                require(tuple(key) in required or any(item.get("key") == key for item in removed), f"required family silently removed: {key}")
    else:
        require(m.get("operation") == "create" and previous_path is None, "operation must be create or update")
    automatic_errors = list(errors)
    if review_path:
        review = json.loads(review_path.read_text(encoding="utf-8"))
        require(review.get("schema") == SCHEMA and review.get("manifest_sha256") == sha(manifest_path), "collection review is stale")
        text(review.get("reviewer"), "reviewer")
        # All current formats and complete entrypoint bytes are review-bound.
        all_review_files = {p: observed[p] for p in set(entries) | {a["path"] for a in artifacts if a["status"] == "current"} if p in observed}
        require(review.get("files") == all_review_files, "review omits a current artifact")
        for key in REVIEW_CHECKS:
            item = review.get("checks", {}).get(key, {})
            require(item.get("passed") is True and isinstance(item.get("note"), str) and bool(item["note"].strip()), f"semantic review missing: {key}")
        usability = review.get("usability", {})
        require(set(usability) == set(by_id), "usability review omits a current representation")
        for aid, a in by_id.items():
            item = usability.get(aid, {})
            require(item.get("topic") == a["identity"]["presentation"]["topic"], f"usability topic not checked: {aid}")
            require(item.get("purpose") == a["identity"]["purpose"], f"usability purpose not checked: {aid}")
            for field in ("open_with", "first_action", "evidence_locator"):
                require(isinstance(item.get(field), str) and bool(item[field].strip()), f"usability {field} missing: {aid}")
    else:
        errors.append("collection semantic review missing; generate --review-template, inspect actual pages, then --review")
    return {"schema": SCHEMA, "status": "failed" if errors else "passed", "scope": "course_collection_delivery",
            "manifest_sha256": sha(manifest_path), "files": observed,
            "automatic_errors": automatic_errors, "errors": errors,
            "exclusions": exclusions, "user_acceptance": "not_established_by_this_tool",
            "task_coverage": "not_checked_use_check_course_task", "acceptance_level": "collection_only",
            "harness_runtime": "not_executed_by_this_tool"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--review-template", type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    # The only writes are explicit review/report destinations, outside course content.
    for output in (args.report, args.review_template):
        if output and output.resolve().is_relative_to(args.root.resolve()):
            parser.error("review/report output must be outside the course root")
        if output and output.resolve() in {p.resolve() for p in (args.manifest, args.review, args.previous) if p}:
            parser.error("output must not overwrite input evidence")
    try:
        if args.review_template:
            args.review_template.write_text(json.dumps(review_template(args.manifest, args.root), ensure_ascii=False, indent=2) + "\n")
        result = check(args.manifest, args.root, args.review, args.previous)
    except (Exception, SystemExit) as exc:
        result = {"schema": SCHEMA, "status": "failed", "scope": "course_collection_delivery", "errors": [str(exc)]}
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
