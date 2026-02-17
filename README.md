# Claims Autopilot Agent (Healthcare Insurance Claims Copilot)

A beginner-friendly **AI agent** that helps automate parts of the healthcare insurance claims workflow:

1) **Build Claim** from a superbill/visit text (synthetic) into a structured claim JSON  
2) **Precheck** to catch common denial risks before submission  
3) **Denied? Fix It** by interpreting CARC/RARC denial codes and generating a correction plan + appeal draft

> **Safety/Compliance**
> - Use **synthetic** examples only. Do **not** paste real patient information (PHI).
> - This tool provides **administrative support** (workflow assistance), not medical or legal advice.
> - Never fabricate information. Only submit what you can document.

## Quickstart (local)

### 1) Setup
```bash
git clone <your-repo-url>
cd claims-autopilot-agent

python -m venv .venv
source .venv/bin/activate   # (Windows: .venv\Scripts\activate)

pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set:
- `OPENAI_API_KEY` (required to use the LLM features)
- `MODEL` (optional)

### 2) Run Streamlit app
```bash
streamlit run src/claims_autopilot/app.py
```

### 3) Or run the CLI
```bash
python -m claims_autopilot.cli precheck --text-file data/sample_superbill.txt
python -m claims_autopilot.cli denial --text-file data/sample_denial_era.txt
```

## Project structure
- `src/claims_autopilot/` – core agent modules
- `data/` – synthetic demo inputs + a small CARC/RARC mapping subset
- `outputs/` – generated claim packets and reports

## Extending to real systems (future)
For a real integration you would connect:
- EHR / billing system exports (not included)
- EDI 837 generation and 276/277 status checks (not included)
- Larger CARC/RARC codebook + payer rule libraries (not included)

## Demo script (for recruiters)
1. Open app → **Build Claim** → load sample superbill → generate structured claim  
2. Go to **Precheck** → show risk report + missing field questions  
3. Go to **Denied? Fix It** → load sample denial → show plain-English explanation + correction plan + appeal draft
