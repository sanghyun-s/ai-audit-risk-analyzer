# AI Audit Risk Analyzer

ML anomaly detection + materiality-calibrated risk scoring + PCAOB-aligned labels for QuickBooks GL exports.

A generalized audit software (GAS) prototype that automates transaction-level analytical review procedures (ARP) on SMB general ledger data. Built as a portfolio piece exploring the intersection of accounting standards, machine learning, and LLM-driven narrative generation.

## What it does

Upload a GL CSV, configure the client profile (entity type, materiality benchmark, detection sensitivity, audit period), and the app runs the following pipeline in under a second:

1. **Validates** the file structure and required columns
2. **Cleans** and coerces dtypes (date → datetime, amount → numeric, derives `abs_amount`)
3. **Engineers 12 audit-domain features** — 6 Tier 1 features that feed the ML model (account-level magnitude z-score, round number, weekend posting, missing description, new vendor, near approval threshold) plus 6 Tier 2 features for display and override logic (control gap score, fraud risk flag, period-over-period %, vendor concentration %, year-end concentration, non-standard DR/CR pattern)
4. **Runs 4 data integrity checks** — hash total, cross-footing, date-in-period, account mapping
5. **Scores anomalies** with Isolation Forest (200 trees, sensitivity-controlled contamination)
6. **Applies the materiality filter** — downgrades or escalates the raw ML tier based on whether the dollar amount exceeds Performance / Transaction materiality
7. **Labels** findings with PCAOB-aligned language: *Potential Material Weakness Indicator*, *Potential Significant Deficiency*, *Monitor — Below Escalation Threshold*
8. **Returns** a sortable, exportable table of flagged transactions with the specific risk indicators that fired on each row

The core thesis: a generic ML anomaly detector finds statistically unusual transactions. An audit-grade tool also asks whether the dollar amount matters and translates findings into the cautious, hedged language standards require.

## Architecture

```
┌─────────────────────────────┐         ┌─────────────────────────────┐
│  Next.js frontend           │  HTTP   │  FastAPI backend            │
│  (React 18, shadcn/ui,      │ ──────► │  (Python 3.13)              │
│   Tailwind, plotly.js)      │  multi- │                             │
│  - Client profile form      │  part   │  features.py    cleaning + 12 feats
│  - CSV upload widget        │ ◄────── │  integrity.py   4 audit checks
│  - Integrity panel          │  JSON   │  model.py       Isolation Forest
│  - PCAOB tier chart         │         │  scoring.py     materiality filter
│  - Flagged txn table        │         │  api.py         /api/analyze endpoint
│  Port 3000 (dev)            │         │  Port 8000 (dev)            │
└─────────────────────────────┘         └─────────────────────────────┘
```

The frontend and backend are independently deployable. The same Python pipeline is reachable via:
- `POST /api/analyze` over HTTP — used by the Next.js UI
- Direct import (`from features import engineer_features`) — used by `smoke_test.py` for regression testing

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| ML | scikit-learn (IsolationForest, StandardScaler) | Unsupervised anomaly detection on engineered audit features |
| Data | pandas, numpy | Tabular transforms over the GL |
| API | FastAPI + uvicorn | Type-safe, async-ready, OpenAPI for free |
| Frontend | Next.js 14 (App Router, JavaScript) | Modern React with server-side defaults |
| UI primitives | shadcn/ui + Tailwind CSS | Composable, no runtime CSS-in-JS overhead |
| Charts | plotly.js (`react-plotly.js`) | Interactive Plotly charts in React |
| Testing | TestClient (FastAPI), bespoke `smoke_test.py` | 22 acceptance criteria asserted per build |

## Project structure

```
app3/
├── backend/
│   ├── api.py                  FastAPI app — POST /api/analyze, GET /api/options, /api/healthz
│   ├── api_test.py             End-to-end test of the FastAPI endpoint using TestClient
│   ├── features.py             Cleaning + 12 engineered features (6 T1 for ML, 6 T2 for display)
│   ├── integrity.py            4 pre-analysis data integrity checks
│   ├── model.py                StandardScaler + IsolationForest → anomaly_score + raw_tier
│   ├── scoring.py              Materiality filter → final_tier + pcaob_label + active_flags
│   ├── generate_sample_gl.py   2,000-row simulated GL with planted anomalies
│   ├── smoke_test.py           Asserts 22 Phase 1 + Phase 2 done-criteria
│   ├── requirements.txt
│   └── sample_data/
│       └── sample_gl.csv       Generated demo data
│
└── frontend/
    ├── app/
    │   ├── layout.jsx
    │   ├── page.jsx            Main analyzer page wiring all sections
    │   └── globals.css
    ├── components/
    │   ├── ClientProfileForm.jsx
    │   ├── CsvUpload.jsx
    │   ├── IntegrityPanel.jsx
    │   ├── FeatureFiringPanel.jsx
    │   ├── SummaryCards.jsx
    │   ├── MaterialityBanner.jsx
    │   ├── RiskDistributionChart.jsx
    │   ├── TopAccountsChart.jsx
    │   ├── FlaggedTable.jsx
    │   └── ui/                 shadcn primitives (button, card, input, label, select, badge)
    ├── lib/
    │   ├── api.js              Thin fetch wrapper for the FastAPI endpoints
    │   └── utils.js            shadcn cn() helper
    ├── next.config.js          Proxies /api/* to FastAPI (localhost:8000) in dev
    ├── tailwind.config.js
    └── package.json
```

## Running locally

### Prerequisites
- Python 3.11+ (tested on 3.13)
- Node.js 18+ (tested on 22)

### Backend (terminal 1)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python generate_sample_gl.py     # creates sample_data/sample_gl.csv
python smoke_test.py             # verifies 22 acceptance criteria pass
uvicorn api:app --reload --port 8000
```

The FastAPI server is now serving on `http://localhost:8000`. Hit `/api/healthz` to verify.

### Frontend (terminal 2)

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Upload `backend/sample_data/sample_gl.csv`, click **Run Analysis**, and the full pipeline runs end-to-end against the FastAPI backend.

### Running the test suite

```bash
cd backend
source .venv/bin/activate
python smoke_test.py             # Phase 1 + Phase 2 pipeline criteria (22)
python api_test.py               # FastAPI endpoint contract (35+ checks)
```

## Audit theory references

The 12 features and the materiality filter are anchored to specific audit-standard sources:

| Feature | Source | What it captures |
|---|---|---|
| `amount_zscore_by_account` | AU-C 315, ARP | Account-level magnitude deviation |
| `is_round_number` | PCAOB AS 2401 | Manual entry / estimate red flag |
| `is_weekend_posting` | Control activities | Unusual posting timing |
| `missing_description` | Information & communication (COSO) | Documentation control gap |
| `is_new_vendor` | Fraud risk factors | Misappropriation opportunity |
| `is_near_approval_threshold` | IT controls / limit tests | Invoice splitting / approval avoidance |
| Materiality filter | PCAOB AS 5 | Severity-of-deficiency framework |
| PCAOB labels | PCAOB AS 5 | "Potential Material Weakness Indicator", etc. |

The GPT narrative layer (Phase 4) extends this with structured prompts referencing AU-C 315 assertion considerations and the COSO five-component framework.

## Roadmap

This is an in-progress portfolio project. Status:

- ✅ **Phase 1** — MVP: CSV upload → 6-feature ML pipeline → PCAOB-labeled table + charts (Streamlit prototype, since migrated)
- ✅ **Phase 2** — 6 Tier 2 features, data integrity layer, FastAPI restructure, Next.js + shadcn frontend
- ⬜ **Phase 3** — Qualitative override rule (≥2 fraud flags → force High regardless of materiality), Tier 2 scoring badges in the table
- ⬜ **Phase 4** — GPT narrative layer: each flagged row gets a 7-field JSON risk memo in hedged, PCAOB-aligned audit language with a rule-based fallback if the API fails
- ⬜ **Phase 5** — Deployment (Vercel + Render/Railway), Excel workbook export, period-over-period fluctuation table, demo polish

## Methodology and limitations

This tool identifies *risk indicators* using statistical anomaly detection and materiality thresholds. It does not determine intent, conclude fraud, or issue audit opinions. The PCAOB-aligned labels use "Potential", "Indicator", and "Monitor" throughout — never definitive language.

Findings should be corroborated with documentary evidence and discussions with management consistent with AU-C 315 (Understanding the Entity and Its Environment) and PCAOB AS 2401 (Consideration of Fraud in a Financial Statement Audit).

Sample data is simulated. The cross-footing integrity check often produces a warning on QuickBooks-style "one row per leg" GL exports — this is expected and demonstrates the integrity layer working on realistic input rather than indicating a tool defect.
