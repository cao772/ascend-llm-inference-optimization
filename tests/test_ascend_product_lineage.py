"""Official Ascend product-family evidence and four-level drill-down contract."""
import json
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "design" / "ascend-explorer-v2" / "content"


class HardwareLineageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((BASE / "hardware-catalog.json").read_text("utf-8"))
        cls.lineage = json.loads((BASE / "product-lineage-v2.json").read_text("utf-8"))

    def test_every_catalog_product_resolves_to_one_known_family(self):
        families = {f["id"]: f for f in self.lineage["families"]}
        self.assertEqual(len(families), len(self.lineage["families"]))
        self.assertEqual(len(families), 6)
        for p in self.catalog["products"]:
            override = self.lineage["productFamilyOverrides"].get(p["id"])
            matches = [f["id"] for f in families.values() if f["name"] == p["family"]]
            self.assertIn(override or (matches[0] if matches else ""), families)
            self.assertTrue((override or (matches[0] if matches else "")))

    def test_processor_mapping_is_scope_limited_to_source_document(self):
        mappings = self.lineage["productProcessorMappings"]
        self.assertEqual({x["productId"] for x in mappings},
                         {"atlas-300i-pro", "atlas-300i-duo"})
        self.assertTrue(all(x["processorFamily"] == "Ascend 310P" for x in mappings))
        self.assertTrue(all(x["confidence"] == "official_product_family" for x in mappings))
        self.assertTrue(all(x["sourceUrl"].startswith("https://www.hiascend.com/")
                            for x in mappings))
        self.assertTrue(all("SKU" in x["scope"] or "产品族" in x["scope"]
                            for x in mappings))

    def test_a3_topology_applies_to_a3_only(self):
        t = self.lineage["topologyCase"]
        self.assertEqual(t["productId"], "atlas-900-a3")
        self.assertEqual(len(t["steps"]), 5)
        self.assertIn("HCCS-L2", " ".join(t["steps"]))
        self.assertIn("不代表", t["warning"])
        self.assertIn("hiascend.com", t["sourceUrl"])

    def test_specs_are_not_fabricated(self):
        self.assertTrue(self.lineage["unverifiedQuantitativeSpecs"])
        for p in self.catalog["products"]:
            self.assertTrue(all(x is None for x in p["quantitative"].values()))
        self.assertEqual(len(self.catalog["products"]), 10)

    def test_family_provenance_and_metadata_are_complete(self):
        for f in self.lineage["families"]:
            self.assertTrue(f["sourceUrl"].startswith("https://www.hiascend.com/"))
            self.assertTrue(f["sourceVersion"])
            self.assertTrue(f["focus"])


if __name__ == "__main__":
    unittest.main()
