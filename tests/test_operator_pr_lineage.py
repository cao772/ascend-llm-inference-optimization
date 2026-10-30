"""Ensure PR chain evidence is specific, linked and not advertised as real hardware measurements."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_operator_pr_lineage", ROOT / "tools" / "validate_operator_pr_lineage.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class PRLineageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(
            (ROOT / "research/source-traces/qwen-operator-pr-lineage-2026-10-30.json").read_text("utf-8")
        )

    def test_curated_records_are_validated(self):
        report = mod.summarize(self.dataset)
        self.assertEqual(report["verified_merged_pr_count_by_connector"], 12)
        self.assertEqual(report["project_measured_kernels"], 0)
        self.assertTrue(report["excluded_from_perf_ranking"])
        self.assertEqual(len(report["lifecycle_edges"]), 5)

    def test_ascend_removed_fusion_is_explicit(self):
        target = next(x for x in self.dataset["entries"] if x["id"] == "PR-ASC-12119")
        self.assertIn("Deletes", target["finding"])
        self.assertIn("allreduce", target["title"].lower())

    def test_qwen_merged_kernel_public_dispatch_mismatch_is_preserved(self):
        target = next(x for x in self.dataset["entries"] if x["id"] == "PR-VLLM-51674")
        self.assertIn("num_v_heads==8*num_k_heads", target["finding"])
        self.assertFalse(target["measured_by_us"])

    def test_lifecycle_relations_are_source_linked(self):
        report = mod.summarize(self.dataset)
        refs = {(x["from"], x["to"]) for x in report["lifecycle_edges"]}
        self.assertIn(("PR-FI-3001", "PR-FI-3155"), refs)
        self.assertIn(("PR-SGL-12787", "PR-SGL-20792"), refs)
        self.assertIn(("PR-SGL-22664", "PR-SGL-24629"), refs)

    def test_duplicate_id_rejected(self):
        x = dict(self.dataset)
        x["entries"] = [self.dataset["entries"][0]] * 2
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            mod.summarize(x)

    def test_invalid_commit_rejected(self):
        x = dict(self.dataset)
        edited = dict(self.dataset["entries"][0])
        edited["merge_commit"] = "madeup"
        x["entries"] = [edited] + self.dataset["entries"][1:]
        with self.assertRaisesRegex(ValueError, "Invalid merge"):
            mod.summarize(x)

    def test_edge_unknown_endpoint_rejected(self):
        x = dict(self.dataset)
        x["edges"] = [{"from":"PR-SGL-12787","to":"not-a-pr","relation":"reverted_by",
                       "source":"https://github.com/sgl-project/sglang/pull/12787"}]
        with self.assertRaisesRegex(ValueError, "unknown"):
            mod.summarize(x)


if __name__ == "__main__":
    unittest.main()
