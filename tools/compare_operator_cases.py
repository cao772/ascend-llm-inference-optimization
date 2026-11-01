#!/usr/bin/env python3
"""Cross-case mechanism overlap: descriptive links, NEVER a speedup predictor.

Usage:
  python3 tools/compare_operator_cases.py
  python3 tools/compare_operator_cases.py --min-shared 3 --output build/case-overlap.json
Only reads checked-in local JSON. No network access, no hardware access.
"""
import argparse
import itertools
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "research" / "cases" / "qwen-optimization-cases-2026-10-30.json"

REQUIRED = ("id", "name", "model", "hardware", "engine", "workload",
            "stage", "evidence_status", "mechanisms", "operators", "source_urls")
UNMEASURED = {
    "proposal_not_measurement",
    "open_source_benchmark_tool_not_measured_here",
    "open_source_method_no_benchmark",
}


def validate(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise ValueError("expected object with cases array")
    cases = payload["cases"]
    seen = set()
    vocab = set(payload.get("mechanism_vocabulary", []))
    for case in cases:
        if any(field not in case for field in REQUIRED):
            raise ValueError(f"missing required fields: {case.get('id')}")
        if case["id"] in seen:
            raise ValueError(f"duplicate case id: {case['id']}")
        seen.add(case["id"])
        if not isinstance(case["mechanisms"], list) or not set(case["mechanisms"]) <= vocab:
            raise ValueError(f"unknown mechanism tags in {case['id']}")
        if len(set(case["mechanisms"])) != len(case["mechanisms"]):
            raise ValueError(f"duplicate tags in {case['id']}")
        if not case["source_urls"] or not all(
            isinstance(u, str) and u.startswith("https://") for u in case["source_urls"]
        ):
            raise ValueError(f"missing or non-HTTPS source URLs: {case['id']}")
        if case["evidence_status"] in UNMEASURED and case.get("outcome") is not None:
            raise ValueError(f"unmeasured case must not have benchmark outcome: {case['id']}")
    return cases


def compare(payload, min_shared=2, include_proposals=False):
    if min_shared < 1:
        raise ValueError("min_shared must be positive")
    cases = validate(payload)
    selected = [x for x in cases if include_proposals or x["evidence_status"] not in UNMEASURED]
    frequencies = Counter(tag for x in selected for tag in x["mechanisms"])
    evidence_counts = Counter(x["evidence_status"] for x in cases)
    pairs = []
    for a, b in itertools.combinations(selected, 2):
        shared = sorted(set(a["mechanisms"]) & set(b["mechanisms"]))
        if len(shared) < min_shared:
            continue
        same_context_labels = all(a[k] == b[k] for k in ("model", "hardware", "workload", "stage"))
        pairs.append({
            "a": a["id"], "b": b["id"], "shared_mechanisms": shared,
            "overlap_count": len(shared),
            "same_context_labels": same_context_labels,
            "performance_comparison_allowed": False,
            "portability": "hypothesis_only",
        })
    pairs.sort(key=lambda x: (-x["overlap_count"], x["a"], x["b"]))
    return {
        "schema_version": "1.0",
        "purpose": "shared technical mechanisms only (not performance ranking, prediction, or validated portability)",
        "included_cases": len(selected),
        "all_cases": len(cases),
        "evidence_status_counts": dict(sorted(evidence_counts.items())),
        "include_proposals": include_proposals,
        "frequencies": dict(sorted(frequencies.items(), key=lambda x: (-x[1], x[0]))),
        "pairs": pairs,
        "notes": [
            "Same tag does not imply code is portable between NPU, GPU, TPU or Metal.",
            "Operator microbenchmarks and end-to-end serving results cannot be compared directly.",
            "Original authors' metrics are not measured by this project.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=CASES_PATH)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--min-shared", type=int, default=2)
    parser.add_argument("--include-proposals", action="store_true")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        report = compare(data, min_shared=args.min_shared, include_proposals=args.include_proposals)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    content = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
        print(f"Saved {len(report['pairs'])} shared-mechanism links from {report['included_cases']} cases: {args.output}")
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
