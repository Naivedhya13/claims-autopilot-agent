from __future__ import annotations

import sys
from pathlib import Path
import json
import streamlit as st

# Make 'src' importable when running Streamlit directly
SRC_DIR = Path(__file__).resolve().parents[1]  # points to src/
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from claims_autopilot.extractor import extract_claim_from_text
from claims_autopilot.validator import load_rules, validate
from claims_autopilot.questioner import questions_from_issues
from claims_autopilot.generator import export_outputs, to_table
from claims_autopilot.denial import extract_codes, load_codebook, lookup_meanings, build_denial_plan

st.set_page_config(page_title="Claims Autopilot Agent", layout="wide")
st.title("Claims Autopilot Agent (Synthetic Demo)")

st.info("Use synthetic examples only. Do not paste real patient information (PHI).")

tab1, tab2, tab3 = st.tabs(["1) Build Claim", "2) Precheck", "3) Denied? Fix It"])

if "packet" not in st.session_state:
    st.session_state.packet = None

with tab1:
    st.subheader("Build a structured claim packet from text")
    colA, colB = st.columns([2,1])

    with colA:
        txt = st.text_area("Paste a synthetic superbill / visit summary", height=260)
        if st.button("Load sample superbill"):
            txt = Path("data/sample_superbill.txt").read_text(encoding="utf-8")
            st.session_state["sample_superbill"] = txt
        if "sample_superbill" in st.session_state and not txt:
            txt = st.session_state["sample_superbill"]

        if st.button("Extract claim (LLM)") and txt.strip():
            packet = extract_claim_from_text(txt)
            st.session_state.packet = packet.model_dump()
            st.success("Extracted claim packet.")

    with colB:
        if st.session_state.packet:
            st.write("Claim JSON")
            st.code(json.dumps(st.session_state.packet, indent=2), language="json")

with tab2:
    st.subheader("Precheck (denial risk + missing info)")
    if not st.session_state.packet:
        st.warning("Go to 'Build Claim' and extract a claim first.")
    else:
        rules = load_rules("data/rules.yml")
        report = validate(st.session_state.packet, rules)
        st.write("Risk:", report["risk"])
        st.write("Issues:")
        st.json(report["issues"])
        qs = questions_from_issues(report["issues"])
        if qs:
            st.write("Questions to ask (only what's needed):")
            for q in qs:
                st.write("- " + q)
        else:
            st.success("No obvious missing fields from demo rules.")

        st.write("Claim lines table:")
        st.dataframe(to_table(st.session_state.packet), use_container_width=True)

        if st.button("Export outputs to /outputs"):
            paths = export_outputs(st.session_state.packet)
            st.success(f"Saved: {paths}")

with tab3:
    st.subheader("Denial → correction plan + appeal draft")
    denial_txt = st.text_area("Paste synthetic ERA/EOB/denial text", height=220)
    if st.button("Load sample denial"):
        denial_txt = Path("data/sample_denial_era.txt").read_text(encoding="utf-8")
        st.session_state["sample_denial"] = denial_txt
    if "sample_denial" in st.session_state and not denial_txt:
        denial_txt = st.session_state["sample_denial"]

    if st.button("Analyze denial (LLM)") and denial_txt.strip():
        carc, rarc = extract_codes(denial_txt)
        codebook = load_codebook("data/carc_rarc_subset.csv")
        meanings = lookup_meanings(codebook, carc, rarc)

        st.write("Codes found:", {"CARC": carc, "RARC": rarc})
        st.write("Code meanings (demo subset):")
        st.json(meanings)

        plan = build_denial_plan(denial_txt, meanings)
        st.write("Plain-English summary:")
        st.write(plan.plain_english_summary)
        st.write("Likely missing items:")
        st.write(plan.likely_missing_items)
        st.write("Correction steps:")
        st.write(plan.correction_steps)
        st.write("Appeal draft (short):")
        st.code(plan.appeal_draft)
