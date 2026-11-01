"""Evidence V2.5: source/metric integrity and explicitly separated experiments."""
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "design/ascend-explorer-v2"
data = json.loads((HERE/"content/experiment-evidence-v2.5.json").read_text("utf-8"))

class ExperimentalEvidenceV25(unittest.TestCase):
    def test_provenance_and_coverage(self):
        self.assertEqual(data["schema_version"], "2.5.0")
        self.assertEqual(data["project_own_hardware_measurements"], 0)
        cases=data["case_records"]
        self.assertEqual(len(cases), 8)
        self.assertEqual(sum(r["source_kind"]=="vendor_developer_preview" for r in cases), 6)
        self.assertEqual(sum(r["source_kind"]=="github_issue_report" for r in cases), 2)
        self.assertEqual(len(data["documentation_examples"]), 1)
        self.assertEqual(len(set(x["id"] for x in cases)), len(cases))
    def test_measurement_pairs_and_scope(self):
        pairs=0
        for c in data["case_records"]:
            self.assertTrue(c["source_url"].startswith("https://"))
            self.assertTrue(c["hardware"] and c["change"] and c["constraints"])
            self.assertTrue(c["workload"] and c["metrics"])
            for m in c["metrics"]:
                self.assertTrue(m["scope"] and m["label"] and m["unit"])
                self.assertIn(m["direction"], ["lower","higher"])
                if m["before"] is not None and m["after"] is not None:
                    pairs+=1
                    self.assertGreaterEqual(m["before"],0)
                    self.assertGreaterEqual(m["after"],0)
                if c["source_kind"]=="github_issue_report":
                    self.assertFalse(m["comparable"],"Two cache rounds are NOT isolated A/B")
                else:
                    self.assertTrue(m["comparable"])
        self.assertEqual(pairs,24)
        self.assertEqual(data["collection"]["metric_pairs"],pairs)
    def test_operator_metrics_are_not_conflated(self):
        a=data["case_records"][0]
        self.assertEqual([m["scope"] for m in a["metrics"]],["single_operator","pipeline_mte2","pipeline_mte2"])
        d=next(c for c in data["case_records"] if c["id"]=="ASC-OP-006")
        self.assertEqual(next(m for m in d["metrics"] if m["id"]=="total")["before"],149.82)
        self.assertEqual(next(m for m in d["metrics"] if m["id"]=="total")["after"],93.76)
        self.assertEqual(d["reported_only"][0]["before"],0)
        self.assertTrue(d["reported_only"][0]["after"]>0)
    def test_issue_observation_tpt_does_not_falsely_improve(self):
        rows=[c for c in data["case_records"] if c["source_kind"]=="github_issue_report"]
        self.assertEqual(len(rows),2)
        for r in rows:
            t=next(m for m in r["metrics"] if m["id"]=="tpot")
            self.assertGreater(t["after"],t["before"])
            self.assertFalse(t["comparable"])
            self.assertEqual(r["workload"]["requests"],100)
            self.assertEqual(r["workload"]["repeat_rounds"],2)
            self.assertIn("缓存",r["change"])
    def test_documentation_demo_excluded(self):
        self.assertTrue(all(x["source_kind"]=="documentation_example" for x in data["documentation_examples"]))
        self.assertFalse(any(m["comparable"] for x in data["documentation_examples"] for m in x["metrics"]))
        self.assertTrue(all(x["id"] not in [c["id"] for c in data["case_records"]] for x in data["documentation_examples"]))
    def test_build_injects_case_data_and_controls(self):
        import sys
        sys.path.insert(0,str(HERE/"site"))
        import build_site
        p=build_site.build_payload()
        self.assertEqual(p["experimentEvidence"]["collection"]["metric_pairs"],24)
        html=build_site.render()
        for id in ("experiment-hub","experiment-query","experiment-tabs","experiment-cards",
                   "experiment-detail","exp-summary","experiment-example"):
            self.assertIn('id="'+id+'"',html)
        self.assertIn("project_own_hardware_measurements",html)
        self.assertIn("非隔离 A/B",html)
        self.assertIn("document.getElementById",html)
        self.assertNotIn("/* APP_JS_INJECT */",html)

if __name__=="__main__":
    unittest.main()
