"""V2.2 source-scoped hardware facts, pinned release and architecture guardrails."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"design/ascend-explorer-v2"
def get(name):
    return json.loads((BASE/"content"/name).read_text("utf-8"))

class VerifiedProductAndStackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s=get("verified-product-specs-v2.2.json")
        cls.sw=get("software-compat-v2.2.json")
        cls.arch=get("architecture-paths-v2.2.json")
        cls.catalog=get("hardware-catalog.json")

    def test_product_figures_have_exact_scope(self):
        items={p["id"]:p for p in self.s["products"]}
        self.assertEqual(set(items),{"atlas-300i-duo","atlas-800i-a2"})
        duo={x["id"]:x for x in items["atlas-300i-duo"]["specs"]}
        self.assertEqual(duo["device-memory"]["values"],[48,96])
        self.assertEqual(duo["memory-bandwidth"]["value"],408)
        self.assertIn("整卡",duo["memory-bandwidth"]["scope"])
        self.assertEqual(duo["int8"]["unit"],"TOPS")
        self.assertEqual(duo["fp16"]["unit"],"TFLOPS")
        self.assertIn("可选",next(x for x in items["atlas-800i-a2"]["specs"] if x["id"]=="interconnect")["scope"])
        self.assertEqual(next(x for x in items["atlas-800i-a2"]["specs"] if x["id"]=="interconnect")["value"],392)

    def test_product_specs_are_official_and_not_mixed_into_general_catalog(self):
        ids={p["id"] for p in self.catalog["products"]}
        for p in self.s["products"]:
            self.assertIn(p["id"],ids)
            self.assertTrue(p["sourceUrl"].startswith("https://e.huawei.com/"))
            self.assertTrue(p["limitations"])
            for x in p["specs"]:
                self.assertTrue(x["scope"] and x["unit"])
                self.assertTrue(x.get("value",0)>=0)
        self.assertTrue(all(all(x is None for x in p["quantitative"].values()) for p in self.catalog["products"]))

    def test_release_is_one_co_validated_set(self):
        self.assertEqual(self.sw["release"],"vLLM-Ascend 0.30.0")
        components={x["layer"]:x for x in self.sw["components"]}
        for label,version in [("Ascend HDK（驱动/固件）","26.1.1"),("CANN Toolkit + Ops","9.2.0"),("NNAL","9.2.0"),
                              ("PyTorch","2.10.0"),("TorchNPU","2.10.0.post7"),("vLLM-Ascend","0.30.0")]:
            self.assertEqual(components[label]["version"],version)
        self.assertNotIn("300I DUO",components["Triton Ascend"]["appliesTo"])
        self.assertIn("300I DUO",components["Triton Ascend"]["notUsedOn"])

    def test_models_have_source_and_are_not_claimed_to_be_our_benchmarks(self):
        self.assertIn("supported_models.html",self.sw["modelExamples"]["sourceUrl"])
        names=[x["model"] for x in self.sw["modelExamples"]["rows"]]
        self.assertTrue(any(n.startswith("GLM") for n in names))
        self.assertTrue(any(n.startswith("DeepSeek") for n in names))
        self.assertTrue(any(n.startswith("Qwen") for n in names))
        for row in self.sw["modelExamples"]["rows"]:
            self.assertEqual(row["documentedHardware"],"A2/A3")
            self.assertIn("✅",row["documentedStatus"])
        self.assertTrue(any("不等于" in note for note in self.sw["caveats"]))

    def test_architecture_paths_are_aic_aiv_scoped_and_contain_debug_guidance(self):
        paths={p["id"]:p for p in self.arch["paths"]}
        self.assertEqual(set(paths),{"gemm","vector"})
        self.assertEqual(len(paths["gemm"]["steps"]),7)
        self.assertEqual(len(paths["vector"]["steps"]),5)
        self.assertIn("FixPipe",[x["name"] for x in paths["gemm"]["steps"]])
        self.assertIn("AIV",paths["vector"]["engine"])
        self.assertIn("AIC",paths["gemm"]["engine"])
        for path in paths.values():
            for step in path["steps"]:
                self.assertTrue(step["detail"] and step["verify"] and step["question"])
        self.assertIn("canncommercial",self.arch["sourceUrl"])

    def test_document_is_explicitly_not_hardware_measurement(self):
        joined=json.dumps({"s":self.s,"sw":self.sw,"arch":self.arch},ensure_ascii=False)
        self.assertIn("不能",joined)
        self.assertIn("非实测",joined)
        self.assertNotIn("本项目实测提升",joined)

if __name__=="__main__":
    unittest.main()
