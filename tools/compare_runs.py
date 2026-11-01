"""Compare user-recorded LLM inference runs (stdlib only, no device access)."""
import argparse
import json
import math
from pathlib import Path

LOWER_IS_BETTER = ("tpot_ms", "ttft_ms", "e2e_ms", "tpot_p95_ms", "ttft_p95_ms", "e2e_p95_ms")
HIGHER_IS_BETTER = ("throughput_tps", "request_throughput_rps")
CONTROLLED = ("model_id", "model_revision", "hardware", "workload")


def load_run(path):
    run = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(run, dict):
        raise ValueError(f"{path}: expected JSON object")
    for field in ("run_id", "provenance", "model_id", "model_revision", "hardware", "software", "workload", "metrics"):
        if field not in run:
            raise ValueError(f"{path}: missing '{field}'")
    if run["provenance"] not in ("measured", "reported", "synthetic"):
        raise ValueError(f"{path}: unsupported provenance")
    for key, value in run["metrics"].items():
        if key not in LOWER_IS_BETTER + HIGHER_IS_BETTER:
            raise ValueError(f"{path}: unknown metric {key}")
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{path}: {key} must be finite and > 0")
    if "tpot_ms" not in run["metrics"]:
        raise ValueError(f"{path}: missing metrics.tpot_ms")
    return run


def compare(base, candidate, *, allow_mismatch=False, include_nonmeasured=False):
    mismatches = [key for key in CONTROLLED if base[key] != candidate[key]]
    if mismatches and not allow_mismatch:
        raise ValueError("controlled conditions differ: " + ", ".join(mismatches))
    if not include_nonmeasured and (base["provenance"] != "measured" or candidate["provenance"] != "measured"):
        raise ValueError("non-measured data requires --include-nonmeasured")
    rows = []
    for key in LOWER_IS_BETTER + HIGHER_IS_BETTER:
        if key not in base["metrics"] or key not in candidate["metrics"]:
            continue
        a, b = base["metrics"][key], candidate["metrics"][key]
        improvement = ((a - b) / a * 100) if key in LOWER_IS_BETTER else ((b - a) / a * 100)
        rows.append({"metric": key, "baseline": a, "candidate": b, "improvement_pct": round(improvement, 2)})
    return {"baseline_run": base["run_id"], "candidate_run": candidate["run_id"],
            "provenance": [base["provenance"], candidate["provenance"]],
            "mismatched_conditions": mismatches, "software_baseline": base["software"],
            "software_candidate": candidate["software"], "results": rows,
            "warning": ("Not a controlled A/B comparison: conditions differ" if mismatches else None)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--allow-mismatch", action="store_true",
                        help="permit differences but include a warning")
    parser.add_argument("--include-nonmeasured", action="store_true",
                        help="permit reported/synthetic results, not device validation")
    args = parser.parse_args()
    try:
        result = compare(load_run(args.baseline), load_run(args.candidate),
                         allow_mismatch=args.allow_mismatch,
                         include_nonmeasured=args.include_nonmeasured)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
