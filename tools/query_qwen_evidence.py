#!/usr/bin/env python3
"""Deterministic offline retrieval over the sourced Qwen evidence atlas.

Supports exact model/PR/mechanism/failure kind and literal substring search.
This is *not* semantic/vector search, not a code-compatibility recommendation.
"""
import argparse
import json
from pathlib import Path

from build_qwen_evidence_atlas import load_atlas


def retrieve(atlas, selector, value, radius=1, max_anchors=10, max_nodes=60):
    if radius not in (0, 1, 2):
        raise ValueError("radius must be 0, 1 or 2")
    if not 1 <= max_anchors <= 100 or not 1 <= max_nodes <= 200:
        raise ValueError("invalid result bounds")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("nonempty value required")
    nodes = {n["id"]: n for n in atlas["nodes"]}
    allowed = {"case_id", "model_id", "pr_id", "mechanism", "operator", "failure_kind", "text"}
    if selector not in allowed:
        raise ValueError("unknown selector")
    norm = value.casefold()

    def match(n):
        nid = n["id"]
        if selector == "case_id":
            return nid == "case:" + value
        if selector == "model_id":
            return nid == "model:" + value
        if selector == "pr_id":
            return nid == "pr:" + value
        if selector == "mechanism":
            return nid == "mechanism:" + value
        if selector == "operator":
            return n["kind"] == "operator" and n["label"].casefold() == norm
        if selector == "failure_kind":
            return n["kind"] == "failure_or_caveat" and n["failure_kind"] == value
        return (norm in (n.get("label") or "").casefold() or
                (n["kind"] == "failure_or_caveat" and
                 any(norm in (n.get(k) or "").casefold()
                     for k in ("trigger", "symptom", "mitigation", "hardware_scope"))))

    matched = [n for n in atlas["nodes"] if match(n)]
    anchor_ids = sorted(n["id"] for n in matched)[:max_anchors]
    selected = set(anchor_ids)
    frontier = set(anchor_ids)
    seen_edges = {}
    # An edge is selected only if it is incident to the previous frontier.
    # Bound total nodes to prevent a high-degree mechanism from filling output.
    for _ in range(radius):
        next_frontier = set()
        for e in atlas["edges"]:
            a, b = e["source"], e["target"]
            if a not in frontier and b not in frontier:
                continue
            other = b if a in frontier else a
            if other not in selected and len(selected) >= max_nodes:
                continue
            key = (a, b, e["relation"])
            seen_edges[key] = e
            if other not in selected:
                selected.add(other)
                next_frontier.add(other)
        frontier = next_frontier
        if not frontier:
            break
    return {
        "query": {"selector": selector, "value": value, "radius": radius},
        "search_type": "exact_typed_or_literal_substring_only_not_semantic",
        "anchor_total": len(matched),
        "anchors_included": anchor_ids,
        "truncated_anchors": len(matched) > max_anchors,
        "nodes": [nodes[k] for k in sorted(selected)],
        "edges": sorted(seen_edges.values(), key=lambda e: (e["relation"], e["source"], e["target"])),
        "portability_or_speedup_proven": False,
        "note": "Edges include human-coded tags and upstream reported results; inspect evidence_level, provenance_urls and version scope.",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    s = p.add_mutually_exclusive_group(required=True)
    s.add_argument("--case-id")
    s.add_argument("--model-id")
    s.add_argument("--pr-id")
    s.add_argument("--mechanism")
    s.add_argument("--operator")
    s.add_argument("--failure-kind")
    s.add_argument("--text")
    p.add_argument("--radius", type=int, choices=(0, 1, 2), default=1)
    p.add_argument("--max-anchors", type=int, default=10)
    p.add_argument("--max-nodes", type=int, default=60)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    selector = next(k for k in (
        "case_id", "model_id", "pr_id", "mechanism",
        "operator", "failure_kind", "text",
    ) if getattr(a, k) is not None)
    try:
        result = retrieve(load_atlas(), selector, getattr(a, selector), a.radius, a.max_anchors, a.max_nodes)
    except (OSError, ValueError, KeyError, TypeError) as err:
        p.error(str(err))
    raw = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(raw, encoding="utf-8")
        print(f"{a.output}: {len(result['anchors_included'])} anchors, {len(result['nodes'])} nodes")
    else:
        print(raw, end="")


if __name__ == "__main__":
    main()
