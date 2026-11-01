#!/usr/bin/env python3
"""Export V2.6 source-reported specialist observations. Never treat them as our benchmark."""
import argparse
import csv
import json
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
SRC=BASE/"content/cross-operator-evidence-v2.6.json"
FIELDS=["case_id","technical_area","record_type","source_kind","source_status","hardware",
        "model","metric","before","after","reported_value","unit","scope","isolated_ab",
        "source_url","limitations","workload_json","original_statement","project_measured"]


def make_rows(payload):
    for case in payload["case_records"]:
        base={"case_id":case["id"],"technical_area":case["area"],
              "source_kind":case["source_kind"],"source_status":case["source_status"],
              "hardware":case["hardware"],"model":case.get("model") or "",
              "source_url":case["source_url"],
              "limitations":" | ".join(case["constraints"]),
              "workload_json":json.dumps(case["workload"],ensure_ascii=False,sort_keys=True),
              "isolated_ab":"false","project_measured":"false"}
        for m in case["metrics"]:
            yield {**base,"record_type":"reported_two_state_value","metric":m["label"],
                   "before":m["before"],"after":m["after"],"reported_value":"",
                   "unit":m["unit"],"scope":m["scope"],
                   "original_statement":"Observation under different states; not isolated A/B."}
        for m in case["reported_only"]:
            yield {**base,"record_type":"reported_single_value","metric":m["metric"],
                   "before":"","after":"","reported_value":m["value"],"unit":m["unit"],
                   "scope":"source_report_only","original_statement":m["statement"]}


def export(target:Path):
    payload=json.loads(SRC.read_text("utf-8"))
    if payload["project_owned_npu_benchmarks"]!=0:
        raise ValueError("V2.6 stores external evidence ONLY")
    rows=list(make_rows(payload))
    n_pair=sum(x["record_type"]=="reported_two_state_value" for x in rows)
    n_single=sum(x["record_type"]=="reported_single_value" for x in rows)
    if n_pair!=payload["paired_observations"] or n_single!=payload["unpaired_observations"]:
        raise ValueError("Counts do not reconcile")
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open("w",newline="",encoding="utf-8-sig") as out:
        writer=csv.DictWriter(out,fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"External evidence CSV ready: {len(rows)} rows = {n_pair} two-state + {n_single} single-point; local hardware measurements=0")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    export(p.parse_args().output)
