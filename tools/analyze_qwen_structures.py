#!/usr/bin/env python3
"""Inspect Qwen config.json without loading weights, torch, HF Hub or accelerators.

Two supported operations:
  python tools/analyze_qwen_structures.py --matrix
  python tools/analyze_qwen_structures.py --config /path/to/config.json --model-id Qwen/...
A "guard ruled out" finding is tied ONLY to vLLM PR #51674 historical source.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "research/model-structures/qwen-gdn-structure-matrix-2026-10-30.json"
PR_GUARD = "https://github.com/vllm-project/vllm/pull/51674"


def _safe_count(v):
    return isinstance(v, int) and not isinstance(v, bool) and v > 0


def from_config(raw, model_id, source="user_supplied_config"):
    if not isinstance(raw, dict):
        raise ValueError("config must be a JSON object")
    cfg = raw.get("text_config", raw)
    if not isinstance(cfg, dict):
        raise ValueError("text_config must be a JSON object")
    layers = cfg.get("layer_types")
    num_layers = cfg.get("num_hidden_layers")
    if layers is not None and (not isinstance(layers, list) or
                               not all(x in {"linear_attention", "full_attention"} for x in layers)):
        raise ValueError("layer_types includes an unknown or invalid layer type")
    if layers is not None and _safe_count(num_layers) and len(layers) != num_layers:
        raise ValueError("layer_types length does not equal num_hidden_layers")
    k, v = cfg.get("linear_num_key_heads"), cfg.get("linear_num_value_heads")
    ratio = (v / k) if _safe_count(k) and _safe_count(v) else None
    guard = ("ruled_out_by_known_head_ratio" if ratio is not None and v != 8 * k else
             "head_ratio_satisfied_not_runtime_verified" if ratio is not None else
             "unknown_insufficient_head_metadata")
    experts = cfg.get("num_experts")
    if experts is None:
        moe = False if cfg.get("intermediate_size") is not None else "unknown"
    else:
        moe = _safe_count(experts)
    return {
        "model_id": model_id,
        "architecture": raw.get("architectures", []),
        "text_model_type": cfg.get("model_type"),
        "model_dtype": cfg.get("dtype", raw.get("torch_dtype")),
        "num_hidden_layers": num_layers,
        "layer_types_explicit": layers is not None,
        "linear_attention_layers": layers.count("linear_attention") if layers is not None else None,
        "full_attention_layers": layers.count("full_attention") if layers is not None else None,
        "full_attention_interval": cfg.get("full_attention_interval"),
        "has_linear_attention_config": _safe_count(k) and _safe_count(v),
        "linear_num_key_heads": k,
        "linear_num_value_heads": v,
        "gdn_v_per_k_ratio": ratio,
        "num_experts": experts,
        "num_experts_per_tok": cfg.get("num_experts_per_tok"),
        "moe": moe,
        "mtp_num_hidden_layers": cfg.get("mtp_num_hidden_layers"),
        "pr51674_head_ratio_check": guard,
        "source": source,
        "source_pr": PR_GUARD,
        "runtime_dispatch_verified": False,
        "performance_verified_by_project": False,
    }


def validate_matrix(data):
    if not isinstance(data, dict) or not isinstance(data.get("models"), list):
        raise ValueError("expected a model matrix")
    found = set()
    results = []
    for m in data["models"]:
        if m["id"] in found:
            raise ValueError("duplicate model id")
        found.add(m["id"])
        k, v = m["linear_num_key_heads"], m["linear_num_value_heads"]
        if not (_safe_count(k) and _safe_count(v)):
            raise ValueError("invalid linear attention head numbers")
        if m["gdn_v_per_k_ratio"] != v / k:
            raise ValueError("incorrect v/k ratio")
        if m["pr51674_shape_guard_satisfied"] != (v == 8 * k):
            raise ValueError("incorrect shape guard")
        if m["layer_types_explicit"]:
            a, b, n = (m["linear_attention_layers"],
                       m["full_attention_layers"], m["num_hidden_layers"])
            if a is None or b is None or a + b != n:
                raise ValueError("layer count does not match")
        elif m["linear_attention_layers"] is not None or m["full_attention_layers"] is not None:
            raise ValueError("do not pretend inferred layers were explicit")
        if m["moe"] and not _safe_count(m.get("num_experts")):
            raise ValueError("MoE model missing experts")
        results.append({
            "id": m["id"],
            "gdn_ratio": m["gdn_v_per_k_ratio"],
            "pr51674_shape_guard_satisfied": m["pr51674_shape_guard_satisfied"],
            "moe": m["moe"],
            "layer_count_explicit": m["layer_types_explicit"],
            "layers": [m["linear_attention_layers"], m["full_attention_layers"]],
            "source": m["source"],
            "config_verification": m["config_verification"],
        })
    return {
        "model_count": len(results),
        "cases": results,
        "source_pr": data["pr_guard"],
        "validated_as": "static curated config attributes only",
        "all_real_hardware_speedups_unknown": True,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--matrix", action="store_true")
    group.add_argument("--config", type=Path)
    p.add_argument("--model-id", help="required when using --config")
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    if args.config and not args.model_id:
        p.error("--model-id is required with --config")
    try:
        if args.matrix:
            data = json.loads(MATRIX.read_text("utf-8"))
            out = validate_matrix(data)
        else:
            data = json.loads(args.config.read_text("utf-8"))
            out = from_config(data, args.model_id, str(args.config))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        p.error(str(exc))
    rendered = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, "utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
