"""Evidence-atlas integrity, lossless provenance and retrieval behavior."""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_qwen_evidence_atlas as atlas_mod  # noqa: E402
import query_qwen_evidence as query_mod  # noqa: E402


class EvidenceAtlasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = atlas_mod._load(atlas_mod.CASES_PATH)
        cls.models = atlas_mod._load(atlas_mod.MATRIX)
        cls.links = atlas_mod._load(atlas_mod.LINKS)
        cls.prs = atlas_mod._load(atlas_mod.PRS_PATH)
        cls.failures = atlas_mod._load(atlas_mod.FAILURES_PATH)
        cls.graph = atlas_mod.build_atlas(cls.cases, cls.models, cls.links, cls.prs, cls.failures)

    def test_schema_controls_nodes_relations_and_evidence_levels(self):
        schema = json.loads(
            (ROOT / "research/schemas/qwen-evidence-atlas.schema.json").read_text("utf-8")
        )
        self.assertEqual(schema["properties"]["project_hardware_measurements"]["const"], 0)
        kinds = set(schema["properties"]["nodes"]["items"]["properties"]["kind"]["enum"])
        relations = set(schema["properties"]["edges"]["items"]["properties"]["relation"]["enum"])
        levels = set(schema["properties"]["edges"]["items"]["properties"]["evidence_level"]["enum"])
        self.assertTrue({n["kind"] for n in self.graph["nodes"]} <= kinds)
        self.assertTrue({e["relation"] for e in self.graph["edges"]} <= relations)
        self.assertTrue({e["evidence_level"] for e in self.graph["edges"]} <= levels)
        for e in self.graph["edges"]:
            for field in schema["properties"]["edges"]["items"]["required"]:
                self.assertIn(field, e)

    def test_failure_nodes_always_stay_unreproduced_in_schema(self):
        schema = json.loads(
            (ROOT / "research/schemas/qwen-evidence-atlas.schema.json").read_text("utf-8")
        )
        self.assertTrue(schema["properties"]["nodes"]["items"]["properties"]["not_project_reproduced"]["const"])
        self.assertTrue(all(n["not_project_reproduced"] for n in self.graph["nodes"]
                            if n["kind"] == "failure_or_caveat"))

    def test_counts_and_not_local_benchmarks(self):
        g = self.graph
        self.assertEqual(g["project_hardware_measurements"], 0)
        for kind, expected in (("case", 15), ("model", 5),
                               ("upstream_pr", 12), ("failure_or_caveat", 8)):
            self.assertEqual(g["counts"]["by_node_kind"][kind], expected)
        self.assertEqual(len(g["edges"]), g["counts"]["edges"])

    def test_every_edge_has_provenance_and_valid_endpoints(self):
        ids = {n["id"] for n in self.graph["nodes"]}
        for e in self.graph["edges"]:
            self.assertIn(e["source"], ids)
            self.assertIn(e["target"], ids)
            self.assertTrue(e["provenance_urls"])
            self.assertTrue(all(url.startswith("https://") for url in e["provenance_urls"]))
            self.assertFalse(e["runtime_dispatch_verified_by_project"])
            self.assertFalse(e["speedup_verified_by_project"])

    def test_cross_model_and_cross_stage_prs_not_case_direct(self):
        pr_to_case = [e for e in self.graph["edges"] if e["relation"] == "pr_documents_specific_case"]
        self.assertEqual(len(pr_to_case), 5)
        self.assertTrue(all(e["source"] not in {
            "pr:PR-SGL-12787", "pr:PR-SGL-20792",
            "pr:PR-SGL-23402", "pr:PR-VLLM-51674"
        } for e in pr_to_case))

    def test_all_five_models_excluded_only_from_specific_guard(self):
        exclusions = [e for e in self.graph["edges"] if
                      e["relation"] == "excludes_pr51674_head_ratio_branch"]
        self.assertEqual(len(exclusions), 5)
        self.assertTrue(all(e["target"] == "pr:PR-VLLM-51674" for e in exclusions))
        self.assertTrue(all(e["not_a_universal_gdn_incompatibility"] for e in exclusions))

    def test_failure_provenance_keeps_removal_distinct_from_regression(self):
        fs = [n for n in self.graph["nodes"] if n["kind"] == "failure_or_caveat"]
        self.assertEqual(sum(x["failure_kind"] == "feature_removed" for x in fs), 3)
        self.assertEqual(sum(x["failure_kind"] == "numerical_regression" for x in fs), 1)
        self.assertTrue(all(x["not_project_reproduced"] for x in fs))

    def test_derived_similarity_explicitly_noncausal(self):
        sims = [e for e in self.graph["edges"] if e["relation"] == "shares_tags"]
        self.assertTrue(sims)
        self.assertTrue(all(e["evidence_level"] == "derived_tag_cooccurrence" for e in sims))
        self.assertTrue(all(e["explicitly_noncausal"] for e in sims))

    def test_repeatable_and_no_mutation_of_case_sources(self):
        input1 = copy.deepcopy(self.cases)
        first = atlas_mod.build_atlas(input1, self.models, self.links, self.prs, self.failures)
        self.assertEqual(input1, self.cases)
        self.assertEqual(first, atlas_mod.build_atlas(self.cases, self.models, self.links, self.prs, self.failures))

    def test_unknown_pr_reference_fails_closed(self):
        broken = copy.deepcopy(self.failures)
        broken["failures"][0]["linked_pr_ids"] = ["PR-NONEXISTENT"]
        with self.assertRaisesRegex(ValueError, "unknown PR"):
            atlas_mod.build_atlas(self.cases, self.models, self.links, self.prs, broken)

    def test_unknown_mechanism_fails_closed(self):
        broken = copy.deepcopy(self.failures)
        broken["failures"][0]["mechanisms"] = ["invented"]
        with self.assertRaisesRegex(ValueError, "Unknown failure mechanism"):
            atlas_mod.build_atlas(self.cases, self.models, self.links, self.prs, broken)

    def test_direct_pr_case_scope_must_be_explicit(self):
        broken = copy.deepcopy(self.prs)
        target = next(x for x in broken["entries"] if x["id"] == "PR-VLLM-51674")
        target["cases"] = ["QINF-004"]
        with self.assertRaisesRegex(ValueError, "unverified direct case"):
            atlas_mod.build_atlas(self.cases, self.models, self.links, broken, self.failures)

    def test_model_query_evidence(self):
        r = query_mod.retrieve(self.graph, "model_id", "Qwen/Qwen3.6-27B")
        self.assertEqual(r["anchors_included"], ["model:Qwen/Qwen3.6-27B"])
        self.assertIn("pr:PR-VLLM-51674", [n["id"] for n in r["nodes"]])
        self.assertFalse(r["portability_or_speedup_proven"])

    def test_failure_query_fetches_pr_evidence(self):
        r = query_mod.retrieve(self.graph, "failure_kind", "deadlock")
        self.assertEqual(r["anchor_total"], 2)
        self.assertTrue(any(e["relation"] == "failure_or_caveat_documented_by_pr" for e in r["edges"]))

    def test_exact_case_query_not_fuzzy(self):
        r = query_mod.retrieve(self.graph, "case_id", "QINF-004")
        self.assertEqual(r["anchor_total"], 1)
        q = query_mod.retrieve(self.graph, "case_id", "QINF-04")
        self.assertEqual(q["anchor_total"], 0)

    def test_literal_chinese_search(self):
        r = query_mod.retrieve(self.graph, "text", "死锁", radius=0)
        self.assertGreaterEqual(r["anchor_total"], 1)
        self.assertEqual(r["search_type"], "exact_typed_or_literal_substring_only_not_semantic")

    def test_bounded_result_and_invalid_radius(self):
        r = query_mod.retrieve(self.graph, "mechanism", "fusion", max_nodes=3)
        self.assertLessEqual(len(r["nodes"]), 3)
        self.assertTrue(r["truncated_neighbors"])
        self.assertFalse(r["truncated_anchors"])
        r2 = query_mod.retrieve(self.graph, "failure_kind", "feature_removed", max_nodes=1)
        self.assertEqual(len(r2["anchors_included"]), 1)
        self.assertTrue(r2["truncated_anchors"])
        with self.assertRaisesRegex(ValueError, "radius"):
            query_mod.retrieve(self.graph, "mechanism", "fusion", radius=3)

    def test_cli_smoke(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "tools/query_qwen_evidence.py"),
             "--model-id", "Qwen/Qwen3.5-35B-A3B", "--radius", "1"],
            text=True, capture_output=True, cwd=ROOT,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["anchor_total"], 1)


if __name__ == "__main__":
    unittest.main()
