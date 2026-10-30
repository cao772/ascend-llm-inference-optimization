#!/usr/bin/env python3
"""Join case-mechanism graph with official Qwen *structure*, never speedup.

No fuzzy model matching: only a hand-reviewed, source-linked bridge is used.
Unknown model/PR applicability is not silently promoted to "supported".
"""
import argparse
import json
from pathlib import Path

from analyze_qwen_structures import MATRIX, validate_matrix
from build_case_graph import CASES_PATH, build

ROOT = Path(__file__).resolve().parents[1]
LINKS = ROOT / "research/model-structures/case-model-evidence-links-2026-10-30.json"
ALLOWED = {"exact_model_mentioned", "quantized_derivative_structure_only"}


def make_graph(cases, structures, associations):
    graph = build(cases)
    checked = validate_matrix(structures)
    existing = {c["id"] for c in cases["cases"]}
    selected = {x["id"]: x for x in structures["models"]}
    nodes = {x["id"]: x for x in graph["nodes"]}
    edges = list(graph["edges"])
    seen = set()
    for model in structures["models"]:
        mid = "model:" + model["id"]
        nodes[mid] = {
            "id": mid, "kind": "model", "label": model["id"],
            "moe": model["moe"], "gdn_head_ratio": model["gdn_v_per_k_ratio"],
            "pr51674_head_ratio_satisfied": model["pr51674_shape_guard_satisfied"],
            "official_config_source": model["source"],
            "layer_types_explicit": model["layer_types_explicit"],
            "code_compatibility_verified": False,
            "runtime_dispatch_verified": False,
        }
        if model["moe"]:
            nodes["feature:moe"] = {"id": "feature:moe", "kind": "architecture_feature", "label": "Mixture of Experts"}
            edges.append({"source": mid, "target": "feature:moe",
                          "relation": "config_declares_architecture_feature", "provenance": model["source"]})
        if model["layer_types_explicit"] and model["linear_attention_layers"] > 0:
            nodes["feature:linear_attention"] = {
                "id": "feature:linear_attention", "kind": "architecture_feature", "label": "GDN/linear attention layers"
            }
            edges.append({"source": mid, "target": "feature:linear_attention",
                          "relation": "config_declares_architecture_feature", "provenance": model["source"]})
    for link in associations["links"]:
        case, model, kind, source = link["case_id"], link["model_id"], link["kind"], link["source"]
        if case not in existing or model not in selected:
            raise ValueError("Case-model link points to missing curated case/model")
        if kind not in ALLOWED or not source.startswith("https://"):
            raise ValueError("Link lacks supported type or HTTPS source")
        if (case, model) in seen:
            raise ValueError("Duplicate case-model association")
        seen.add((case, model))
        edges.append({
            "source": "case:" + case, "target": "model:" + model,
            "relation": "case_mentions_exact_model" if kind == "exact_model_mentioned" else "case_uses_quantized_derivative",
            "source_url": source,
            "model_structure_not_performance_equivalence": True,
            "runtime_dispatch_verified": False,
        })
    return {
        "schema_version": "1.0", "purpose": "evidence-tagged research graph, not a validated operator compatibility graph",
        "no_local_measurement": True,
        "model_count": checked["model_count"], "case_count": len(cases["cases"]),
        "case_model_links": len(associations["links"]),
        "nodes": [nodes[k] for k in sorted(nodes)],
        "edges": sorted(edges, key=lambda x: (x["relation"], x["source"], x["target"])),
        "limitations": [
            "Model config architecture features do not prove a specific backend kernel is dispatched.",
            "Quantized derivatives may differ from official BF16 checkpoints.",
            "Shared mechanism tags are hypotheses, not portable source code or performance estimates.",
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        case_data = json.loads(CASES_PATH.read_text("utf-8"))
        matrix = json.loads(MATRIX.read_text("utf-8"))
        links = json.loads(LINKS.read_text("utf-8"))
        result = make_graph(case_data, matrix, links)
    except (ValueError, OSError, TypeError, KeyError) as exc:
        p.error(str(exc))
    raw = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw, encoding="utf-8")
        print(f"{args.output}: {result['case_count']} cases, {result['model_count']} models")
    else:
        print(raw, end="")


if __name__ == "__main__":
    main()
