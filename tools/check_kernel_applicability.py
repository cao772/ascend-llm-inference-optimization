#!/usr/bin/env python3
"""Offline, three-valued *documented-guard* checker for selected upstream Qwen kernels.

Does not initialize CUDA/NPU, load weights or prove dispatch. It evaluates only
specific source-level guards from pinned upstream PRs against user-supplied facts.
Unknown input -> unknown, not "supported"; an explicit failed guard -> ruled out.
"""
import argparse
import json
from pathlib import Path

SOURCES = {
    "vllm_gdn_mtp_51674": "https://github.com/vllm-project/vllm/pull/51674",
    "vllm_flashinfer_gdn_prefill_40717": "https://github.com/vllm-project/vllm/pull/40717",
    "sglang_flashinfer_allreduce_deterministic_24629": "https://github.com/sgl-project/sglang/pull/24629",
}


def require_equal(facts, key, wanted):
    if key not in facts or facts[key] is None:
        return None
    return facts[key] == wanted


def require_member(facts, key, allowed):
    if key not in facts or facts[key] is None:
        return None
    return facts[key] in allowed


def require_positive(facts, key):
    if key not in facts or facts[key] is None:
        return None
    n = facts[key]
    return isinstance(n, int) and not isinstance(n, bool) and n > 0


def require_less_or_equal(facts, key, max_value):
    if key not in facts or facts[key] is None:
        return None
    n = facts[key]
    return isinstance(n, int) and not isinstance(n, bool) and 0 < n <= max_value


def head_ratio(facts):
    a, b = facts.get("num_v_heads"), facts.get("num_k_heads")
    if a is None or b is None:
        return None
    if not all(isinstance(n, int) and not isinstance(n, bool) and n > 0 for n in (a, b)):
        return False
    return a == 8 * b


def is_true(facts, key):
    if key not in facts or facts[key] is None:
        return None
    return facts[key] is True


def mtp_decode_checks(facts):
    """PR #51674 (_can_use_fused_gdn_mtp_decode) + build prerequisite."""
    return {
        "has_spec_sequence_masks": is_true(facts, "has_spec_sequence_masks"),
        "ordinary_decode_count_is_zero": require_equal(facts, "num_decodes", 0),
        "spec_decode_count_positive": require_positive(facts, "num_spec_decodes"),
        "recurrent_state_dtype_allowed": require_member(facts, "state_dtype", ("bfloat16", "float32")),
        "decode_kernel_is_cuda": require_equal(facts, "gdn_decode_kernel", "cuda"),
        "num_v_heads_is_8_times_num_k_heads": head_ratio(facts),
        "state_indices_present": is_true(facts, "state_indices_present"),
        "spec_state_width_at_most_8": require_less_or_equal(facts, "state_indices_width", 8),
        "fused_op_built": is_true(facts, "fused_op_built"),
    }


def prefill_checks(facts):
    """PR #40717 guards only. Blackwell also needs installed DSL runtime."""
    requested = require_member(facts, "backend", ("auto", "flashinfer"))
    cuda = require_equal(facts, "platform", "cuda")
    family = facts.get("cuda_sm_family")
    if family is None:
        arch = None
    elif family == 90:
        arch = True
    elif family == 100:
        dim = require_equal(facts, "head_k_dim", 128)
        runtime = facts.get("cuda_runtime_major")
        runtime_check = None if runtime is None else (
            isinstance(runtime, int) and not isinstance(runtime, bool) and runtime >= 13
        )
        dsl = is_true(facts, "cutlass_dsl_installed")
        arch = False if False in (dim, runtime_check, dsl) else (
            True if all(x is True for x in (dim, runtime_check, dsl)) else None
        )
    else:
        arch = False
    return {
        "backend_requested_flashinfer_or_auto": requested,
        "platform_is_cuda": cuda,
        "supported_gpu_runtime_shape_and_dependencies": arch,
    }


def allreduce_determinism_checks(facts):
    """PR #24629: deterministic mode suppresses auto-enabled FI fusion."""
    det = require_equal(facts, "enable_deterministic_inference", False)
    enable = is_true(facts, "fusion_requested")
    # If fusion wasn't even requested, it is not selected. Otherwise the
    # deterministic-mode off-switch is authoritative for this historical PR.
    return {
        "fusion_requested": enable,
        "not_deterministic_inference": det,
    }


CHECKS = {
    "vllm_gdn_mtp_51674": mtp_decode_checks,
    "vllm_flashinfer_gdn_prefill_40717": prefill_checks,
    "sglang_flashinfer_allreduce_deterministic_24629": allreduce_determinism_checks,
}


def evaluate(mode, facts):
    if mode not in CHECKS:
        raise ValueError("Unknown mode; choose from: " + ", ".join(sorted(CHECKS)))
    if not isinstance(facts, dict):
        raise ValueError("facts must be an object")
    checks = CHECKS[mode](facts)
    failed = sorted(k for k, val in checks.items() if val is False)
    unknown = sorted(k for k, val in checks.items() if val is None)
    status = (
        "ruled_out_by_known_guard" if failed else
        "insufficient_metadata" if unknown else
        "documented_guards_satisfied_not_runtime_verified"
    )
    return {
        "mode": mode,
        "status": status,
        "checks": checks,
        "failed_guards": failed,
        "unknown_guards": unknown,
        "source": SOURCES[mode],
        "hardware_execution_or_speedup_verified": False,
        "note": "Source PR version only; a passing static guard does NOT prove binary availability, real dispatch, or speedup.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=sorted(CHECKS))
    parser.add_argument("--facts", type=Path, required=True, help="input JSON facts, no shell or execution")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        facts = json.loads(args.facts.read_text(encoding="utf-8"))
        result = evaluate(args.mode, facts)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    raw = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw, encoding="utf-8")
    else:
        print(raw, end="")


if __name__ == "__main__":
    main()
