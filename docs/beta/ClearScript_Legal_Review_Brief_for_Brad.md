# ClearScript — Legal Review Brief

## A. What ClearScript does

ClearScript is a web application that ingests a PBM contract (PDF or text) from a self-insured employer plan sponsor, runs the contract text through an OpenAI gpt-5.4-mini reasoning model with a structured extraction prompt, and returns a deal score, a tier-weighted risk inventory, an eleven-point audit-rights scorecard graded against gold-standard contract language, a list of compliance flags referencing ERISA, CAA 2021, and the DOL transparency rule, and a draft audit-request letter the plan sponsor can adapt.

The product also accepts an optional plan-document upload (SBC, SPD, EOC) and produces a cross-reference report identifying mismatches between what the contract obligates the PBM to do and what the plan document tells members. A separate disclosure-analyzer module ingests PBM-issued semiannual disclosure reports and grades them against the items the new DOL rule requires.

The audience is HR directors, benefits managers, in-house counsel, and CFOs at self-insured employers in the 200–5,000 employee range — roughly 30,000 employers in the US. A secondary audience is benefits brokers and consultants who advise multiple employers in that range.

## B. Data flow and retention

| Stage | What happens | Where it lives |
|---|---|---|
| Upload | User uploads a PBM contract PDF via the web frontend | TLS in transit; never written to client-device storage |
| Text extraction | `pdfplumber` extracts plain text inside the backend container | RAM only; PDF bytes discarded after extraction |
| AI analysis | Extracted text (truncated to ~12,000 characters) is sent to the OpenAI Chat Completions API | OpenAI processes under their enterprise API agreement: zero data retention, no training on inputs, deletion within 30 days |
| Storage | Returned structured analysis is persisted to SQLite on the backend | Encrypted at rest, US data center on Render, deleted on user request |
| Audit benchmarking | Local Python scoring against an in-house template | RAM only |
| Output delivery | Analysis is rendered to the frontend as JSON, optionally exported as a branded PDF | Generated on demand |

The frontend is hosted on Vercel and proxies API calls through to the backend on Render. Authentication is handled by Clerk. The backend is FastAPI on Python 3.13. Source code lives in a private GitHub repository.

PBM contracts themselves do not contain PHI. The product also has a claims-data upload endpoint that accepts a member-level pharmacy claims CSV — that path is disabled for beta participants and will not be exposed to anyone in the beta cohort. Once we re-enable it post-beta the data flow will need a separate review.

## C. Legal questions

### 1. Unauthorized practice of law

ClearScript's output cites statutes by section number and recommends specific actions ("renegotiate spread pricing to full pass-through before renewal," "expand audit rights to include rebate contracts"). Where is the line between informational analysis and legal advice? Is the existing user-facing language sufficient, or does the output itself need to be softened — for example, replacing "non-compliant" with "potentially inconsistent with [statute]" and replacing imperative recommendations with "considerations for counsel review"? I am willing to do a global find-and-replace through the prompts and the user-facing copy if that materially reduces UPL exposure.

### 2. Liability for analysis errors

If ClearScript flags Section 14.2 of a real contract as "a CAA 2021 Section 201 gag-clause violation" and that interpretation turns out to be wrong, what is our exposure? What carrier and coverage limits are typical for an errors-and-omissions policy on a healthcare-adjacent SaaS at this stage, and at what point in the customer pipeline should we bind it?

### 3. Marketing claims

Two phrases I use in marketing copy that I would like you to stress-test:

- "ClearScript identifies non-compliant PBM clauses." Is "non-compliant" defensible, or is that already a legal conclusion? Should I soften to "flagged for review" or "potentially inconsistent with [framework]"?
- "In under 60 seconds you get a deal score, an audit-rights scorecard, and a draft audit letter citing ERISA, CAA, and DOL provisions." Anything you would want pulled or qualified before this goes to plan sponsors?

### 4. PHI / HIPAA exposure

The backend has a `/api/claims/upload` endpoint that accepts a member-level pharmacy claims CSV. It is blocked from beta participants but exists in the codebase, and the underlying analysis features (spread pricing detection, rebate passthrough verification, network adequacy, formulary manipulation detection) all assume that data is available. Two questions:

- Once we re-enable claims uploads post-beta, what is the right legal posture — full Business Associate (BAA with each customer, HIPAA Security Rule compliance, audit logs, breach notification), or does a "de-identified data only" stance under the Safe Harbor method get us out of Business Associate status entirely?
- If we go the de-identified route, do we need to operationally enforce de-identification (reject uploads with prohibited fields, run a Safe Harbor checker on every upload), or is contractual representation in the Terms of Service sufficient?
