"""Real V2 website build/source-integrity smoke tests. Does not claim NPU performance."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "design/ascend-explorer-v2/site"
sys.path.insert(0, str(HERE))
import build_site


class ParseIds(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
        self.buttons = []
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if "id" in d:
            self.ids.append(d["id"])
        if tag == "a":
            self.links.append(d.get("href", ""))
        if tag == "button":
            self.buttons.append(d)


class AscendExplorerSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = build_site.build_payload()
        cls.html = build_site.render()
        cls.parser = ParseIds()
        cls.parser.feed(cls.html)

    def test_all_nine_sections_present(self):
        required = ["overview", "hardware", "anatomy", "stack", "lifecycle",
                    "factors", "operators", "optimization", "evidence"]
        self.assertTrue(all(x in self.parser.ids for x in required))
        self.assertEqual(len(self.parser.ids), len(set(self.parser.ids)))
        self.assertTrue(all("#" + x in self.parser.links for x in required[1:]))

    def test_integrity_of_existing_sources(self):
        p = self.payload
        self.assertEqual(len(p["hardware"]["products"]), 10)
        self.assertEqual(len(p["hardware"]["processorResearchTopics"]), 2)
        self.assertEqual(len(p["operators"]["stories"]), 7)
        self.assertEqual(sum(len(x["frames"]) for x in p["operators"]["stories"]), 42)
        self.assertEqual(len(p["cases"]["cases"]), 15)
        self.assertEqual(len(p["prs"]["entries"]), 12)
        self.assertEqual(len(p["failures"]["failures"]), 8)
        self.assertEqual(p["atlas"]["counts"]["nodes"], 75)
        self.assertEqual(p["atlas"]["counts"]["edges"], 202)
        self.assertEqual(p["atlas"]["project_hardware_measurements"], 0)

    def test_hardware_specs_are_unknown_not_fake_numbers(self):
        for product in self.payload["hardware"]["products"]:
            self.assertTrue(all(value is None for value in product["quantitative"].values()))
            self.assertEqual(product["compatibilityStatus"], "not_assessed")
        self.assertTrue(all(x["notAPhysicalCard"] for x in self.payload["hardware"]["processorResearchTopics"]))

    def test_self_contained_build_no_remote_assets(self):
        h = self.html
        self.assertGreater(len(h), 120_000)
        self.assertNotIn("/* APP_", h)
        self.assertNotIn("<script src=", h)
        self.assertNotIn("<link rel=\"stylesheet\"", h)
        self.assertNotIn("@import url(", h)
        self.assertIn('id="app-data" type="application/json"', h)
        self.assertIn("real_hardware_measurements", h) if "real_hardware_measurements" in h else self.assertIn("project_hardware_measurements", h)
        self.assertIn("本项目尚无昇腾 NPU 实际性能数据", h)

    def test_embedded_json_parses_and_is_safe(self):
        match = re.search(r'<script id="app-data" type="application/json">(.*?)</script>', self.html, re.S)
        self.assertIsNotNone(match)
        p = json.loads(match.group(1))
        self.assertEqual(p["mode"], "educational_demo_not_npu_benchmark")
        self.assertEqual(p["atlas"]["counts"]["edges"], 202)
        self.assertNotIn("</script", match.group(1).lower())

    def test_no_external_perf_as_project_result(self):
        self.assertIn("非本项目实测", self.html)
        self.assertIn("条件性", self.html)
        self.assertIn("未核验", self.html)
        self.assertIn("Profiler", self.html)

    def test_buttons_and_key_interactions_exist(self):
        for key in ("product-tabs", "chip-units", "anatomy-levels", "operator-tabs",
                    "operator-steps", "timeline-stages", "factor-tabs", "case-grid",
                    "symptoms", "drawer-close", "drawer-backdrop", "nav-toggle"):
            self.assertIn(key, self.parser.ids)
        self.assertIn("aria-pressed", self.html)
        self.assertIn("prefers-reduced-motion", self.html)
        self.assertIn("Escape", self.html)
        self.assertIn("aria-modal", self.html)

    def test_offline_build_to_output(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "ascend-explorer-v2.html"
            r = subprocess.run([sys.executable, str(HERE / "build_site.py"),
                                "--output", str(out)], text=True, capture_output=True, cwd=ROOT)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 120_000)
            self.assertIn("算子显微镜", out.read_text(encoding="utf-8"))

    @unittest.skipUnless(shutil.which("node"), "Node runtime not installed")
    def test_javascript_is_syntax_valid(self):
        r = subprocess.run([shutil.which("node"), "--check", str(HERE / "app.js")],
                           text=True, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_no_mock_runtime_metrics(self):
        assert not self.payload.get("measurement_results")
        self.assertIn("轨道尺寸只表达概念", (HERE / "app.js").read_text(encoding="utf-8"))
        self.assertIn("未核验", (HERE / "app.js").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
