from __future__ import annotations
from typing import Dict, Any, List, Tuple
import re
import pandas as pd
from pydantic import BaseModel, Field
from .llm import call_json

def extract_codes(text: str) -> Tuple[List[str], List[str]]:
    carc = re.findall(r"CARC\s*(\d+)", text)
    rarc = re.findall(r"RARC\s*([A-Z]\d+)", text)
    return list(dict.fromkeys(carc)), list(dict.fromkeys(rarc))

def load_codebook(csv_path: str) -> pd.DataFrame:
    return pd.read_csv(csv_path)

def lookup_meanings(codebook: pd.DataFrame, carc: List[str], rarc: List[str]) -> Dict[str, List[Dict[str, str]]]:
    out = {"CARC": [], "RARC": []}
    for c in carc:
        sub = codebook[(codebook["code_type"] == "CARC") & (codebook["code"].astype(str) == str(c))]
        out["CARC"].append({"code": str(c), "meaning": str(sub.iloc[0]["meaning"]) if len(sub) else "Meaning not found in demo subset."})
    for r in rarc:
        sub = codebook[(codebook["code_type"] == "RARC") & (codebook["code"].astype(str) == str(r))]
        out["RARC"].append({"code": str(r), "meaning": str(sub.iloc[0]["meaning"]) if len(sub) else "Meaning not found in demo subset."})
    return out

SYSTEM = """You are a revenue-cycle denial assistant.
Given denial codes and a denial message, produce:
- plain_english_summary
- likely_missing_items (list)
- correction_steps (list)
- appeal_draft (short letter)

Rules:
- Do not suggest fabricating information.
- Keep it practical and brief.
- Output JSON only.
"""

class DenialPlan(BaseModel):
    plain_english_summary: str
    likely_missing_items: List[str] = Field(default_factory=list)
    correction_steps: List[str] = Field(default_factory=list)
    appeal_draft: str

def build_denial_plan(denial_text: str, meanings: Dict[str, Any]) -> DenialPlan:
    user = f"""Denial text:
{denial_text}

Known meanings:
{meanings}

Return a DenialPlan JSON."""
    return call_json(SYSTEM, user, DenialPlan)