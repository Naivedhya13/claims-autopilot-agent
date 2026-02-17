from __future__ import annotations
from typing import Dict, List

QUESTION_MAP = {
    "patient.member_id": "What is the insurance member ID?",
    "providers.billing_npi": "What is the billing provider NPI?",
    "providers.rendering_npi": "What is the rendering provider NPI?",
    "providers.ordering_provider_name": "What is the ordering provider name?",
    "providers.referring_provider_id": "What is the referring provider identifier/NPI?",
    "claim.date_of_service": "What is the date of service (YYYY-MM-DD)?",
    "claim.place_of_service": "What is the place of service (e.g., 11 for office)?",
}

def questions_from_issues(issues: List[Dict[str, str]]) -> List[str]:
    qs: List[str] = []
    for it in issues:
        field = it.get("field", "")
        if field in QUESTION_MAP:
            qs.append(QUESTION_MAP[field])

    seen = set()
    out = []
    for q in qs:
        if q not in seen:
            out.append(q)
            seen.add(q)
    return out