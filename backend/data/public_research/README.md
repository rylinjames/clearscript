# Public PBM Research Library

This folder stores public-source material gathered to harden ClearScript's PBM contract analysis beyond a pure heuristic implementation.

## What is in here

### Contracts

- `contracts/nashp_model_pbm_contract_terms_2020.pdf`
  - Model PBM contract terms from NASHP.
  - Use: baseline "good governance" benchmark for rebate passthrough, audit rights, spread pricing, and specialty controls.

- `contracts/nastad_pbm_contract_language_bank.pdf`
  - Public contract language bank collected by NASTAD.
  - Use: alternative benchmark clauses and stronger drafting examples for redlines and comparison logic.

- `contracts/michigan_state_employee_pbm_contract_220000001116.pdf`
  - Real public state employee PBM contract.
  - Use: live contract benchmark for how a negotiated public-sector arrangement allocates pricing, audit, rebate, and specialty rights.

- `contracts/michigan_medicaid_pbm_contract_071B0200069.pdf`
  - Public Michigan Medicaid PBM contract artifact.
  - Use: second live contract benchmark for clause coverage and control allocation.

### Audits

- `audits/ohio_medicaid_managed_care_pharmacy_services_2018.pdf`
  - Public audit associated with PBM spread-pricing findings.
  - Use: calibrate severity for spread pricing and support exposure messaging.

- `audits/pennsylvania_performrx_audit_2024.pdf`
  - Public audit covering PerformRx / DHS oversight and pricing controls.
  - Use: strengthen audit-rights interpretation and control-map logic.

- `audits/delaware_pbm_report_analysis_2025.pdf`
  - Public PBM report and analysis prepared for Delaware.
  - Use: current public evidence on PBM economics, specialty control, and plan sponsor leverage.

### Benchmarks

- `benchmarks/ftc_pbm_first_interim_report_2024.pdf`
  - FTC first interim staff report on pharmacy benefit managers.
  - Use: market evidence for concentration, spread, and control-risk framing.

- `benchmarks/ftc_pbm_second_interim_report_2025.pdf`
  - FTC second interim staff report.
  - Use: support for specialty and vertical-integration risk interpretation.

- `benchmarks/gao_selected_states_pbm_regulation_2024.html`
  - Access-denied response captured during automated fetch from GAO.
  - Use: none directly. Keep only as provenance showing the source was attempted but blocked in this environment.

- `benchmarks/gao_selected_states_pbm_regulation_2024.pdf`
  - Blocked placeholder from GAO direct PDF attempt.
  - Use: none directly.

### Pricing

- `pricing/cms_nadac_methodology_2024.pdf`
  - CMS NADAC methodology document.
  - Use: benchmark reference for ingredient-cost reasoning and pharmacy reimbursement comparisons.

## How this helps the product now

- Supports stronger weighting and narrative justification for:
  - rebate leakage
  - spread pricing
  - specialty control
  - audit-right limitations
- Provides public benchmark clauses to compare against employer-unfavorable contract language.
- Improves credibility of executive outputs, especially deal diagnosis, control map, and audit implications.

## What is still missing

Public material helps calibration, but it does not make the system fully institutional-grade on its own.

Still needed:

- Real adjudicated commercial pharmacy claims
- More real PBM contracts with known negotiation outcomes
- Rebate/disclosure files or audit recoveries
- Employer-specific specialty routing and channel data

## Recommended next data acquisitions

Priority 1:

- Employer or advisor-provided commercial claims extracts
- Redacted PBM contracts with known "good deal / bad deal" outcomes

Priority 2:

- APCD request-based pharmacy claims from state databases
- Public payer audit recoveries tied to contract language

Priority 3:

- Rebate summaries, manufacturer administrative-fee disclosures, or audit workpapers

## Notes

- Some public sources block direct automated downloads. GAO was one of them in this environment.
- The existing public claims sample under `../public_claims/` is still useful for demo and product testing, but not for final institutional calibration.
