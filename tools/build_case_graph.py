#!/usr/bin/env python3
"""Build a source-grounded Qwen inference research graph from curated case JSON.

Edges represent human-curated co-occurrence, NOT causality or performance portability.
No network, model downloads or hardware calls.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from compare_operator_cases import CASES_PATH, UNMEASURED, compare, validate


def build(payload, min_shared=2):
    cases = validate(payload)
    nodes = {}
    edges = []
    seen_edges = set()

    def node(node_id, kind, label, **kwargs):
        if node_id not in nodes:
            nodes[node_id] = {"id": node_id, "kind": kind, "label": label, **kwargs}

    def edge(src, dst, kind, **kwargs):
        key = (src, dst, kind)
        if key in seen_edges:
            return
        seen_edges.add(key)
        edges.append({"source": src, "target": dst, "relation": kind, **kwargs})

    for c in cases:
        cid = "case:" + c["id"]
        measured = c["evidence_status"] not in UNMEASURED
        node(cid, "case", c["name"], evidence_status=c["evidence_status"],
             measured_by_our_project=False, externally_reported_metric=measured and c.get("outcome") is not None,
             sources=c["source_urls"])
        for term in c["mechanisms"]:
            mid = "mechanism:" + term
            node(mid, "mechanism", term)
            edge(cid, mid, "tagged_mechanism", provenance=c["id"])
        for term in c["operators"]:
            oid = "operator:" + term.lower().replace(" ", "_")
            node(oid, "operator", term)
            edge(cid, oid, "tagged_operator", provenance=c["id"])
    pairs = compare(payload, min_shared=min_shared)
    for p in pairs["pairs"]:
        edge("case:" + p["a"], "case:" + p["b"], "shares_tags",
             mechanism_tags=p["shared_mechanisms"],
             performance_comparison_allowed=False, code_portability_verified=False)
    kinds = defaultdict(int)
    for n in nodes.values():
        kinds[n["kind"]] += 1
    return {
        "schema_version": "1.0",
        "semantics": "case-to-tag references and case-to-case tag overlap only; not an ontology of validated causal kernel gains",
        "project_hardware_benchmarks": 0,
        "nodes": [nodes[k] for k in sorted(nodes)],
        "edges": sorted(edges, key=lambda e: (e["relation"], e["source"], e["target"])),
        "counts": {"case_count": len(cases), "nodes_by_kind": dict(sorted(kinds.items())),
                   "edge_count": len(edges), "shared_pairs": len(pairs["pairs"])},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=CASES_PATH)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--min-shared", type=int, default=2)
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        graph = build(payload, min_shared=args.min_shared)
    except (OSError, ValueError, json.JSONDecodeError) as err:
        parser.error(str(err))
    data = json.dumps(graph, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(data, encoding="utf-8")
        print(f"Graph: {graph['counts']['case_count']} cases, {graph['counts']['edge_count']} edges → {args.output}")
    else:
        print(data, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
