#!/usr/bin/env python3
"""Generate a traceable Qwen model snapshot plan; default mode makes NO requests.

Examples:
  python3 tools/qwen_inventory.py --output build/qwen-plan.json
  python3 tools/qwen_inventory.py --online --output build/qwen-live-metadata.json
  python3 tools/qwen_inventory.py --online --only Qwen/Qwen3.6-27B
Requires only Python's standard library. Online results are metadata, not downloads.
"""
import argparse
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog" / "qwen-research-models.json"


def select_models(catalog, requested):
    models = catalog["models"]
    ids = {m["id"] for m in models}
    unknown = set(requested) - ids
    if unknown:
        raise ValueError("Unknown model IDs: " + ", ".join(sorted(unknown)))
    return [m for m in models if not requested or m["id"] in requested]


def remote_metadata(model_id, timeout=25):
    if not model_id.startswith("Qwen/") or "/" in model_id[5:]:
        raise ValueError("Only Qwen/<model_name> official repositories are allowed")
    url = "https://huggingface.co/api/models/" + quote(model_id, safe="/") + "?blobs=true"
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "qwen-infra-research/0.1"})
    with urlopen(req, timeout=timeout) as response:
        data = json.load(response)
    siblings = data.get("siblings") or []
    sizes = [f.get("size") or (f.get("lfs") or {}).get("size") for f in siblings]
    total = sum(n for n in sizes if isinstance(n, int) and n >= 0)
    missing = sum(n is None for n in sizes)
    card = data.get("cardData") or {}
    return {
        "revision": data.get("sha"),
        "license_reported_by_hub": card.get("license"),
        "file_count": len(siblings),
        "total_bytes": total if siblings and missing == 0 else None,
        "files_without_size": missing,
        "all_file_sizes_known": bool(siblings) and missing == 0,
        "hub_url": "https://huggingface.co/" + model_id,
    }


def generate(catalog, requested, online, get_metadata=remote_metadata):
    rows = []
    for model in select_models(catalog, requested):
        item = dict(model)
        item["downloaded"] = False
        item["uploaded_to_drive"] = False
        item["sha256_verified"] = False
        item["hub_metadata_status"] = "not_checked"
        if online:
            try:
                item["remote"] = get_metadata(model["id"])
                item["hub_metadata_status"] = "checked"
            except (HTTPError, URLError, OSError, ValueError, KeyError) as error:
                item["hub_metadata_status"] = "error"
                item["hub_error"] = type(error).__name__ + ": " + str(error)
        rows.append(item)
    return {
        "schema_version": "1.0",
        "catalog_as_of": catalog["as_of"],
        "scope": "selected research models, not all Qwen checkpoints or quantizations",
        "operation": "online_metadata_only" if online else "offline_catalog_only",
        "no_weights_downloaded_or_uploaded": True,
        "models": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--online", action="store_true", help="read official Hub metadata; no model download")
    parser.add_argument("--only", action="append", default=[], metavar="Qwen/MODEL", help="limit model IDs")
    parser.add_argument("--output", type=Path, help="write JSON manifest at this path")
    args = parser.parse_args()
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    result = generate(catalog, args.only, args.online)
    encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
        print(f"Model metadata plan: {args.output}; models={len(result['models'])}")
    else:
        print(encoded, end="")
    return int(any(m["hub_metadata_status"] == "error" for m in result["models"]))


if __name__ == "__main__":
    raise SystemExit(main())
