#!/usr/bin/env python3
"""Export the curated V2.5 public observations as auditable, scope-aware CSV rows.

The CSV is not a project NPU benchmark and must never be merged across scopes
without matching workload/hardware/metric and a reproducible A/B design.
"""
import argparse
import csv
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
INPUT = BASE / "content" / "experiment-evidence-v2.5.json"
HEADERS = ["case_id","title","source_kind","experiment_type","hardware","model",
           "metric_id","metric_name","metric_scope","unit","direction",
           "before","after","paired_source_values","isolated_ab",
           "source_url","workload_json","change","constraints_json",
           "project_hardware_reproduction"]


def records(payload):
    for case in payload["case_records"]:
        for metric in case["metrics"]:
            yield {
                "case_id":case["id"],"title":case["title"],"source_kind":case["source_kind"],
                "experiment_type":"operator" if case["id"].startswith("ASC-OP") else "service_observation",
                "hardware":case["hardware"],"model":case.get("model") or "",
                "metric_id":metric["id"],"metric_name":metric["label"],
                "metric_scope":metric["scope"],"unit":metric["unit"],"direction":metric["direction"],
                "before":metric["before"],"after":metric["after"],
                "paired_source_values":str(metric["before"] is not None and metric["after"] is not None).lower(),
                "isolated_ab":"false" if case["source_kind"]=="github_issue_report" else "not_established",
                "source_url":case["source_url"],
                "workload_json":json.dumps(case["workload"],ensure_ascii=False,sort_keys=True),
                "change":case["change"],
                "constraints_json":json.dumps(case["constraints"],ensure_ascii=False),
                "project_hardware_reproduction":"false"
            }


def export(output:Path):
    payload=json.loads(INPUT.read_text(encoding="utf-8"))
    if payload["project_own_hardware_measurements"]!=0:
        raise ValueError("Only external evidence is accepted by this exporter")
    rows=list(records(payload))
    count=payload["collection"]["metric_pairs"]
    if len(rows)!=count or count!=24:
        raise ValueError("Case metrics do not match curated pair count")
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=HEADERS)
        w.writeheader()
        w.writerows(rows)
    print(f"Created evidence CSV: {len(rows)} metric observations from {len(payload['case_records'])} source cases; local hardware results=0")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    export(parser.parse_args().output)
