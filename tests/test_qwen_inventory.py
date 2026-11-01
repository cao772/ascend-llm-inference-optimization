"""Offline tests: must not contact Hugging Face or download weights."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_script(script, *args):
    return subprocess.run(
        [sys.executable, str(ROOT / "tools" / script), *args],
        cwd=ROOT, text=True, capture_output=True,
    )


class QwenResearchTests(unittest.TestCase):
    def test_inventory_default_is_offline(self):
        proc = run_script("qwen_inventory.py")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        manifest = json.loads(proc.stdout)
        self.assertEqual(manifest["operation"], "offline_catalog_only")
        self.assertTrue(manifest["no_weights_downloaded_or_uploaded"])
        self.assertGreaterEqual(len(manifest["models"]), 6)
        self.assertTrue(all(not m["uploaded_to_drive"] for m in manifest["models"]))

    def test_inventory_subset(self):
        proc = run_script("qwen_inventory.py", "--only", "Qwen/Qwen3.6-27B")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        manifest = json.loads(proc.stdout)
        self.assertEqual([m["id"] for m in manifest["models"]], ["Qwen/Qwen3.6-27B"])

    def test_inventory_unknown_is_rejected(self):
        proc = run_script("qwen_inventory.py", "--only", "Unknown/Qwen")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Unknown model", proc.stderr)

    def test_snapshot_defaults_to_dry_run(self):
        proc = run_script("download_qwen_snapshot.py", "--model-id", "Qwen/Qwen3.5-35B-A3B")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        plan = json.loads(proc.stdout)
        self.assertEqual(plan["mode"], "dry_run")
        self.assertFalse(plan["include_weights"])
        self.assertFalse(plan["uploaded_to_drive"])

    def test_snapshot_rejects_non_catalog_repo(self):
        proc = run_script("download_qwen_snapshot.py", "--model-id", "random/unsafe")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Unknown model", proc.stderr)

    def test_snapshot_rejects_negative_budget(self):
        proc = run_script("download_qwen_snapshot.py", "--model-id", "Qwen/Qwen3-0.6B", "--max-gb", "-1")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--max-gb must be positive", proc.stderr)


if __name__ == "__main__":
    unittest.main()
