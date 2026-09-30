#!/usr/bin/env python3
"""Read-only heuristic audit of numeric prose against saved Jupyter outputs.

Usage: python3 audit_notebook_numbers.py notebook.ipynb [--audit] [--stale TEXT]
This does not execute code or prove a conclusion correct; inspect every flagged value.
"""

import argparse
import json
import re
from pathlib import Path


NUMBER = re.compile(r"\b\d[\d,]*(?:\.\d+)?\b")


def as_text(value):
    return "".join(value) if isinstance(value, list) else (value or "")


def saved_output(cell):
    parts = []
    for output in cell.get("outputs", []):
        if output.get("output_type") == "stream":
            parts.append(as_text(output.get("text")))
        elif output.get("output_type") in ("execute_result", "display_data"):
            parts.append(as_text(output.get("data", {}).get("text/plain")))
    return "\n".join(parts)


def audit(path, check_numbers=False, stale=None):
    notebook = json.loads(Path(path).read_text(encoding="utf-8"))
    cells = notebook.get("cells", [])
    if not isinstance(cells, list):
        raise ValueError("Notebook cells must be a list")
    code = [(i, c) for i, c in enumerate(cells) if c.get("cell_type") == "code"]
    errors = [(i, o.get("ename", "error")) for i, c in code for o in c.get("outputs", []) if o.get("output_type") == "error"]
    unrun = [i for i, c in code if c.get("execution_count") is None]
    print(f"notebook={path} cells={len(cells)} code={len(code)} unrun={len(unrun)} errors={len(errors)}")
    for i, name in errors:
        print(f"error cell={i}: {name}")
    if unrun:
        print("unrun cells=" + ",".join(map(str, unrun)))
    if stale:
        for term in stale:
            hits = [i for i, c in enumerate(cells) if term in as_text(c.get("source"))]
            print(f"stale {term!r}: cells={hits}")
    if check_numbers:
        output_nums = {n.replace(",", "") for _, c in code for n in NUMBER.findall(saved_output(c))}
        for i, cell in enumerate(cells):
            if cell.get("cell_type") != "markdown":
                continue
            candidates = {n for n in NUMBER.findall(as_text(cell.get("source"))) if len(n.replace(",", "").replace(".", "")) >= 3}
            unmatched = sorted(n for n in candidates if n.replace(",", "") not in output_nums)
            if unmatched:
                print(f"review cell={i}: {', '.join(unmatched)}")
        print("review entries are possible mismatches, not automatic errors")
    return 1 if errors else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook")
    parser.add_argument("--audit", action="store_true", help="flag prose numbers absent from saved text outputs")
    parser.add_argument("--stale", action="append", help="find an obsolete string in cell sources")
    args = parser.parse_args()
    raise SystemExit(audit(args.notebook, args.audit, args.stale))
