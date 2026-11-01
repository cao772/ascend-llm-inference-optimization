#!/usr/bin/env python3
"""Download a pinned official Qwen snapshot when explicitly requested.

Requires: pip install -U huggingface_hub
This downloads to local disk, NOT to Google Drive; see docs/qwen-model-archive.md.
Default is a dry run. It never puts model weights in GitHub.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from qwen_inventory import CATALOG, select_models


def allowed_metadata_file(name):
    return name in {
        "README.md", "LICENSE", "config.json", "configuration.json",
        "generation_config.json", "tokenizer.json", "tokenizer_config.json",
        "chat_template.jinja", "preprocessor_config.json",
        "video_preprocessor_config.json", "special_tokens_map.json",
        "vocab.json", "merges.txt", ".gitattributes",
    } or name.endswith(".json") and not name.endswith("safetensors.index.json")


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", required=True, help="one official Qwen model from catalog")
    parser.add_argument("--dest", type=Path, default=Path("model-checkpoints"))
    parser.add_argument("--execute", action="store_true", help="actually download after checks")
    parser.add_argument("--include-weights", action="store_true", help="include large model weight shards")
    parser.add_argument("--max-gb", type=float, default=100.0, help="hard cap per snapshot in decimal GB")
    args = parser.parse_args()
    if args.max_gb <= 0:
        parser.error("--max-gb must be positive")

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    try:
        model = select_models(catalog, [args.model_id])[0]
    except ValueError as exc:
        parser.error(str(exc))
    target = args.dest.resolve() / args.model_id.split("/", 1)[1]
    if not args.execute:
        print(json.dumps({
            "mode": "dry_run", "model": model, "target": str(target),
            "include_weights": args.include_weights,
            "max_gb": args.max_gb, "uploaded_to_drive": False,
        }, ensure_ascii=False, indent=2))
        return 0

    try:
        from huggingface_hub import HfApi, snapshot_download
    except ImportError as error:
        parser.error("Install huggingface_hub first: pip install -U huggingface_hub")

    info = HfApi().model_info(args.model_id, files_metadata=True)
    files = list(info.siblings or [])
    selected = [f for f in files if args.include_weights or allowed_metadata_file(f.rfilename)]
    if not selected:
        parser.error("No files matched the selected mode")
    sizes = [getattr(f, "size", None) for f in selected]
    if any(not isinstance(size, int) or size < 0 for size in sizes):
        parser.error("Cannot verify complete remote size; refusing an unbounded download")
    expected_bytes = sum(sizes)
    if expected_bytes > args.max_gb * 1e9:
        parser.error(f"Snapshot requires {expected_bytes / 1e9:.2f} GB; max {args.max_gb:.2f} GB")
    target.parent.mkdir(parents=True, exist_ok=True)
    free_bytes = shutil.disk_usage(target.parent).free
    if free_bytes < expected_bytes * 1.1:
        parser.error(f"Not enough free disk: need 10% headroom above {expected_bytes / 1e9:.2f} GB")
    print(f"Downloading {args.model_id}@{info.sha}, {expected_bytes / 1e9:.2f} GB, {len(selected)} files")
    path = snapshot_download(
        repo_id=args.model_id,
        revision=info.sha,
        local_dir=str(target),
        allow_patterns=None if args.include_weights else [f.rfilename for f in selected],
    )
    downloaded = []
    for filename in sorted(p for p in Path(path).rglob("*") if p.is_file() and ".cache" not in p.parts):
        if filename.name == "local-checksums.json":
            continue
        downloaded.append({
            "path": filename.relative_to(path).as_posix(),
            "bytes": filename.stat().st_size,
            "sha256": sha256_file(filename),
        })
    expected_names = {f.rfilename for f in selected}
    got_names = {f["path"] for f in downloaded}
    if expected_names != got_names:
        raise RuntimeError(f"Snapshot incomplete: missing={sorted(expected_names-got_names)}, unexpected={sorted(got_names-expected_names)}")
    receipt = {
        "repo_id": args.model_id, "revision": info.sha,
        "license_reported_by_hub": (getattr(info, "card_data", None) or {}).get("license") if isinstance(getattr(info, "card_data", None), dict) else None,
        "mode": "full_weights" if args.include_weights else "metadata_only",
        "download_complete": True, "uploaded_to_drive": False,
        "files": downloaded,
    }
    (target / "local-checksums.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Local snapshot verified: {target}. Google Drive upload NOT performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
