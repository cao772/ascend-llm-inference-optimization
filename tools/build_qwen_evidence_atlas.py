#!/usr/bin/env python3
"""Build a provenance-first Qwen inference evidence graph (stdlib only).

Evidence links are not causal proofs. PRs may be removed/reverted; matching
model head shape is not evidence of runtime dispatch or performance.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from build_qwen_model_case_graph import LINKS, MATRIX, CASES_PATH, make_graph
from validate_operator_pr_lineage import DEFAULT as PRS_PATH, summarize

ROOT = Path(__file__).resolve().parents[1]
FAILURES_PATH = ROOT / "research/failures/qwen-operator-failure-modes-2026-10-31.json"
FAILURE_KINDS = {
    "deadlock", "numerical_regression", "guard_mismatch",
    "feature_removed", "benchmark_interpretation",
}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_atlas(cases, models, links, prs, failures):
    base = make_graph(cases, models, links)
    summarize(prs)
    case_ids = {c["id"] for c in cases["cases"]}
    mechanisms = set(cases["mechanism_vocabulary"])
    pr_index = {p["id"]: p for p in prs["entries"]}
    nodes = {n["id"]: dict(n) for n in base["nodes"]}
    edges = []
    keys = set()

    def add_edge(source, target, relation, urls, level, **kwargs):
        if source == target:
            raise ValueError("self-loop not supported")
        key = (source, target, relation)
        if key in keys:
            raise ValueError("Duplicate evidence relation: " + str(key))
        if not urls or not all(isinstance(u, str) and u.startswith("https://") for u in urls):
            raise ValueError("Every relation must carry HTTPS provenance")
        keys.add(key)
        edges.append({
            "source": source, "target": target, "relation": relation,
            "provenance_urls": list(dict.fromkeys(urls)),
            "evidence_level": level,
            "runtime_dispatch_verified_by_project": False,
            "speedup_verified_by_project": False,
            **kwargs,
        })

    # Normalize inherited graph edges. The original tags and similarity links
    # are analyst annotations, not upstream assertions of performance.
    for e in base["edges"]:
        src = nodes[e["source"]]
        if e["relation"] in {"tagged_operator", "tagged_mechanism", "shares_tags"}:
            urls = src.get("sources", [])
            if e["relation"] == "shares_tags":
                urls += nodes[e["target"]].get("sources", [])
                lvl = "derived_tag_cooccurrence"
            else:
                lvl = "analyst_coded_from_source"
        elif e["relation"] == "config_declares_architecture_feature":
            urls = [e["provenance"]]
            lvl = "official_model_config"
        else:
            urls = [e["source_url"]]
            lvl = "reviewed_case_to_model_source"
        add_edge(e["source"], e["target"], e["relation"], urls, lvl,
                 explicitly_noncausal=True)

    for pr in prs["entries"]:
        pid = "pr:" + pr["id"]
        nodes[pid] = {
            "id": pid, "kind": "upstream_pr", "label": pr["title"],
            "repo": pr["repo"], "number": pr["number"],
            "merge_commit": pr["merge_commit"], "merged_as_of_review": True,
            "source_paths": pr["path"], "source_url": pr["url"],
            "current_feature_presence": "not_determined_by_merge_status",
            "local_hardware_measurement": False,
        }
        for tag in pr["mechanisms"]:
            if tag not in mechanisms:
                raise ValueError("Unknown PR mechanism: " + tag)
            target = "mechanism:" + tag
            if target not in nodes:
                nodes[target] = {"id": target, "kind": "mechanism", "label": tag}
            add_edge(pid, target, "pr_discusses_mechanism", [pr["url"]],
                     "upstream_pr_source", noncausal_tag=True)
        for case_id in pr.get("cases", []):
            if case_id not in case_ids or not pr.get("case_link_scope", "").startswith("specific"):
                raise ValueError("PR has unverified direct case linkage: " + pr["id"])
            add_edge(pid, "case:" + case_id, "pr_documents_specific_case",
                     [pr["url"]], "curated_direct_pr_to_case",
                     only_case_specific_not_general_speedup=True)

    for lineage in prs["edges"]:
        pr_from, pr_to = "pr:" + lineage["from"], "pr:" + lineage["to"]
        add_edge(pr_from, pr_to, lineage["relation"], [lineage["source"]],
                 "upstream_pr_lifecycle", scoped_to_source_version=True)

    if failures.get("no_local_measurements") is not True or not isinstance(failures.get("failures"), list):
        raise ValueError("Failure catalog must identify no local measurements")
    failure_ids = set()
    for f in failures["failures"]:
        fid = "failure:" + f["id"]
        if fid in failure_ids or fid in nodes:
            raise ValueError("Duplicate failure id: " + fid)
        failure_ids.add(fid)
        if f["kind"] not in FAILURE_KINDS:
            raise ValueError("Unknown failure kind: " + f["kind"])
        if not f["source_urls"] or not all(x.startswith("https://") for x in f["source_urls"]):
            raise ValueError("Failure lacks HTTPS source")
        if not f["linked_case_ids"] and not f["linked_pr_ids"]:
            raise ValueError("Failure without any case/PR evidence link")
        nodes[fid] = {
            "id": fid, "kind": "failure_or_caveat", "label": f["title"],
            "failure_kind": f["kind"], "trigger": f["trigger"],
            "symptom": f["symptom"], "mitigation": f["mitigation"],
            "source_urls": f["source_urls"], "claim_type": f["claim_type"],
            "hardware_scope": f["hardware_scope"],
            "not_project_reproduced": True,
        }
        for pr_id in f["linked_pr_ids"]:
            if pr_id not in pr_index:
                raise ValueError("Failure references unknown PR: " + pr_id)
            add_edge(fid, "pr:" + pr_id, "failure_or_caveat_documented_by_pr",
                     f["source_urls"], "upstream_failure_review",
                     does_not_imply_pr_introduced_bug=True)
        for case_id in f["linked_case_ids"]:
            if case_id not in case_ids:
                raise ValueError("Failure references unknown case: " + case_id)
            add_edge(fid, "case:" + case_id, "case_has_documented_failure_or_caveat",
                     f["source_urls"], "upstream_case_risk",
                     does_not_imply_same_runtime_configuration=True)
        for tag in f["mechanisms"]:
            if tag not in mechanisms:
                raise ValueError("Unknown failure mechanism: " + tag)
            add_edge(fid, "mechanism:" + tag, "failure_relevant_to_mechanism",
                     f["source_urls"], "analyst_failure_tag",
                     noncausal_tag=True)

    # Only this PARTICULAR historical CUDA fused-GDN-MTP branch has 8:1 guard.
    # If a config is from main rather than pinned revision, preserve that fact.
    guard_pr = "pr:PR-VLLM-51674"
    for model in models["models"]:
        if model["pr51674_shape_guard_satisfied"] is False:
            add_edge("model:" + model["id"], guard_pr, "excludes_pr51674_head_ratio_branch",
                     [model["source"], pr_index["PR-VLLM-51674"]["url"]],
                     "static_official_config_plus_source_guard",
                     condition="linear_num_value_heads == 8 * linear_num_key_heads",
                     actual_ratio=model["gdn_v_per_k_ratio"],
                     config_verification=model["config_verification"],
                     not_a_universal_gdn_incompatibility=True)

    for e in edges:
        if e["source"] not in nodes or e["target"] not in nodes:
            raise ValueError("Dangling evidence graph edge: " + str(e))
    edges.sort(key=lambda e: (e["relation"], e["source"], e["target"]))
    counts = Counter(n["kind"] for n in nodes.values())
    ec = Counter(e["relation"] for e in edges)
    return {
        "schema_version": "2.0",
        "scope": "research evidence graph, not runtime or causal performance ontology",
        "source_collection_date": failures.get("curated_date"),
        "project_hardware_measurements": 0,
        "counts": {
            "nodes": len(nodes), "edges": len(edges),
            "by_node_kind": dict(sorted(counts.items())),
            "by_relation": dict(sorted(ec.items())),
        },
        "nodes": [nodes[k] for k in sorted(nodes)],
        "edges": edges,
        "rules": [
            "Upstream PR merge does not imply current code exists, model hits kernel, or speedup.",
            "Cross-model or cross-stage analogies are never direct case-to-PR claims.",
            "Model head-ratio exclusion is confined to vLLM PR #51674 branch.",
            "A reported microbenchmark result is not end-to-end serving performance.",
        ],
    }


def load_atlas():
    return build_atlas(
        _load(CASES_PATH), _load(MATRIX), _load(LINKS),
        _load(PRS_PATH), _load(FAILURES_PATH)
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        atlas = load_atlas()
    except (OSError, ValueError, KeyError, TypeError) as err:
        parser.error(str(err))
    raw = json.dumps(atlas, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw, encoding="utf-8")
        print(f"Evidence graph: {atlas['counts']['nodes']} nodes, {atlas['counts']['edges']} edges → {args.output}")
    else:
        print(raw, end="")


if __name__ == "__main__":
    main()
