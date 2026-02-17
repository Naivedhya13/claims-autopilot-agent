from __future__ import annotations
from typing import Dict, Any, List
import yaml
from .utils import get_path

def load_rules(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def _service_codes(packet_dict: Dict[str, Any]) -> List[str]:
    lines = get_path(packet_dict, "claim.lines") or []
    codes: List[str] = []
    if isinstance(lines, list):
        for ln in lines:
            if isinstance(ln, dict):
                c = ln.get("cpt_hcpcs")
                if c:
                    codes.append(str(c).strip())
    return codes

def validate(packet_dict: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
    issues: List[Dict[str, str]] = []

    for rf in rules.get("required_fields", []):
        val = get_path(packet_dict, rf)
        if val is None or val == "" or val == []:
            issues.append({"type": "missing_required", "field": rf, "message": f"Missing required field: {rf}"})

    for chk in rules.get("basic_checks", []):
        if chk.get("type") == "min_list_len":
            val = get_path(packet_dict, chk.get("path", ""))
            if not isinstance(val, list) or len(val) < int(chk.get("min", 1)):
                issues.append({"type": "check_failed", "field": chk.get("path", ""), "message": chk.get("message", "Check failed")})

    svc_codes = set(_service_codes(packet_dict))
    for chk in rules.get("conditional_checks", []):
        if chk.get("type") == "requires_field_for_codes":
            codes = set(str(x).strip() for x in (chk.get("codes") or []))
            field = chk.get("field", "")
            if svc_codes.intersection(codes):
                val = get_path(packet_dict, field)
                if val is None or val == "" or val == []:
                    msg = (chk.get("message") or "Missing field for codes").format(codes=",".join(sorted(codes)))
                    issues.append({"type": "conditional_missing", "field": field, "message": msg})

    risk = "LOW"
    if any(i["type"] in ("missing_required", "conditional_missing") for i in issues):
        risk = "HIGH"
    elif issues:
        risk = "MEDIUM"

    return {"risk": risk, "issues": issues}