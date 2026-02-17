from __future__ import annotations
from typing import Dict, Any
import json
import pandas as pd
from pathlib import Path

def to_table(packet: Dict[str, Any]) -> pd.DataFrame:
    lines = packet.get("claim", {}).get("lines", []) or []
    rows = []
    for idx, ln in enumerate(lines, start=1):
        rows.append({
            "line": idx,
            "cpt_hcpcs": ln.get("cpt_hcpcs"),
            "units": ln.get("units", 1),
            "modifiers": ",".join(ln.get("modifiers", []) or []),
            "dx_pointer": ",".join(str(x) for x in (ln.get("diagnosis_pointer", []) or [])),
        })
    return pd.DataFrame(rows)

def export_outputs(packet: Dict[str, Any], out_dir: str = "outputs") -> Dict[str, str]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    json_path = str(Path(out_dir) / "claim_packet.json")
    csv_path = str(Path(out_dir) / "claim_lines.csv")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(packet, f, indent=2)

    df = to_table(packet)
    df.to_csv(csv_path, index=False)
    return {"json": json_path, "csv": csv_path}
