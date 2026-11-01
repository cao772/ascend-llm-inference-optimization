#!/usr/bin/env python3
"""Validate v2 DESIGN inputs (offline, no model/NPU, no inferred hardware specs).

This checks content integrity, evidence URLs, unknown numeric fields, and
granularity of the storyboard. It does not validate vendor compatibility.
"""
import argparse
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
CONTENT = BASE / "content"
FRAMES = ("input", "execution", "memory", "bottleneck", "optimization", "validation")
FORMS = {"module", "edge_system", "accelerator_card", "inference_server",
         "training_server", "compute_pod"}
REQUIRED_MODULES = tuple("M%02d" % x for x in range(9))
QUAL_STATUS = {"not_assessed", "confirmed_in_version", "unsupported_in_version"}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_design(catalog, stories, modules, design_text, types_text, css_text):
    if catalog.get("schemaVersion") != "2.0-design":
        raise ValueError("Bad product catalog version")
    if stories.get("schemaVersion") != "2.0-design" or modules.get("schemaVersion") != "2.0-design":
        raise ValueError("Bad design data schema version")

    products, seen = catalog["products"], set()
    for x in products:
        pid = x["id"]
        if pid in seen or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", pid):
            raise ValueError("Duplicate or invalid product ID")
        seen.add(pid)
        if x["form"] not in FORMS or not x["family"] or not x["name"]:
            raise ValueError("Unknown/empty product family or form: " + pid)
        if not x["sourceUrl"].startswith("https://www.hiascend.com/"):
            raise ValueError("Product evidence must come from official website: " + pid)
        if x["claimLevel"] != "official_product" or x["compatibilityStatus"] not in QUAL_STATUS:
            raise ValueError("Product evidence level or compatibility status missing")
        if not x["limitations"] or not x["sourceVersion"]:
            raise ValueError("Product source limitations/version absent")
        for key, val in x["quantitative"].items():
            if val is not None:
                sources = x.get("quantitativeEvidence", {})
                if key not in sources or not sources[key].startswith("https://"):
                    raise ValueError("Numeric hardware spec lacks field-level evidence: " + pid + "." + key)
                if not isinstance(val, (int, float)) or isinstance(val, bool) or val < 0:
                    raise ValueError("Invalid numeric hardware specification")

    topics = catalog["processorResearchTopics"]
    if len({t["id"] for t in topics}) != len(topics):
        raise ValueError("Duplicate processor research topic")
    for t in topics:
        if not t["notAPhysicalCard"] or t["sourceStatus"] != "specific_product_datasheet_not_collected":
            raise ValueError("Unsupported processor research topic assertion")
        if t["id"] in seen:
            raise ValueError("Processor topic mixed with product SKU")

    if stories["frameContract"] != list(FRAMES):
        raise ValueError("Wrong storyboard frame contract")
    if len(stories["stories"]) < 7 or len({s["id"] for s in stories["stories"]}) != len(stories["stories"]):
        raise ValueError("Missing or duplicated operator story")
    for story in stories["stories"]:
        if not story["sourceUrls"] or not all(url.startswith("https://") for url in story["sourceUrls"]):
            raise ValueError("Story lacks HTTPS provenance")
        if story["localPerformanceEvidence"] is not False or not story["limitations"]:
            raise ValueError("Operator story must mark simulated/limited evidence")
        frames = story["frames"]
        if [f["slug"] for f in frames] != list(FRAMES) or [f["index"] for f in frames] != list(range(1, 7)):
            raise ValueError("Story should contain six ordered frames")
        if any(f["observed"] is not False or not f["label"] for f in frames):
            raise ValueError("Cannot claim actual hardware observations in design")

    allmods = modules["modules"]
    if [m["id"] for m in allmods] != list(REQUIRED_MODULES):
        raise ValueError("Expected M00–M08 ordered modules")
    if len({m["hash"] for m in allmods}) != len(allmods):
        raise ValueError("Duplicate module hash")
    if [n["id"] for n in modules["navigation"]] != list(REQUIRED_MODULES):
        raise ValueError("Navigation and design modules diverged")
    for m in allmods:
        if m["implementationStatus"] != "design_only":
            raise ValueError("Design cannot claim implementation verified")
        if not m["acceptance"] or not m["evidenceDrawer"] or m["motion"] != "reduced-motion-safe":
            raise ValueError("Module missing interaction or accessible acceptance")
    if modules["scope"]["hasNPUResults"] is not False:
        raise ValueError("Never invent performance results")
    if "M00" not in design_text or "M08" not in design_text:
        raise ValueError("DESIGN.md lacks module explanations")
    if "EMPTY_BENCHMARK" not in types_text or "performanceCanBeCalledMeasured" not in types_text:
        raise ValueError("Missing measurement evidence gate")
    if "prefers-reduced-motion" not in css_text or ":focus-visible" not in css_text:
        raise ValueError("Missing keyboard/motion accessibility tokens")

    return {
        "design_status": "review_candidate_not_implemented",
        "products_officially_categorized": len(products),
        "processor_topics_not_merged_with_cards": len(topics),
        "operator_stories": len(stories["stories"]),
        "operator_frames": sum(len(s["frames"]) for s in stories["stories"]),
        "design_modules": len(allmods),
        "observed_npu_performance": False,
        "result": "design_data_and_evidence_checks_pass",
    }


def validate_repository():
    return check_design(
        load_json(CONTENT / "hardware-catalog.json"),
        load_json(CONTENT / "operator-stories.json"),
        load_json(CONTENT / "modules.json"),
        (BASE / "DESIGN.md").read_text(encoding="utf-8"),
        (BASE / "src/types.ts").read_text(encoding="utf-8"),
        (BASE / "src/tokens.css").read_text(encoding="utf-8"),
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    data = validate_repository()
    result = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result, end="")
