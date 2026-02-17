from __future__ import annotations
import argparse, json
from pathlib import Path
from .extractor import extract_claim_from_text
from .validator import load_rules, validate
from .questioner import questions_from_issues
from .generator import export_outputs
from .denial import extract_codes, load_codebook, lookup_meanings, build_denial_plan

def cmd_precheck(text_file: str):
    txt = Path(text_file).read_text(encoding="utf-8")
    packet = extract_claim_from_text(txt)
    packet_dict = packet.model_dump()

    rules = load_rules("data/rules.yml")
    report = validate(packet_dict, rules)
    qs = questions_from_issues(report["issues"])

    exports = export_outputs(packet_dict)
    out = {"risk": report["risk"], "issues": report["issues"], "questions": qs, "exports": exports}
    print(json.dumps(out, indent=2))

def cmd_denial(text_file: str):
    txt = Path(text_file).read_text(encoding="utf-8")
    carc, rarc = extract_codes(txt)
    codebook = load_codebook("data/carc_rarc_subset.csv")
    meanings = lookup_meanings(codebook, carc, rarc)
    plan = build_denial_plan(txt, meanings)
    print(plan.model_dump_json(indent=2))

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("precheck")
    p1.add_argument("--text-file", required=True)

    p2 = sub.add_parser("denial")
    p2.add_argument("--text-file", required=True)

    args = p.parse_args()
    if args.cmd == "precheck":
        cmd_precheck(args.text_file)
    elif args.cmd == "denial":
        cmd_denial(args.text_file)

if __name__ == "__main__":
    main()
