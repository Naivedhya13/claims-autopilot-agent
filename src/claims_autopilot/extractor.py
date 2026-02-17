from __future__ import annotations
import re
from typing import Optional, List
from .schemas import ClaimPacket, ServiceLine
from .llm import call_json

SYSTEM = """You are a careful healthcare revenue-cycle assistant.
Extract a ClaimPacket from a synthetic superbill / visit summary.

Hard requirements:
- Output ONLY valid JSON.
- Never invent values (NPIs, member IDs, dates, codes).
- patient.insurance MUST be a single string (payer/plan), not an object.
- patient.member_id MUST be a string if present.
- providers.billing_npi and providers.rendering_npi MUST be 10-digit strings if present.
- claim.diagnoses is a list of ICD-10 codes (strings), e.g. ["J02.9","R50.9"]
- claim.lines is a list of service lines. Each line has:
  - cpt_hcpcs (string)
  - units (int, default 1 if missing)
  - modifiers (list of strings; empty list if none)
  - diagnosis_pointer (list of ints; empty list if missing)
If something is unknown, set it to null/empty list.
"""

USER_TEMPLATE = """Extract a ClaimPacket from the following text.

TEXT:
{txt}

Return JSON with keys: patient, providers, claim, meta.
"""

def _find(pattern: str, txt: str) -> Optional[str]:
    m = re.search(pattern, txt, re.IGNORECASE)
    return m.group(1).strip() if m else None

def _parse_pos(txt: str) -> Optional[str]:
    m = re.search(r"Place\s+of\s+Service:\s*([0-9]{2})", txt, re.IGNORECASE)
    return m.group(1) if m else None

def _parse_diagnoses(txt: str) -> List[str]:
    dx = []
    in_dx = False
    for line in txt.splitlines():
        if re.search(r"^\s*Diagnoses\b", line, re.IGNORECASE):
            in_dx = True
            continue
        if in_dx and re.search(r"^\s*Procedures\b", line, re.IGNORECASE):
            break
        if in_dx:
            m = re.search(r"^\s*-\s*([A-Z][0-9A-Z\.]{2,8})\b", line.strip())
            if m:
                dx.append(m.group(1))
    return list(dict.fromkeys(dx))

def _parse_service_lines(txt: str) -> List[ServiceLine]:
    lines: List[ServiceLine] = []
    in_proc = False
    current: Optional[dict] = None

    def flush():
        nonlocal current
        if current and current.get("cpt_hcpcs"):
            lines.append(ServiceLine(
                cpt_hcpcs=current["cpt_hcpcs"],
                units=int(current.get("units", 1) or 1),
                modifiers=current.get("modifiers", []) or [],
                diagnosis_pointer=current.get("diagnosis_pointer", []) or [],
            ))
        current = None

    for raw in txt.splitlines():
        line = raw.rstrip("\n")
        if re.search(r"^\s*Procedures\b", line, re.IGNORECASE):
            in_proc = True
            continue
        if not in_proc:
            continue

        m = re.search(r"^\s*-\s*([0-9]{5}|[A-Z][0-9A-Z]{3,6})\b", line)
        if m:
            flush()
            current = {"cpt_hcpcs": m.group(1), "units": 1, "modifiers": [], "diagnosis_pointer": []}
            continue

        if current is None:
            continue

        mu = re.search(r"Units:\s*(\d+)", line, re.IGNORECASE)
        if mu:
            current["units"] = int(mu.group(1))
            continue

        mm = re.search(r"Modifiers?:\s*(.+)", line, re.IGNORECASE)
        if mm:
            val = mm.group(1).strip()
            if val.lower().startswith("(none"):
                current["modifiers"] = []
            else:
                mods = [x.strip() for x in re.split(r"[,\s]+", val) if x.strip() and x.strip() != "(none)"]
                current["modifiers"] = mods
            continue

        md = re.search(r"Diagnosis\s+pointer:\s*(.+)", line, re.IGNORECASE)
        if md:
            nums = []
            for x in re.split(r"[,\s]+", md.group(1).strip()):
                if x.strip().isdigit():
                    nums.append(int(x.strip()))
            current["diagnosis_pointer"] = nums
            continue

        if re.search(r"^\s*Clinical\s+notes\b", line, re.IGNORECASE):
            break

    flush()
    return lines

def _regex_extract(txt: str) -> ClaimPacket:
    packet = ClaimPacket()
    packet.patient.name = _find(r"Patient:\s*(.+)", txt) or packet.patient.name
    packet.patient.dob = _find(r"DOB:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", txt)
    packet.patient.insurance = _find(r"Insurance:\s*(.+)", txt)
    packet.patient.member_id = _find(r"Member\s*ID:\s*([A-Za-z0-9\-]+)", txt)

    packet.providers.billing_npi = _find(r"Billing\s+Provider\s+NPI:\s*([0-9]{10})", txt)
    packet.providers.rendering_npi = _find(r"Rendering\s+Provider\s+NPI:\s*([0-9]{10})", txt)
    packet.providers.ordering_provider_name = _find(r"Ordering\s+Provider\s+Name:\s*(.+)", txt)
    packet.providers.referring_provider_id = _find(r"Referring\s+Provider\s+Identifier/NPI:\s*([0-9]{10})", txt)

    packet.claim.date_of_service = _find(r"Date\s+of\s+Service:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", txt)
    packet.claim.place_of_service = _parse_pos(txt)
    packet.claim.diagnoses = _parse_diagnoses(txt)
    packet.claim.lines = _parse_service_lines(txt)

    packet.meta["extraction_mode"] = "regex"
    return packet

def _merge(base: ClaimPacket, patch: ClaimPacket) -> ClaimPacket:
    b, p = base, patch

    if (not b.patient.name or b.patient.name == "SYNTHETIC PATIENT") and p.patient.name:
        b.patient.name = p.patient.name
    if b.patient.dob is None and p.patient.dob:
        b.patient.dob = p.patient.dob
    if b.patient.member_id is None and p.patient.member_id:
        b.patient.member_id = p.patient.member_id
    if b.patient.insurance is None and p.patient.insurance:
        b.patient.insurance = p.patient.insurance

    if b.providers.billing_npi is None and p.providers.billing_npi:
        b.providers.billing_npi = p.providers.billing_npi
    if b.providers.rendering_npi is None and p.providers.rendering_npi:
        b.providers.rendering_npi = p.providers.rendering_npi
    if b.providers.ordering_provider_name is None and p.providers.ordering_provider_name:
        b.providers.ordering_provider_name = p.providers.ordering_provider_name
    if b.providers.referring_provider_id is None and p.providers.referring_provider_id:
        b.providers.referring_provider_id = p.providers.referring_provider_id

    if b.claim.date_of_service is None and p.claim.date_of_service:
        b.claim.date_of_service = p.claim.date_of_service
    if b.claim.place_of_service is None and p.claim.place_of_service:
        b.claim.place_of_service = p.claim.place_of_service
    if (not b.claim.diagnoses) and p.claim.diagnoses:
        b.claim.diagnoses = p.claim.diagnoses
    if (not b.claim.lines) and p.claim.lines:
        b.claim.lines = p.claim.lines

    b.meta = {**(b.meta or {}), **(p.meta or {})}
    return b

def extract_claim_from_text(txt: str) -> ClaimPacket:
    regex_packet = _regex_extract(txt)

    # Try LLM extraction first
    llm_packet = call_json(SYSTEM, USER_TEMPLATE.format(txt=txt), ClaimPacket)
    llm_packet.meta["extraction_mode"] = "llm"

    # Patch missing values from regex
    merged = _merge(llm_packet, regex_packet)
    return merged