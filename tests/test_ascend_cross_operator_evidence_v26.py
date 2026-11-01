"""V2.6 specialist evidence: prevent unsupported NPU speedup and ABI claims."""
import json
import unittest
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]/"design"/"ascend-explorer-v2"
d=json.loads((BASE/"content"/"cross-operator-evidence-v2.6.json").read_text("utf-8"))

class CrossOperatorTests(unittest.TestCase):
    def test_seven_unique_sources_and_no_project_npu_measurement(self):
        rows=d["case_records"]
        self.assertEqual(len(rows),7)
        self.assertEqual(len(set(r["id"] for r in rows)),7)
        self.assertEqual(len(set(r["source_url"] for r in rows)),7)
        self.assertEqual(d["project_owned_npu_benchmarks"],0)
        self.assertEqual(d["case_count"],7)
        self.assertEqual(d["paired_observations"],7)
        self.assertEqual(d["unpaired_observations"],18)
        self.assertEqual({r["area"] for r in rows},{"attention","moe","gdn","communication"})

    def test_every_metric_has_scope_and_warning(self):
        for r in d["case_records"]:
            self.assertIn(r["kind"],{"operator","service"})
            self.assertTrue(r["source_url"].startswith("https://github.com/"))
            self.assertTrue(r["source_status"] and r["constraints"] and r["workload"])
            for m in r["metrics"]:
                self.assertTrue(m["scope"] and m["unit"] and m["label"])
                self.assertFalse(m["comparable"],"No new V2.6 observation is isolated A/B")
                self.assertIsNotNone(m["before"])
                self.assertIsNotNone(m["after"])
            for v in r["reported_only"]:
                self.assertTrue(v["metric"] and v["statement"] and v["unit"])
                self.assertIn("value",v)

    def test_attention_pr_has_no_fake_time_pairs(self):
        a=next(r for r in d["case_records"] if r["id"]=="ASC-ATT-001")
        self.assertEqual(a["metrics"],[])
        self.assertEqual([x["value"] for x in a["reported_only"]],[6.2,1.7])
        self.assertIn("open PR",a["source_status"])
        self.assertIn("FlashAttentionScoreV4",a["workload"]["operator"])

    def test_moe_probe_is_standalone_not_service_gain(self):
        p=next(r for r in d["case_records"] if r["id"]=="ASC-MOE-001")
        self.assertEqual(p["workload"]["calls_per_round"],200)
        self.assertEqual(p["workload"]["rounds"],7)
        self.assertEqual([x["value"] for x in p["reported_only"]],[5.495,5.591,5.485])
        self.assertEqual(p["metrics"],[])
        t=next(r for r in d["case_records"] if r["id"]=="ASC-MOE-002")
        self.assertEqual(t["reported_only"][0]["value"],9.72)
        self.assertTrue(any("+1.5ms" in x["statement"] for x in t["reported_only"]))
        self.assertTrue(any("仅 MoE" in s for s in t["constraints"]))

    def test_gdn_is_memory_failure_not_tps(self):
        c=next(r for r in d["case_records"] if r["id"]=="ASC-GDN-001")
        self.assertEqual((c["metrics"][0]["before"],c["metrics"][0]["after"]),(4,39))
        self.assertEqual([v["value"] for v in c["reported_only"]],[19.45,15.47])
        self.assertEqual(c["metrics"][0]["scope"],"configuration_impact")

    def test_collective_incidents_have_noncomparable_scope(self):
        c=next(r for r in d["case_records"] if r["id"]=="ASC-COMM-001")
        self.assertEqual((c["metrics"][0]["before"],c["metrics"][0]["after"]),(1719.37,105.9))
        self.assertEqual(c["reported_only"][0]["value"],1051)
        x=next(r for r in d["case_records"] if r["id"]=="ASC-COMM-002")
        self.assertEqual((x["metrics"][0]["before"],x["metrics"][0]["after"]),(1.58,8.19))
        self.assertNotEqual(x["workload"]["output_len_v023"],x["workload"]["output_len_v026"])
        self.assertFalse(all(m["comparable"] for m in x["metrics"]))

    def test_readable_offline_site_has_seven_specialist_cases(self):
        import sys
        sys.path.insert(0,str(BASE/"site"))
        import build_site
        p=build_site.build_payload()
        self.assertEqual(p["crossOperatorEvidence"]["case_count"],7)
        self.assertEqual(p["atlas"]["project_hardware_measurements"],0)
        h=build_site.render()
        self.assertIn("ASC-ATT-001",h)
        self.assertIn("ASC-COMM-001",h)
        self.assertIn("ASC-MOE-002",h)
        self.assertIn("source_status",h)
        self.assertIn("source_url",h)
        self.assertNotIn("/* APP_JS_INJECT */",h)

if __name__=="__main__":
    unittest.main()
