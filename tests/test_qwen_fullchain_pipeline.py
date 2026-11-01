"""Offline evidence → model features → hypothesis → validation → decision tests."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_qwen_decision_pipeline as pipe  # noqa: E402
import render_qwen_decision_dashboard as htmlgen  # noqa: E402


class QwenFullchainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = pipe._load(pipe.RULES)
        cls.models = pipe._load(pipe.MATRIX)
        cls.cases = pipe._load(pipe.CASES_PATH)
        cls.prs = pipe._load(pipe.PRS_PATH)
        cls.failures = pipe._load(pipe.FAILURES_PATH)
        cls.report = pipe.decide(cls.rules, cls.models, cls.cases, cls.prs, cls.failures)
        cls.scenarios = {x["id"]: x for x in cls.report["scenarios"]}

    def test_source_counts_and_empty_performance(self):
        r = self.report
        self.assertEqual(r["source_counts"], {
            "external_case_records": 15, "official_model_structures": 5,
            "upstream_pr_records": 12, "failure_or_limit_records": 8,
        })
        self.assertEqual(r["scenario_count"], 5)
        self.assertEqual(r["hypotheses_total"], 10)
        self.assertEqual(r["real_hardware_measurements"], 0)
        self.assertFalse(r["deployment_available"])
        self.assertTrue(all(s["measurement_status"] == "not_measured" for s in r["scenarios"]))
        self.assertTrue(all(all(v is None for v in s["observed_results"].values()) for s in r["scenarios"]))

    def test_pipeline_has_six_gates(self):
        self.assertEqual(len(self.report["pipeline"]), 6)
        self.assertEqual(self.report["pipeline"][0]["name"], "证据接入")
        self.assertEqual(self.report["pipeline"][-1]["name"], "裁决和经验回写")

    def test_dense_model_branches_to_sp_not_moe(self):
        s = self.scenarios["ASCEND36-PREFILL"]
        ids = {h["id"] for h in s["priority_actions"]}
        self.assertIn("H-05", ids)
        self.assertIn("H-03", ids)
        self.assertNotIn("H-04", ids)
        self.assertEqual(s["static_model_facts"]["linear_attention_layers_explicit"], 48)
        self.assertFalse(s["static_model_facts"]["moe"])

    def test_moe_model_branches_to_moe_not_dense_sp(self):
        s = self.scenarios["ASCEND35-C1"]
        ids = {h["id"] for h in s["priority_actions"]}
        self.assertIn("H-04", ids)
        self.assertNotIn("H-05", ids)
        self.assertTrue(s["static_model_facts"]["moe"])
        self.assertEqual(s["static_model_facts"]["num_experts"], 256)

    def test_mixed_c8_retains_decode_and_prefill_research(self):
        s = self.scenarios["ASCEND35-C8"]
        ids = {h["id"] for h in s["priority_actions"]}
        self.assertIn("H-02", ids)
        self.assertIn("H-06", ids)
        self.assertGreater(s["candidate_count"], 1)

    def test_static_head_guard_exclusions_apply_to_decode_stage_only(self):
        for s in self.report["scenarios"]:
            self.assertFalse(s["static_model_facts"]["pr51674_8to1_shape_guard_satisfied"])
            matching = [x for x in s["priority_actions"] if x["id"] == "H-08"]
            if s["stage"] in {"decode", "mixed"}:
                self.assertEqual(len(matching), 1)
                h = matching[0]
                self.assertEqual(h["priority"], "BLOCK")
                self.assertIsNone(h["speedup_pct"])
                self.assertFalse(h["hardware_benchmark_observed"])
            else:
                self.assertEqual(matching, [])
                self.assertIn("H-08", s["not_applicable_hypotheses"])

    def test_old_ascend_path_blocked_cuda_reference_not_blocked(self):
        for name in ("ASCEND35-C1", "ASCEND35-C8", "ASCEND36-PREFILL", "ASCEND36-DECODE"):
            ids = {h["id"] for h in self.scenarios[name]["priority_actions"]}
            self.assertIn("H-07", ids)
        b = self.scenarios["B200397-REF"]
        ids = {h["id"] for h in b["priority_actions"]}
        self.assertNotIn("H-07", ids)
        self.assertNotIn("H-02", ids)
        self.assertNotIn("H-04", ids)

    def test_all_pr_and_failure_urls_are_backed_by_curated_data(self):
        for s in self.report["scenarios"]:
            for h in s["priority_actions"]:
                self.assertTrue(h["evidence"])
                self.assertTrue(all(x.startswith("https://") for x in h["evidence"]))
                self.assertEqual(len(h["related_pr_urls"]), len(h["related_pr_ids"]))
                self.assertTrue(all(u.startswith("https://") for u in h["related_pr_urls"]))
                self.assertTrue(all(x["sources"] for x in h["related_failure_sources"]))

    def test_source_based_priority_is_not_predicted_gain(self):
        for s in self.report["scenarios"]:
            self.assertFalse(s["compatibility_confirmed"])
            self.assertTrue(s["hypothetical_configuration"])
            for h in s["priority_actions"]:
                self.assertIn(h["decision"], {
                    "exclude_specific_legacy_or_shape_incompatible_path",
                    "must_validate_or_measure_first", "conditional_experiment_candidate",
                    "conditional_later_research",
                })
                self.assertIn("speedup_pct", h)
                self.assertIsNone(h["speedup_pct"])

    def test_reject_fake_measurement_in_research_spec(self):
        r = copy.deepcopy(self.rules)
        r["benchmark_observations"] = [{"TPOT_ms": 5}]
        with self.assertRaisesRegex(ValueError, "No environment"):
            pipe.decide(r, self.models, self.cases, self.prs, self.failures)

    def test_reject_unknown_source_pr(self):
        r = copy.deepcopy(self.rules)
        r["hypotheses"][0]["related_pr_ids"] = ["PR-FAKE-1"]
        with self.assertRaisesRegex(ValueError, "non-curated"):
            pipe.decide(r, self.models, self.cases, self.prs, self.failures)

    def test_escaped_html_and_export(self):
        h = htmlgen.render(self.report)
        self.assertIn("<!doctype html>", h)
        self.assertIn("Qwen 推理优化", h)
        self.assertIn('id="research-data"', h)
        self.assertIn("__PAYLOAD__", htmlgen.HTML)
        self.assertNotIn("__PAYLOAD__", h)
        self.assertIn("待实测", h)
        self.assertIn("application/json", h)
        self.assertIn('id="fraction"', h)
        self.assertIn('id="kernelGain"', h)
        self.assertIn("理想端到端上界（非实测）", h)
        self.assertIn("function updateWhatIf()", h)
        self.assertIn("不包含我方 NPU/GPU 性能数据", h)

    def test_renderer_refuses_nonnull_measured_values(self):
        report = copy.deepcopy(self.report)
        report["scenarios"][0]["observed_results"]["TPOT_p50_ms"] = 5.0
        with self.assertRaisesRegex(ValueError, "Refuse"):
            htmlgen.render(report)

    def test_cli_generates_json_and_single_html_without_network(self):
        with tempfile.TemporaryDirectory() as d:
            p1 = Path(d) / "fullchain.json"
            p2 = Path(d) / "dashboard.html"
            a = subprocess.run([sys.executable, str(ROOT / "tools/build_qwen_decision_pipeline.py"),
                                "--output", str(p1)], cwd=ROOT, capture_output=True, text=True)
            b = subprocess.run([sys.executable, str(ROOT / "tools/render_qwen_decision_dashboard.py"),
                                "--output", str(p2)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(a.returncode, 0, a.stderr)
            self.assertEqual(b.returncode, 0, b.stderr)
            self.assertEqual(json.loads(p1.read_text("utf-8"))["scenario_count"], 5)
            html = p2.read_text("utf-8")
            self.assertGreater(len(html), 22000)
            self.assertIn("ASCEND36-PREFILL", html)


if __name__ == "__main__":
    unittest.main()
