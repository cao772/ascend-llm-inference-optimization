#!/usr/bin/env python3
"""Build an offline, source-grounded, one-file Ascend V2 explainer.

Data is read from existing project JSON and the already validated evidence atlas.
It contains NO live hardware telemetry, NO invented SKU specs, NO new weight files.
"""
import argparse
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # repository root
sys.path.insert(0, str(ROOT / "tools"))
from build_qwen_evidence_atlas import load_atlas


def json_read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_payload():
    base = HERE.parent
    payload = {
        "schema_version": "2.0-offline",
        "as_of": "2026-11-01",
        "mode": "educational_demo_not_npu_benchmark",
        "hardware": json_read(base / "content/hardware-catalog.json"),
        "productLineage": json_read(base / "content/product-lineage-v2.json"),
        "verifiedSpecs": json_read(base / "content/verified-product-specs-v2.2.json"),
        "softwareCompat": json_read(base / "content/software-compat-v2.2.json"),
        "architecturePaths": json_read(base / "content/architecture-paths-v2.2.json"),
        "operators": json_read(base / "content/operator-stories.json"),
        "modules": json_read(base / "content/modules.json"),
        "cases": json_read(ROOT / "research/cases/qwen-optimization-cases-2026-10-30.json"),
        "prs": json_read(ROOT / "research/source-traces/qwen-operator-pr-lineage-2026-10-30.json"),
        "failures": json_read(ROOT / "research/failures/qwen-operator-failure-modes-2026-10-31.json"),
        "atlas": load_atlas(),
    }
    if payload["atlas"]["project_hardware_measurements"] != 0:
        raise ValueError("Project NPU observations require a separate verified data contract")
    if payload["hardware"]["asOf"] != "2026-11-01":
        raise ValueError("Hardware catalog is not the reviewed version")
    return payload


def render():
    source = (HERE / "index.html").read_text(encoding="utf-8")
    style = (HERE / "app.css").read_text(encoding="utf-8")
    script = (HERE / "app.js").read_text(encoding="utf-8")
    for marker in ("/* APP_CSS_INJECT */", "/* DATA_JSON_INJECT */", "/* APP_JS_INJECT */"):
        if source.count(marker) != 1:
            raise ValueError("Missing or duplicate injection marker " + marker)
    data = json.dumps(build_payload(), ensure_ascii=False, separators=(",", ":"))
    data = data.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    # Browser must never be able to terminate embedded source tags from project input.
    if "</script" in data.lower() or "</style" in style.lower() or "</script" in script.lower():
        raise ValueError("unsafe literal closing tag")
    page = source.replace("/* APP_CSS_INJECT */", style)
    page = page.replace("/* DATA_JSON_INJECT */", data)
    page = page.replace("/* APP_JS_INJECT */", script)
    if "/* APP_" in page:
        raise ValueError("Unfilled source marker")
    return page


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = render()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8")
    print(f"Created standalone Ascend V2 interactive website: {args.output} ({len(output)} chars)")


if __name__ == "__main__":
    main()
