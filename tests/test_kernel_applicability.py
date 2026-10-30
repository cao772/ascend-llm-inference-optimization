"""Static source-guard tests: no CUDA, HuggingFace, NPU or model loading."""
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_kernel_applicability", ROOT / "tools" / "check_kernel_applicability.py")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class GuardTests(unittest.TestCase):
    def test_public_qwen35_35b_layout_is_ruled_out_even_without_gpu_details(self):
        # 16 K heads / 32 V heads quoted by upstream PR #51674.
        x = mod.evaluate("vllm_gdn_mtp_51674", {"num_k_heads": 16, "num_v_heads": 32})
        self.assertEqual(x["status"], "ruled_out_by_known_guard")
        self.assertIn("num_v_heads_is_8_times_num_k_heads", x["failed_guards"])
        self.assertFalse(x["hardware_execution_or_speedup_verified"])

    def test_source_ratio_could_pass_but_runtime_still_unverified(self):
        x = mod.evaluate("vllm_gdn_mtp_51674", {
            "num_k_heads": 4, "num_v_heads": 32,
            "num_decodes": 0, "num_spec_decodes": 4,
            "has_spec_sequence_masks": True, "state_dtype": "bfloat16",
            "gdn_decode_kernel": "cuda", "state_indices_present": True,
            "state_indices_width": 4, "fused_op_built": True,
        })
        self.assertEqual(x["status"], "documented_guards_satisfied_not_runtime_verified")
        self.assertFalse(x["hardware_execution_or_speedup_verified"])

    def test_many_spec_tokens_are_ruled_out(self):
        x = mod.evaluate("vllm_gdn_mtp_51674", {
            "num_k_heads": 2, "num_v_heads": 16, "state_indices_width": 9
        })
        self.assertIn("spec_state_width_at_most_8", x["failed_guards"])

    def test_missing_metadata_is_unknown_not_support(self):
        x = mod.evaluate("vllm_gdn_mtp_51674", {})
        self.assertEqual(x["status"], "insufficient_metadata")
        self.assertGreater(len(x["unknown_guards"]), 1)

    def test_wrong_dtype_and_broken_op_are_rejected(self):
        x = mod.evaluate("vllm_gdn_mtp_51674", {
            "state_dtype": "float16", "fused_op_built": False
        })
        self.assertIn("recurrent_state_dtype_allowed", x["failed_guards"])
        self.assertIn("fused_op_built", x["failed_guards"])

    def test_flashinfer_prefill_cannot_run_on_ascend(self):
        x = mod.evaluate("vllm_flashinfer_gdn_prefill_40717", {
            "platform": "npu", "backend": "flashinfer", "cuda_sm_family": 0,
        })
        self.assertEqual(x["status"], "ruled_out_by_known_guard")

    def test_flashinfer_blackwell_requires_dim_128_cuda_13_and_dsl(self):
        x = mod.evaluate("vllm_flashinfer_gdn_prefill_40717", {
            "platform": "cuda", "backend": "auto", "cuda_sm_family": 100,
            "head_k_dim": 64, "cuda_runtime_major": 13, "cutlass_dsl_installed": True,
        })
        self.assertIn("supported_gpu_runtime_shape_and_dependencies", x["failed_guards"])

    def test_flashinfer_hopper_does_not_require_blackwell_dsl(self):
        x = mod.evaluate("vllm_flashinfer_gdn_prefill_40717", {
            "platform": "cuda", "backend": "flashinfer", "cuda_sm_family": 90,
        })
        self.assertEqual(x["status"], "documented_guards_satisfied_not_runtime_verified")

    def test_determinism_overrides_allreduce(self):
        x = mod.evaluate("sglang_flashinfer_allreduce_deterministic_24629", {
            "enable_deterministic_inference": True, "fusion_requested": True
        })
        self.assertEqual(x["status"], "ruled_out_by_known_guard")
        self.assertIn("not_deterministic_inference", x["failed_guards"])

    def test_no_fusion_request_is_not_accidentally_success(self):
        x = mod.evaluate("sglang_flashinfer_allreduce_deterministic_24629", {
            "enable_deterministic_inference": False, "fusion_requested": False
        })
        self.assertEqual(x["status"], "ruled_out_by_known_guard")

    def test_cli_uses_file_only(self):
        path = ROOT / "research" / "source-traces" / "qwen35-35b-layout-pr51674.json"
        done = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "check_kernel_applicability.py"),
             "--mode", "vllm_gdn_mtp_51674", "--facts", str(path)],
            text=True, capture_output=True, cwd=ROOT,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout)["status"], "ruled_out_by_known_guard")

    def test_bad_mode_rejected(self):
        with self.assertRaises(ValueError):
            mod.evaluate("fake_mode", {})


if __name__ == "__main__":
    unittest.main()
