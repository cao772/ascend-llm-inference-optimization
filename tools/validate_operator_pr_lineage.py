#!/usr/bin/env python3
"""Validate and summarize upstream PR lineage; does not call GitHub or execute kernels."""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "research/source-traces/qwen-operator-pr-lineage-2026-10-30.json"
RELATIONS = {
    "reverted_by", "reintroduced_with_safety_guard_by",
    "determinism_regression_mitigated_by", "subprocess_deadlock_fixed_by",
    "fix_required_before_enable",
}


def summarize(data):
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise ValueError("Expected entries list")
    entries = data["entries"]
    ids = [x["id"] for x in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate PR identifier")
    entry_index = {e["id"]: e for e in entries}
    for e in entries:
        expected_url = f"https://github.com/{e['repo']}/pull/{e['number']}"
        if e.get("url") != expected_url:
            raise ValueError(f"Incorrect PR URL: {e['id']}")
        if not re.fullmatch(r"[0-9a-f]{40}", e.get("merge_commit", "")):
            raise ValueError(f"Invalid merge commit: {e['id']}")
        if e.get("merged") is not True or e.get("measured_by_us") is not False:
            raise ValueError(f"Unverified source or local benchmark asserted: {e['id']}")
        if not isinstance(e.get("path"), list) or not e["path"]:
            raise ValueError(f"Missing source path: {e['id']}")
    for edge in data.get("edges", []):
        if edge["from"] not in entry_index or edge["to"] not in entry_index:
            raise ValueError("Lineage edge references unknown PR")
        if edge["relation"] not in RELATIONS:
            raise ValueError("Unrecognized lifecycle relation")
        if edge.get("source") not in (entry_index[edge["from"]]["url"], entry_index[edge["to"]]["url"]):
            raise ValueError("Lineage relation must cite one of its PR endpoints")
    repo_counts = Counter(x["repo"] for x in entries)
    return {
        "verified_merged_pr_count_by_connector": len(entries),
        "project_measured_kernels": 0,
        "pr_by_repo": dict(sorted(repo_counts.items())),
        "lifecycle_edges": data.get("edges", []),
        "excluded_from_perf_ranking": True,
        "evidence_limit": "PR statuses/code metadata verified; no GPU/NPU tests, no proven cross-platform speedups.",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=DEFAULT)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    try:
        d = json.loads(a.input.read_text(encoding="utf-8"))
        out = summarize(d)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        p.error(str(exc))
    text = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
