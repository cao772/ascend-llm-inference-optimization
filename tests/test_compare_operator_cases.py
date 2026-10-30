"""Offline regression tests for evidence-aware cross-case analysis."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("compare_operator_cases", ROOT / "tools" / "compare_operator_cases.py")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class CaseComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads((ROOT / "research/cases/qwen-optimization-cases-2026-10-30.json").read_text("utf-8"))

    def test_catalog_has_citations_and_no_local_measurements(self):
        cases = mod.validate(self.raw)
        self.assertEqual(len(cases), 15)
        self.assertTrue(self.raw["no_local_benchmark"])
        self.assertTrue(all(c["source_urls"] for c in cases))

    def test_proposal_excluded_by_default(self):
        report = mod.compare(self.raw, min_shared=1)
        self.assertEqual(report["included_cases"], 9)
        self.assertTrue(all(all(k not in (x["a"], x["b"]) for k in ("QINF-009", "QINF-013", "QINF-014", "QINF-015")) for x in report["pairs"]))
        self.assertFalse(report["include_proposals"])

    def test_can_explicitly_include_proposals_but_never_compare_performance(self):
        report = mod.compare(self.raw, min_shared=1, include_proposals=True)
        self.assertEqual(report["included_cases"], 15)
        self.assertTrue(all(not x["performance_comparison_allowed"] for x in report["pairs"]))

    def test_common_patterns_are_counted_once_per_case(self):
        report = mod.compare(self.raw)
        self.assertEqual(report["frequencies"]["fusion"], 5)
        self.assertGreaterEqual(report["frequencies"]["memory_traffic"], 9)

    def test_controlled_acceptance_is_not_natural_traffic(self):
        trial = next(c for c in self.raw["cases"] if c["id"] == "QINF-010")
        self.assertIn("controlled", trial["evidence_status"])
        self.assertIn("2.3", trial["workload"])
        self.assertTrue(self.raw["no_local_benchmark"])

    def test_method_only_is_unmeasured(self):
        self.assertIn("open_source_method_no_benchmark", mod.UNMEASURED)
        report = mod.compare(self.raw)
        self.assertEqual(report["evidence_status_counts"]["open_source_method_no_benchmark"], 2)

    def test_duplicate_ids_rejected(self):
        small = dict(self.raw)
        small["cases"] = [self.raw["cases"][0], self.raw["cases"][0]]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            mod.validate(small)

    def test_measured_metric_cannot_attach_to_proposal(self):
        small = dict(self.raw)
        proposed = dict(self.raw["cases"][-1])
        proposed["outcome"] = "fake 99% gain"
        small["cases"] = [proposed]
        with self.assertRaisesRegex(ValueError, "unmeasured"):
            mod.validate(small)

    def test_unregistered_mechanism_rejected(self):
        small = dict(self.raw)
        case = dict(self.raw["cases"][0])
        case["mechanisms"] = ["invented"]
        small["cases"] = [case]
        with self.assertRaisesRegex(ValueError, "unknown"):
            mod.validate(small)

    def test_reject_nonpositive_threshold(self):
        with self.assertRaises(ValueError):
            mod.compare(self.raw, min_shared=0)


if __name__ == "__main__":
    unittest.main()
