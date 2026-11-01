"""External Ascend C evidence, no local NPU runtime or fabricated inferencing gains."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"design"/"ascend-explorer-v2"
sys.path.insert(0,str(BASE/"site"))
import build_site

class PublicMatmulEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e=json.loads((BASE/"content/public-matmul-evidence-2026-11-01.json").read_text("utf-8"))
    def test_reports_only_external_case_and_zero_local_measurement(self):
        e=self.e
        self.assertEqual(e["local_npu_profiling_count"],0)
        self.assertEqual(e["provenance_status"],"public_author_reported_not_independently_reproduced")
        self.assertFalse(e["validation_status"]["project_npu_reproduction"])
        self.assertFalse(e["validation_status"]["proof_of_llm_speedup"])
    def test_source_links_are_real_source_types_not_fake_local_files(self):
        e=self.e
        ids={s["id"] for s in e["sources"]}
        self.assertEqual(len(ids),len(e["sources"]))
        self.assertEqual(len(ids),5)
        self.assertEqual(e["case"]["source_id"],"SRC-ATLAS-A2-CASE")
        self.assertTrue(all(s["url"].startswith("https://") for s in e["sources"]))
        self.assertTrue(all(set(x["source_ids"]).issubset(ids) for x in e["evidence_chain"]))
        self.assertTrue(any(s["kind"]=="developer_preview_case" for s in e["sources"]))
    def test_operator_and_pipeline_times_never_mixed(self):
        c=self.e["case"]
        a,b,d=c["first_experiment"],c["second_experiment"],c["third_experiment"]
        self.assertEqual((c["matrix"]["M"],c["matrix"]["N"],c["matrix"]["K"]),(4096,5120,4096))
        self.assertEqual((a["before"],a["after"]),(12045,2532))
        self.assertEqual((b["before"],b["after"]),(2452,808))
        self.assertEqual((d["before"],d["after"]),(808,591))
        self.assertEqual(a["measured_metric"],"operator_execution_duration_us")
        self.assertEqual(b["measured_metric"],d["measured_metric"])
        self.assertNotEqual(a["measured_metric"],b["measured_metric"])
        self.assertIn("Do not sum",c["scope_warning"])
    def test_precise_tile_and_parallel_context(self):
        c=self.e["case"]
        a,b,d=c["first_experiment"],c["second_experiment"],c["third_experiment"]
        self.assertEqual((a["launcher_cube_cores_before"],a["launcher_cube_cores_after"]),(4,20))
        self.assertEqual((a["tiling_used_core_num_before"],a["tiling_used_core_num_after"]),(8,40))
        self.assertEqual((b["tile_before"]["baseM"],b["tile_after"]["baseM"]),(64,128))
        self.assertEqual((b["tile_before"]["baseN"],b["tile_after"]["baseN"]),(64,256))
        self.assertEqual((b["tile_before"]["baseK"],b["tile_after"]["baseK"]),(256,64))
        self.assertIn("CFG_MDL",d["code_mechanism"])
    def test_hardware_api_does_not_imply_a_fixed_l1_size(self):
        e=self.e
        s=next(s for s in e["sources"] if s["id"]=="SRC-CORE-MEM")
        self.assertIn("GetCoreMemSize",s["title"])
        self.assertIsNone(e["case"]["gpu_or_chip_exact_sku"])
        self.assertFalse(e["validation_status"]["full_raw_profile_available"])
    def test_bundled_site_preserves_evidence_tier(self):
        h=build_site.render()
        self.assertIn("reported-evidence-grid",h)
        self.assertIn("public_author_reported_not_independently_reproduced",h)
        self.assertIn("不能跨行累乘",h)
        self.assertNotIn('"project_npu_reproduction":true',h)
        self.assertIn("MTE2_pipeline_duration_us",h)
        self.assertNotIn("/* APP_JS_INJECT */",h)

if __name__=="__main__":
    unittest.main()
