"""Synthetic unit-test values; tests do not claim real NPU measurements."""
import json
import tempfile
import unittest
from pathlib import Path
from tools.compare_runs import compare, load_run


def fixture(tpot=10.0, *, provenance="measured", concurrency=1):
    return {"run_id": "unit-test", "provenance": provenance,
            "model_id": "test/model", "model_revision": "sha000",
            "hardware": {"device": "test", "cards": 1, "tp": 1, "dp": 1},
            "software": {"vllm": "test", "vllm_ascend": "test", "cann": "test"},
            "workload": {"dataset": "synthetic-test", "input_tokens": 1024,
                         "output_tokens": 512, "concurrency": concurrency, "sampling": "greedy"},
            "metrics": {"tpot_ms": tpot, "ttft_ms": 100, "throughput_tps": 10}}


class CompareTests(unittest.TestCase):
    def test_latency_throughput(self):
        a, b = fixture(), fixture(tpot=8)
        b["metrics"]["throughput_tps"] = 12
        out = compare(a, b)
        self.assertEqual(out["results"][0]["improvement_pct"], 20)
        self.assertEqual(out["results"][-1]["improvement_pct"], 20)

    def test_mismatch_and_explicit_override(self):
        a, b = fixture(), fixture(concurrency=4)
        with self.assertRaisesRegex(ValueError, "workload"):
            compare(a, b)
        self.assertIn("workload", compare(a, b, allow_mismatch=True)["mismatched_conditions"])

    def test_reported_not_measured(self):
        with self.assertRaisesRegex(ValueError, "non-measured"):
            compare(fixture(), fixture(provenance="reported"))
        self.assertEqual(compare(fixture(), fixture(provenance="reported"),
                                 include_nonmeasured=True)["provenance"][-1], "reported")

    def test_invalid_metric(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "invalid.json"
            obj = fixture()
            obj["metrics"]["tpot_ms"] = -1
            p.write_text(json.dumps(obj), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must be finite"):
                load_run(p)


if __name__ == "__main__":
    unittest.main()
