#!/usr/bin/env python3
"""Build falsifiable Qwen inference optimization pathways, WITHOUT profiling/hardware.

This project can evaluate official model structure and upstream source constraints.
It CANNOT discover the bottleneck or estimate speedup with no device/trace.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_qwen_structures import MATRIX, validate_matrix
from build_qwen_evidence_atlas import CASES_PATH, PRS_PATH, FAILURES_PATH, _load

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "research/decisions/qwen-fullchain-hypotheses-v1.json"
ALLOWED_PRIORITIES = ("P0", "BLOCK", "P1", "P2")
APPLICABILITY = {"all", "ascend", "cuda", "moe", "dense", "linear_attention", "mtp"}
STAGES = {"all", "prefill", "decode"}
REQUIRED_METRIC_FIELDS = (
    "TTFT_p50_ms", "TTFT_p95_ms", "TPOT_p50_ms", "TPOT_p95_ms",
    "E2E_p50_ms", "E2E_p95_ms", "output_tokens_s", "requests_s",
)


def _model_features(model):
    return {
        "moe": model["moe"],
        "gdn_or_linear_attention": bool(
            model.get("linear_attention_layers") or
            (model.get("linear_num_key_heads") and model.get("linear_num_value_heads"))
        ),
        "mtp_config_present": model.get("mtp_num_hidden_layers") is not None,
        "num_experts": model.get("num_experts"),
        "num_experts_per_tok": model.get("num_experts_per_tok"),
        "gdn_head_ratio": model["gdn_v_per_k_ratio"],
        "linear_attention_layers_explicit": model.get("linear_attention_layers"),
        "full_attention_layers_explicit": model.get("full_attention_layers"),
        "model_config_source": model["source"],
        "config_verification": model["config_verification"],
        "pr51674_8to1_shape_guard_satisfied": model["pr51674_shape_guard_satisfied"],
    }


def _match_tags(h, features, scenario):
    tags = set(h["applies_to"])
    allowed = {"all", scenario["platform"]}
    allowed.add("moe" if features["moe"] else "dense")
    if features["gdn_or_linear_attention"]:
        allowed.add("linear_attention")
    if features["mtp_config_present"]:
        allowed.add("mtp")
    return tags <= (allowed | {"all"})


def _match_stage(h, scenario):
    stage = h["stage"]
    return stage == "all" or scenario["stage"] == stage or scenario["stage"] == "mixed"


def validate_input(rules, model_db, cases, prs, failures):
    validate_matrix(model_db)
    if rules.get("deployment_available") is not False or rules.get("benchmark_observations") != []:
        raise ValueError("No environment yet: must not assert measurements")
    model_ids = {m["id"] for m in model_db["models"]}
    case_ids = {c["id"] for c in cases["cases"]}
    pr_ids = {p["id"] for p in prs["entries"]}
    failure_ids = {f["id"] for f in failures["failures"]}
    scenario_ids, h_ids = set(), set()
    if not rules.get("pipeline") or len(rules["pipeline"]) != 6:
        raise ValueError("Expected six end-to-end pipeline stages")
    for s in rules["scenarios"]:
        if s["id"] in scenario_ids or s["model"] not in model_ids:
            raise ValueError("Invalid/duplicate scenario or unknown official model")
        scenario_ids.add(s["id"])
        if s["platform"] not in {"ascend", "cuda"} or s["stage"] not in {"prefill", "decode", "mixed"}:
            raise ValueError("Bad stage/platform")
        if not isinstance(s["concurrency"], int) or s["concurrency"] <= 0:
            raise ValueError("Bad scenario concurrency")
        if not set(s["reference_case_ids"]) <= case_ids:
            raise ValueError("Unknown external case reference")
        if s["platform"] == "ascend" and "910C" not in s["hardware"]:
            raise ValueError("Ascend scenario should explicitly identify hypothetical chip")
    for h in rules["hypotheses"]:
        if h["id"] in h_ids:
            raise ValueError("Duplicate hypothesis")
        h_ids.add(h["id"])
        if h["priority"] not in ALLOWED_PRIORITIES or h["stage"] not in STAGES:
            raise ValueError("Unsupported hypothesis status")
        if not set(h["applies_to"]) <= APPLICABILITY or not h["applies_to"]:
            raise ValueError("Unsupported applicability tags")
        if not set(h["related_pr_ids"]) <= pr_ids or not set(h["related_failure_ids"]) <= failure_ids:
            raise ValueError("Hypothesis references non-curated PR/failure")
        if not h.get("evidence") or not all(x.startswith("https://") for x in h["evidence"]):
            raise ValueError("Every hypothesis requires HTTPS evidence")
        for key in ("reason", "predict_if", "measure", "acceptance", "rollback", "inference_level"):
            if not h.get(key):
                raise ValueError("Incomplete falsifiable hypothesis: " + key)
    if not set(REQUIRED_METRIC_FIELDS) <= set(rules["measurement_contract"]["latency"]):
        raise ValueError("Missing required E2E metric contract")
    return True


def decide(rules, model_db, cases, prs, failures):
    validate_input(rules, model_db, cases, prs, failures)
    models = {m["id"]: m for m in model_db["models"]}
    pr_urls = {p["id"]: p["url"] for p in prs["entries"]}
    failure_urls = {f["id"]: list(f["source_urls"]) for f in failures["failures"]}
    all_scenarios = []
    for s in rules["scenarios"]:
        features = _model_features(models[s["model"]])
        selected = []
        omitted = []
        for h in rules["hypotheses"]:
            if not _match_tags(h, features, s) or not _match_stage(h, s):
                omitted.append(h["id"])
                continue
            item = {
                "id": h["id"],
                "name": h["name"],
                "topic": h["topic"],
                "stage": h["stage"],
                "priority": h["priority"],
                "decision": {
                    "BLOCK": "exclude_specific_legacy_or_shape_incompatible_path",
                    "P0": "must_validate_or_measure_first",
                    "P1": "conditional_experiment_candidate",
                    "P2": "conditional_later_research",
                }[h["priority"]],
                "assessment_type": h["inference_level"],
                "current_status": "confirmed_static_exclusion_only" if h["priority"] == "BLOCK"
                    else "documented_prerequisite_not_fulfilled" if h["priority"] == "P0"
                    else "hypothesis_unverified",
                "reason": h["reason"],
                "conditional_prediction": h["predict_if"],
                "evidence": h["evidence"],
                "related_pr_ids": h["related_pr_ids"],
                "related_pr_urls": [pr_urls[key] for key in h["related_pr_ids"]],
                "related_failure_ids": h["related_failure_ids"],
                "related_failure_sources": [
                    {"id": key, "sources": failure_urls[key]} for key in h["related_failure_ids"]
                ],
                "measure": h["measure"],
                "acceptance": h["acceptance"],
                "rollback": h["rollback"],
                "flags": h["flags"],
                "model_runtime_eligible": None,
                "has_runtime_trace": False,
                "hardware_benchmark_observed": False,
                "speedup_pct": None,
            }
            selected.append(item)
        selected.sort(key=lambda z: (ALLOWED_PRIORITIES.index(z["priority"]), z["id"]))
        all_scenarios.append({
            "id": s["id"],
            "title": s["title"],
            "model": s["model"],
            "hardware": s["hardware"],
            "platform": s["platform"],
            "framework_target": s["framework_target"],
            "stage": s["stage"],
            "concurrency": s["concurrency"],
            "tp": s["tp"],
            "ep": s["ep"],
            "input_tokens": s["isl"],
            "output_tokens": s["osl"],
            "latency_goal": s["latency_goal"],
            "description": s["description"],
            "hypothetical_configuration": True,
            "compatibility_confirmed": False,
            "hardware_environment_available": False,
            "reference_case_ids": s["reference_case_ids"],
            "uncertainties": s["uncertainties"],
            "static_model_facts": features,
            "candidate_count": sum(x["priority"] in {"P1", "P2"} for x in selected),
            "excluded_path_count": sum(x["priority"] == "BLOCK" for x in selected),
            "priority_actions": selected,
            "not_applicable_hypotheses": omitted,
            "observed_results": {k: None for k in REQUIRED_METRIC_FIELDS},
            "measurement_status": "not_measured",
            "decision_status": "research_only_not_deployable",
            "entry_gates": {
                "model_structure": "reviewed_static_config_not_runtime_verified",
                "chip_compatibility": "unverified",
                "runtime_baseline": "missing",
                "profiling": "missing",
                "correctness": "not_tested",
                "optimization_ab": "not_tested",
                "production_rollout": "not_authorized",
            },
        })
    return {
        "schema_version": "1.0",
        "generated_from_rules_date": rules["as_of"],
        "mode": "static_evidence_plus_falsifiable_inference_only",
        "deployment_available": False,
        "real_hardware_measurements": 0,
        "claims": {
            "evidence": "source-grounded official model config and public framework docs/PRs",
            "inference": "conditioned hypotheses for future profiling / A-B experiments",
            "result": "static eligibility and experiment plan only; no observed performance or predicted numeric gain",
        },
        "pipeline": rules["pipeline"],
        "measurement_contract": rules["measurement_contract"],
        "source_counts": {
            "external_case_records": len(cases["cases"]),
            "official_model_structures": len(model_db["models"]),
            "upstream_pr_records": len(prs["entries"]),
            "failure_or_limit_records": len(failures["failures"]),
        },
        "hypotheses_total": len(rules["hypotheses"]),
        "scenario_count": len(all_scenarios),
        "scenarios": all_scenarios,
        "overall_interpretation": [
            "First secure version/chip/model compatibility and profile baseline; otherwise no actual bottleneck ranking exists.",
            "MoE expert routing and Dense sequence parallelism branch based on architecture; GDN exists in both.",
            "GDN prefill and decode kernels require different guards, workloads and correctness tests.",
            "Old Ascend deleted fusions and the 8:1 CUDA MTP branch are explicitly rejected for the studied scope.",
            "Activation of any feature and throughput improvement remain unknown until hardware traces and paired A/B."
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rules", type=Path, default=RULES)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    try:
        report = decide(
            _load(a.rules), _load(MATRIX), _load(CASES_PATH),
            _load(PRS_PATH), _load(FAILURES_PATH)
        )
    except (ValueError, OSError, TypeError, KeyError) as err:
        p.error(str(err))
    raw = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(raw, encoding="utf-8")
        print(f"Pathways: {report['scenario_count']} scenarios, {report['hypotheses_total']} hypotheses → {a.output}")
    else:
        print(raw, end="")


if __name__ == "__main__":
    main()
