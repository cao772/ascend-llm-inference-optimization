"""Network-free tests of official Qwen model enumeration."""
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("discover_qwen_models", ROOT / "tools" / "discover_qwen_models.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class DiscoveryTests(unittest.TestCase):
    def test_classification_is_explicitly_heuristic(self):
        self.assertEqual(module.classify("Qwen/Qwen3-VL-8B")["category_guess"], "vision-language")
        self.assertEqual(module.classify("Qwen/Qwen3-Coder-Next")["category_guess"], "code")
        self.assertEqual(module.classify("Qwen/Qwen3-Embedding-0.6B")["category_guess"], "embedding")
        self.assertEqual(module.classify("Qwen/Qwen3.6-35B-A3B")["moe_name_hint"], True)
        self.assertEqual(module.classify("Qwen/Qwen3.8-27B")["family"], "Qwen3.8")

    def test_pagination_deduplicates_and_filters_non_qwen(self):
        first = "https://huggingface.co/api/models?author=Qwen&limit=100&full=true&after=abc"
        def fetch(url):
            if "after=abc" not in url:
                return ([{"id": "Qwen/Qwen3-0.6B", "sha": "abc",
                          "cardData": {"license": "apache-2.0"}},
                         {"id": "attacker/sneaky"}], first)
            return ([{"id": "Qwen/Qwen3-0.6B"},
                     {"id": "Qwen/Qwen3.6-27B", "gated": True}], None)
        result = module.collect(fetcher=fetch, max_pages=3)
        self.assertTrue(result["complete"])
        self.assertEqual(result["page_count"], 2)
        self.assertEqual(result["model_count"], 2)
        self.assertEqual(result["models"][0]["license_reported_by_hub"], "apache-2.0")
        self.assertTrue(result["models"][1]["gated"])
        self.assertFalse(result["weights_downloaded"])

    def test_page_limit_means_incomplete(self):
        def fetch(_):
            return ([{"id": "Qwen/Qwen3-0.6B"}],
                    "https://huggingface.co/api/models?author=Qwen&after=next")
        result = module.collect(fetcher=fetch, max_pages=1)
        self.assertFalse(result["complete"])
        self.assertTrue(result["truncated_by_max_pages"])

    def test_unsafe_host_rejected(self):
        with self.assertRaises(ValueError):
            module.validate_next_url("https://not-huggingface.example/api/models?author=Qwen")
        with self.assertRaises(ValueError):
            module.validate_next_url("https://huggingface.co/api/models?author=SomeoneElse")
        with self.assertRaises(ValueError):
            module.validate_next_url("http://huggingface.co/api/models?author=Qwen")

    def test_network_error_preserves_incomplete_status(self):
        def fail(_):
            raise OSError("offline")
        result = module.collect(fetcher=fail)
        self.assertEqual(result["page_count"], 0)
        self.assertFalse(result["complete"])
        self.assertIn("offline", result["error"])

    def test_cli_no_online_rejected(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "discover_qwen_models.py")],
            capture_output=True, text=True, cwd=ROOT,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("--online", completed.stderr)


if __name__ == "__main__":
    unittest.main()
