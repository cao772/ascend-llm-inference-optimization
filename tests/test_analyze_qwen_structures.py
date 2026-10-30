"""Offline Qwen official-structure comparison and historical fused GDN guard tests."""
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("analyze_qwen_structures", ROOT / "tools/analyze_qwen_structures.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class QwenStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = json.loads(module.MATRIX.read_text("utf-8"))
        cls.by_id = {m["id"]: m for m in cls.matrix["models"]}

    def test_curated_matrix_is_consistent(self):
        r = module.validate_matrix(self.matrix)
        self.assertEqual(r["model_count"], 5)
        self.assertTrue(r["all_real_hardware_speedups_unknown"])

    def test_all_five_have_incompatible_head_ratio_for_pr51674(self):
        r = module.validate_matrix(self.matrix)
        self.assertTrue(all(not m["pr51674_shape_guard_satisfied"] for m in r["cases"]))
        self.assertEqual(set(m["gdn_ratio"] for m in r["cases"]), {2, 3, 4})

    def test_dense_qwen36_has_linear_attention_layers(self):
        q = self.by_id["Qwen/Qwen3.6-27B"]
        self.assertFalse(q["moe"])
        self.assertEqual(q["linear_attention_layers"], 48)
        self.assertEqual(q["full_attention_layers"], 16)
        self.assertEqual(q["linear_num_value_heads"] // q["linear_num_key_heads"], 3)

    def test_moe_variants_have_distinct_routing_topology(self):
        a = self.by_id["Qwen/Qwen3.5-35B-A3B"]
        b = self.by_id["Qwen/Qwen3.5-397B-A17B"]
        self.assertEqual([a["num_experts"], a["num_experts_per_tok"]], [256, 8])
        self.assertEqual([b["num_experts"], b["num_experts_per_tok"]], [512, 10])

    def test_next_does_not_invent_layer_type_counts(self):
        q = self.by_id["Qwen/Qwen3-Next-80B-A3B-Instruct"]
        self.assertFalse(q["layer_types_explicit"])
        self.assertIsNone(q["linear_attention_layers"])
        self.assertIsNone(q["mtp_num_hidden_layers"])
        self.assertEqual(q["full_attention_interval"], 4)

    def test_from_config_moe_and_layer_types(self):
        raw = {
            "architectures": ["Qwen3_5MoeForConditionalGeneration"],
            "text_config": {
                "model_type": "qwen3_5_moe_text", "num_hidden_layers": 4,
                "layer_types": ["linear_attention"] * 3 + ["full_attention"],
                "linear_num_key_heads": 16, "linear_num_value_heads": 32,
                "num_experts": 256, "num_experts_per_tok": 8, "dtype": "bfloat16"
            },
        }
        out = module.from_config(raw, "Qwen/Test", "unit_test_synthetic")
        self.assertEqual(out["linear_attention_layers"], 3)
        self.assertTrue(out["moe"])
        self.assertEqual(out["pr51674_head_ratio_check"], "ruled_out_by_known_head_ratio")
        self.assertFalse(out["runtime_dispatch_verified"])

    def test_from_config_shape_only_cannot_claim_runtime(self):
        out = module.from_config({
            "linear_num_key_heads": 4, "linear_num_value_heads": 32
        }, "Qwen/Test8x", "unit_test_synthetic")
        self.assertEqual(out["pr51674_head_ratio_check"], "head_ratio_satisfied_not_runtime_verified")
        self.assertFalse(out["performance_verified_by_project"])

    def test_missing_linear_head_fields_are_unknown(self):
        out = module.from_config({"num_hidden_layers": 4}, "Other/Test")
        self.assertEqual(out["pr51674_head_ratio_check"], "unknown_insufficient_head_metadata")

    def test_dont_accept_invented_explicit_layer_counts(self):
        m = dict(self.by_id["Qwen/Qwen3-Next-80B-A3B-Instruct"])
        m["linear_attention_layers"] = 36
        changed = dict(self.matrix, models=[m])
        with self.assertRaisesRegex(ValueError, "explicit"):
            module.validate_matrix(changed)

    def test_reject_mismatched_layer_list(self):
        with self.assertRaisesRegex(ValueError, "length"):
            module.from_config({
                "num_hidden_layers": 2, "layer_types": ["linear_attention"]
            }, "Qwen/Synthetic")

    def test_cli_matrix_is_network_free(self):
        r = subprocess.run([sys.executable, str(ROOT / "tools/analyze_qwen_structures.py"),
                            "--matrix"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["model_count"], 5)


if __name__ == "__main__":
    unittest.main()
