# ClearScript — PBM Disclosure Audit Engine

ClearScript helps self-insured employers audit their Pharmacy Benefit Managers (PBMs) under the new DOL transparency rule and HR 7148. It's the translation layer between raw PBM disclosures and actionable savings decisions.

Self-insured employers cover ~65% of American workers, and PBMs (Express Scripts, CVS Caremark, Optum Rx) have been overcharging them for years through spread pricing, rebate retention, and formulary manipulation. The DOL proposed sweeping transparency rules on January 30, 2026, and HR 7148 was signed into law on February 3, 2026. ClearScript gives employers the tools to exercise their new rights.

## Features

### Compliance Tier
1. **Contract Intake & Parsing** — Upload a PBM contract (PDF/TXT), AI extracts key terms (rebate passthrough, spread pricing caps, formulary clauses, audit rights, MAC pricing, termination provisions) and flags non-compliant clauses against DOL requirements.
2. **Initial Disclosure Analyzer** — Scores PBM disclosure completeness against DOL-required items. Generates a gap report showing what's missing.
3. **Audit Request Generator** — Generates pre-formatted audit request letters citing specific regulatory provisions, with 10-business-day PBM response deadline tracking.
4. **Compliance Deadline Tracker** — Tracks DOL rule, HR 7148, and 40+ state-level PBM reform bills with alerts at 90/60/30 days.

### Audit Tier
5. **Semiannual Report Auditor** — Cross-references PBM reports against pharmacy claims data and NADAC pricing. Detects rebate and spread pricing discrepancies.
6. **Rebate Passthrough Tracker** — Tracks every rebate dollar from manufacturer to PBM to plan. Calculates rebate leakage percentage.
7. **Spread Pricing Detection Engine** — Compares plan-paid vs pharmacy-reimbursed amounts per prescription, broken down by retail, mail-order, and specialty.

### Full Platform
8. **Pharmacy Network Adequacy Analyzer** — Checks pharmacy network coverage against employee zip codes. Identifies phantom networks.
9. **Formulary Manipulation Detector** — Tracks mid-year formulary changes correlated with rebate incentives. Flags suspicious generic-to-brand swaps.
10. **Benchmarking Dashboard** — Anonymized peer comparison on cost per script, rebate passthrough %, specialty spend, and generic dispensing rate.

### Data Management
- **Claims Upload** — Upload employer pharmacy claims CSV. All analysis features run on your actual data instead of sample data.

## Tech Stack

- **Frontend**: Next.js 16 (App Router) + TypeScript + Tailwind CSS + Recharts
- **Backend**: Python FastAPI
- **AI**: OpenAI GPT-5 mini for contract parsing, disclosure analysis, and audit letter generation
- **Data Sources**:
  - NADAC pricing (live CMS Medicaid API)
  - CMS NPPES pharmacy registry
  - FDA Orange Book (drug equivalency)
  - AHRQ MEPS (employer pharmacy spending benchmarks)

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.9+
- OpenAI API key

### Setup

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/clearscript.git
cd clearscript

# Backend
cd backend
pip install -r requirements.txt
cd ..

# Frontend
cd frontend
npm install
cd ..

# Environment
cp .env.example .env
# Add your OpenAI API key to .env
```

### Run

```bash
# Terminal 1 — Backend
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend
cd frontend
npx next dev --port 3000
```

Open http://localhost:3000

## Target Market

HR directors and benefits managers at self-insured employers with 200-5,000 employees. Roughly 30,000+ employers in this range. Secondary market: benefits brokers (35,000 in the US) who white-label the platform for their clients.

## Why Now

- **HR 7148** signed into law Feb 3, 2026 — requires 100% rebate passthrough
- **DOL transparency rule** proposed Jan 30, 2026 — mandates unrestricted audit rights with 10-day PBM response deadline
- **FTC investigation** documented Big 3 PBM abuses (spread pricing, rebate retention, steering)
- Employers are about to receive an avalanche of PBM data they've never seen before and have no idea how to interpret

## License

MIT
