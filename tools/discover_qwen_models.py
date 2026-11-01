#!/usr/bin/env python3
"""Read the official Qwen Hugging Face organization's public model inventory.

Network access is explicit (--online); this script NEVER downloads model weights.
Paging is bounded and all results are labeled incomplete until pagination ends.
"""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

BASE = "https://huggingface.co/api/models"
VARIANTS = ("-GGUF", "-FP8", "-AWQ", "-GPTQ", "-INT4", "-INT8", "-MLX")


def validate_next_url(url):
    parsed = urlsplit(url)
    qs = parse_qs(parsed.query)
    if (parsed.scheme != "https" or parsed.hostname != "huggingface.co"
            or parsed.port not in (None, 443) or parsed.path != "/api/models"
            or qs.get("author") != ["Qwen"] or parsed.username or parsed.password):
        raise ValueError("Unexpected pagination URL; refusing external follow-up")
    return url


def read_page(url):
    validate_next_url(url)
    request = Request(url, headers={"Accept": "application/json",
                                    "User-Agent": "qwen-inference-research/0.2"})
    with urlopen(request, timeout=35) as response:
        payload = json.load(response)
        link = response.headers.get("Link", "")
    if not isinstance(payload, list):
        raise ValueError("HF models API returned a non-list response")
    next_url = None
    for entry in link.split(","):
        match = re.match(r'\s*<([^>]+)>\s*;\s*rel="next"', entry.strip())
        if match:
            next_url = validate_next_url(match.group(1))
            break
    return payload, next_url


def classify(model_id):
    name = model_id.split("/", 1)[1]
    if re.search(r"Embedding", name, re.I):
        category = "embedding"
    elif re.search(r"Reranker", name, re.I):
        category = "reranker"
    elif re.search(r"ASR|ForcedAligner", name, re.I):
        category = "speech-recognition"
    elif re.search(r"TTS", name, re.I):
        category = "text-to-speech"
    elif re.search(r"Omni|Audio", name, re.I):
        category = "omni-audio"
    elif re.search(r"Image", name, re.I):
        category = "image"
    elif re.search(r"VL|Vision", name, re.I):
        category = "vision-language"
    elif re.search(r"Coder", name, re.I):
        category = "code"
    else:
        category = "text-generation-or-other"
    m = re.match(r"(Qwen(?:2(?:\.5)?|3(?:\.\d+)?)(?:-Next)?)", name)
    family = m.group(1) if m else ("Qwen" if name.startswith("Qwen") else "other")
    return {
        "family": family,
        "category_guess": category,
        "moe_name_hint": bool(re.search(r"\d+B-A\d+B", name)),
        "variant_name_hint": next((v[1:] for v in VARIANTS if v.lower() in name.upper().lower()), None),
    }


def collect(fetcher=read_page, max_pages=30, page_size=100):
    if not 1 <= max_pages <= 200:
        raise ValueError("max_pages must be 1..200")
    if not 1 <= page_size <= 100:
        raise ValueError("page_size must be 1..100")
    url = BASE + "?" + urlencode({"author": "Qwen", "limit": page_size, "full": "true"})
    seen_pages, by_id = set(), {}
    page_count = 0
    failure = None
    while url and page_count < max_pages:
        if url in seen_pages:
            failure = "Repeated pagination cursor"
            break
        seen_pages.add(url)
        try:
            rows, nxt = fetcher(url)
            if not isinstance(rows, list):
                raise ValueError("Invalid rows type")
            if nxt:
                validate_next_url(nxt)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            failure = type(exc).__name__ + ": " + str(exc)
            break
        page_count += 1
        for row in rows:
            if not isinstance(row, dict):
                continue
            model_id = row.get("id") or row.get("modelId")
            if not isinstance(model_id, str) or not model_id.startswith("Qwen/"):
                continue
            if model_id in by_id:
                continue
            card = row.get("cardData")
            card = card if isinstance(card, dict) else {}
            by_id[model_id] = {
                "id": model_id,
                **classify(model_id),
                "revision": row.get("sha"),
                "license_reported_by_hub": card.get("license"),
                "pipeline_tag": row.get("pipeline_tag"),
                "gated": row.get("gated", False),
                "private": row.get("private", False),
                "source": "https://huggingface.co/" + model_id,
                "weights_mirrored_to_drive": False,
            }
        url = nxt
    return {
        "schema_version": "1.0",
        "source": "Hugging Face models API, author=Qwen",
        "page_count": page_count,
        "complete": url is None and failure is None,
        "truncated_by_max_pages": bool(url and failure is None),
        "error": failure,
        "model_count": len(by_id),
        "classification": "heuristic only, verify model card",
        "license_scope": "model-specific license; missing value is unknown, not permissive",
        "weights_downloaded": False,
        "models": [by_id[k] for k in sorted(by_id)],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--online", action="store_true", help="explicitly fetch official model metadata")
    p.add_argument("--max-pages", type=int, default=30)
    p.add_argument("--page-size", type=int, default=100)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    if not args.online:
        p.error("No network by default. Pass --online to enumerate the public Qwen catalog")
    try:
        report = collect(max_pages=args.max_pages, page_size=args.page_size)
    except ValueError as exc:
        p.error(str(exc))
    raw = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw, encoding="utf-8")
        print(f"{args.output}: {report['model_count']} model IDs, complete={report['complete']}")
    else:
        print(raw, end="")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
