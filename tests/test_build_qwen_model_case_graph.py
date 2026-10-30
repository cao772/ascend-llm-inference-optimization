"""Network-free checks of model/case graph provenance and non-portability."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_qwen_model_case_graph as mod  # noqa: E402


class ModelCaseGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(mod.CASES_PATH.read_text("utf-8"))
        cls.matrix = json.loads(mod.MATRIX.read_text("utf-8"))
        cls.links = json.loads(mod.LINKS.read_text("utf-8"))

    def test_five_source_reviewed_links(self):
        g = mod.make_graph(self.cases, self.matrix, self.links)
        self.assertEqual((g["model_count"], g["case_count"], g["case_model_links"]), (5, 15, 5))
        self.assertTrue(g["no_local_measurement"])
        bridges = [e for e in g["edges"] if e["relation"].startswith("case_mentions") or
                   e["relation"] == "case_uses_quantized_derivative"]
        self.assertEqual(len(bridges), 5)
        self.assertTrue(all(e["runtime_dispatch_verified"] is False for e in bridges))

    def test_moe_and_gdn_different_dimensions(self):
        g = mod.make_graph(self.cases, self.matrix, self.links)
        m = next(n for n in g["nodes"] if n["id"] == "model:Qwen/Qwen3.6-27B")
        self.assertFalse(m["moe"])
        self.assertEqual(m["gdn_head_ratio"], 3)
        self.assertFalse(m["pr51674_head_ratio_satisfied"])
        edges = [e for e in g["edges"] if e["source"] == m["id"] and
                 e["relation"] == "config_declares_architecture_feature"]
        self.assertIn("feature:linear_attention", [e["target"] for e in edges])
        self.assertNotIn("feature:moe", [e["target"] for e in edges])

    def test_quantized_variant_is_not_identical_weights(self):
        g = mod.make_graph(self.cases, self.matrix, self.links)
        e = next(e for e in g["edges"] if e["source"] == "case:QINF-004" and
                 e["target"] == "model:Qwen/Qwen3.5-397B-A17B")
        self.assertEqual(e["relation"], "case_uses_quantized_derivative")
        self.assertTrue(e["model_structure_not_performance_equivalence"])

    def test_do_not_fuzzy_map_similar_qwen_model_names(self):
        g = mod.make_graph(self.cases, self.matrix, self.links)
        e = [x for x in g["edges"] if x["source"] == "case:QINF-002" and
             x["target"].startswith("model:")]
        self.assertEqual(e, [])

    def test_unknown_model_fails(self):
        x = {"links": [dict(self.links["links"][0], model_id="Qwen/Unknown")]}
        with self.assertRaisesRegex(ValueError, "missing"):
            mod.make_graph(self.cases, self.matrix, x)

    def test_bad_source_fails(self):
        x = {"links": [dict(self.links["links"][0], source="http://untrusted")]}
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            mod.make_graph(self.cases, self.matrix, x)

    def test_cli(self):
        r = subprocess.run([sys.executable, str(ROOT / "tools/build_qwen_model_case_graph.py")],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["model_count"], 5)


if __name__ == "__main__":
    unittest.main()
