"""Ascend explainer design quality gates. No hardware or UI deployment."""
import copy
import importlib.util
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "design/ascend-explorer-v2"
SPEC = importlib.util.spec_from_file_location("ascend_design_validation", BASE / "tools/validate_design.py")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class AscendExplorerDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = mod.load_json(BASE / "content/hardware-catalog.json")
        cls.s = mod.load_json(BASE / "content/operator-stories.json")
        cls.m = mod.load_json(BASE / "content/modules.json")
        cls.design = (BASE / "DESIGN.md").read_text("utf-8")
        cls.ts = (BASE / "src/types.ts").read_text("utf-8")
        cls.css = (BASE / "src/tokens.css").read_text("utf-8")

    def check(self, c=None, s=None, m=None):
        return mod.check_design(c if c is not None else self.c,
                                s if s is not None else self.s,
                                m if m is not None else self.m,
                                self.design, self.ts, self.css)

    def test_design_review_preview_has_keyboard_interactions(self):
        preview = (BASE / "preview.html").read_text("utf-8")
        for target in ("id=\"hardware-tabs\"", "id=\"compute\"", "id=\"op-tabs\"",
                       "id=\"steps\"", "id=\"detail\""):
            self.assertIn(target.replace("\\\"", "\""), preview)
        self.assertIn("aria-pressed", preview)
        self.assertIn("prefers-reduced-motion", preview)
        self.assertIn("设计交互预览", preview)
        self.assertNotIn("fetch(", preview)
        self.assertNotIn("真实提速 2 倍", preview)

    def test_design_preview_not_marked_as_live_benchmark(self):
        preview = (BASE / "preview.html").read_text("utf-8")
        self.assertIn("非真实", preview) if "非真实" in preview else self.assertIn("非实机", preview)
        self.assertIn("没有硬件规格和真实推理测量", preview)

    def test_published_design_data_passes(self):
        result = self.check()
        self.assertEqual(result["design_status"], "review_candidate_not_implemented")
        self.assertEqual(result["products_officially_categorized"], 10)
        self.assertEqual(result["processor_topics_not_merged_with_cards"], 2)
        self.assertEqual(result["operator_stories"], 7)
        self.assertEqual(result["operator_frames"], 42)
        self.assertEqual(result["design_modules"], 9)
        self.assertFalse(result["observed_npu_performance"])

    def test_product_and_chip_are_different_types(self):
        self.assertTrue(all("form" in p for p in self.c["products"]))
        self.assertTrue(all(x["notAPhysicalCard"] for x in self.c["processorResearchTopics"]))
        self.assertTrue(all(all(v is None for v in p["quantitative"].values())
                            for p in self.c["products"]))

    def test_unknown_numeric_without_official_field_proof_rejected(self):
        c = copy.deepcopy(self.c)
        c["products"][0]["quantitative"]["powerW"] = 100
        with self.assertRaisesRegex(ValueError, "field-level evidence"):
            self.check(c=c)

    def test_unofficial_product_spec_rejected(self):
        c = copy.deepcopy(self.c)
        c["products"][0]["sourceUrl"] = "https://example.com/some-product"
        with self.assertRaisesRegex(ValueError, "official"):
            self.check(c=c)

    def test_fake_software_test_not_permitted_as_npu_result(self):
        m = copy.deepcopy(self.m)
        m["scope"]["hasNPUResults"] = True
        with self.assertRaisesRegex(ValueError, "invent"):
            self.check(m=m)

    def test_missing_story_frame_rejected(self):
        s = copy.deepcopy(self.s)
        s["stories"][0]["frames"].pop(3)
        with self.assertRaisesRegex(ValueError, "six"):
            self.check(s=s)

    def test_missing_negative_case_rejected(self):
        s = copy.deepcopy(self.s)
        s["stories"][1]["limitations"] = []
        with self.assertRaisesRegex(ValueError, "limited"):
            self.check(s=s)

    def test_duplicate_module_anchors_rejected(self):
        m = copy.deepcopy(self.m)
        m["modules"][1]["hash"] = m["modules"][0]["hash"]
        with self.assertRaisesRegex(ValueError, "Duplicate module"):
            self.check(m=m)

    def test_no_false_implementation_status(self):
        m = copy.deepcopy(self.m)
        m["modules"][0]["implementationStatus"] = "verified"
        with self.assertRaisesRegex(ValueError, "cannot claim"):
            self.check(m=m)

    def test_no_fake_operator_observation(self):
        s = copy.deepcopy(self.s)
        s["stories"][2]["frames"][0]["observed"] = True
        with self.assertRaisesRegex(ValueError, "hardware"):
            self.check(s=s)


if __name__ == "__main__":
    unittest.main()
