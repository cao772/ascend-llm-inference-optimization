"""Graph export remains a provenance graph, never a measured speedup predictor."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_case_graph as graph_module  # noqa: E402


class GraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(
            (ROOT / "research/cases/qwen-optimization-cases-2026-10-30.json").read_text("utf-8")
        )

    def test_graph_counts_and_provenance(self):
        graph = graph_module.build(self.payload)
        self.assertEqual(graph["counts"]["case_count"], 15)
        self.assertEqual(graph["counts"]["nodes_by_kind"]["case"], 15)
        self.assertEqual(graph["project_hardware_benchmarks"], 0)
        self.assertTrue(all("relation" in e for e in graph["edges"]))

    def test_no_unvalidated_speedup_claim_in_edges(self):
        graph = graph_module.build(self.payload)
        pairs = [e for e in graph["edges"] if e["relation"] == "shares_tags"]
        self.assertTrue(pairs)
        self.assertTrue(all(e["performance_comparison_allowed"] is False for e in pairs))
        self.assertTrue(all(e["code_portability_verified"] is False for e in pairs))

    def test_source_per_case(self):
        graph = graph_module.build(self.payload)
        cases = [n for n in graph["nodes"] if n["kind"] == "case"]
        self.assertTrue(all(n["sources"] for n in cases))
        self.assertTrue(all(n["measured_by_our_project"] is False for n in cases))
        self.assertFalse(next(n for n in cases if n["id"] == "case:QINF-014")["externally_reported_metric"])

    def test_determinism(self):
        x = graph_module.build(self.payload)
        self.assertEqual(x, graph_module.build(self.payload))

    def test_cli_smoke_no_network(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "tools/build_case_graph.py"), "--min-shared", "3"],
            text=True, capture_output=True, cwd=ROOT,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["counts"]["case_count"], 15)


if __name__ == "__main__":
    unittest.main()
