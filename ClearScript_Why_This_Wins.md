# ClearScript: The Case for Why This Wins

**PBM Disclosure Audit Engine for Self-Insured Employers**
*Confidential — March 2026*

---

## The 60-Second Version

The federal government just handed 33,000+ self-insured employers the legal right to audit their PBM for the first time in history. Nobody has built the tooling for them to actually do it. ClearScript is that tooling. The regulatory deadline is July 2026. There is no funded competitor building this exact product.

---

## 1. The Regulatory Forcing Function

This is not a "nice to have" market. The government is creating the demand on a hard timeline:

**HR 7148 / CAA 2026 (Signed into law February 3, 2026)**
- 100% rebate passthrough required — non-passthrough is now a prohibited transaction under ERISA 408(b)(2)(B)
- Unrestricted annual audit rights for self-insured employers — no scope limitations
- PBMs classified as ERISA Covered Service Providers for the first time
- Twice-yearly PBM reporting on drug spend, rebates, spread pricing, and fees

**DOL Proposed Rule (Published January 30, 2026)**
- PBMs must make semiannual fee disclosures to plan sponsors
- Required: direct compensation, indirect compensation (rebates, spread, fees), pharmacy network terms, formulary details
- $10,000/day penalty for non-compliance
- $100,000/day penalty for knowingly false information
- Unrestricted audit scope with a 10-business-day PBM response deadline

**FTC Enforcement (Active)**
- Express Scripts settlement (Feb 4, 2026): Ordered to stop preferring high-list-price drugs, delink compensation from drug prices
- Active litigation against CVS Caremark and OptumRx for anticompetitive rebating
- FTC staff report: Big 3 PBMs generated $7.3B in excess revenue (2017–2022) from specialty generic markups at affiliated pharmacies

**State-Level Momentum**
- All 50 states have passed PBM reform legislation
- California banned spread pricing (SB 41, effective Jan 1, 2026)
- State audits found: Ohio $224.8M/yr in spread pricing, Maryland $72M/yr, Kentucky $123.5M/yr
- Arkansas banned PBMs from owning pharmacies outright

**Why this matters:** Employers now have legal rights they've never had before. But rights without tools are useless. That's the gap.

---

## 2. The Money at Stake

PBM overcharging isn't theoretical. It's measured and documented:

- **$334 billion** in total manufacturer rebates flow through PBMs annually
- PBMs retain **20–50%** of rebates depending on contract structure
- **Spread pricing** (difference between what plan pays and pharmacy receives) generates hundreds of millions per state
- **CVS Caremark alone** had $615M in identified overcharges on federal health plans
- A typical **1,000-life employer** with $3–4M in pharmacy spend is leaving **$150K–$400K/year** on the table

**The J-Code rebate gap** (a discovery from our collaboration with Segal Consulting):
- 30% of Rx spend occurs in the J-code billing intersection (oncology, rheumatology, infusion therapies)
- J-code claims capture only ~5% in rebates vs. 24–30% on retail/mail NDC claims
- A single J-code can map to 5+ separate NDCs with different manufacturers and rebate rates
- PBMs have no incentive to enforce NDC-level billing because "100% passthrough" only applies to what's actually captured
- The passthrough can be technically compliant while the rebate was never captured in the first place
- For a $3–4M plan, the annual recoverable amount from enforcing NDC billing: **$150K–$360K**

**Reference: Segal audit example** — $1M in savings over 2 years for a single mid-market employer ($600K from AWP discount errors, $400K from rebate capture gaps).

---

## 3. The Product (Built and Working)

ClearScript is not a pitch deck. It's a working prototype with 13 functional modules:

### Compliance Layer
1. **Contract Intake & Parsing** — Upload PBM contracts, AI extracts key terms (rebate passthrough, spread caps, formulary clauses, audit rights, MAC pricing, termination), flags non-compliant language against DOL requirements
2. **Disclosure Analyzer** — Scores PBM fee disclosures for completeness against every DOL-required item, generates gap report with specific deficiencies
3. **Audit Request Generator** — Produces pre-formatted audit request letters citing specific regulatory provisions with automated deadline tracking
4. **Compliance Deadline Tracker** — Monitors 40+ federal and state-level PBM reform deadlines with 90/60/30-day alerts

### Audit Layer
5. **Semiannual Report Auditor** — Cross-references PBM reports against pharmacy claims and NADAC pricing to detect rebate and spread discrepancies
6. **Rebate Passthrough Tracker** — Follows every rebate dollar from manufacturer to PBM to plan, calculates leakage percentage
7. **Spread Pricing Detection** — Compares plan-paid vs. pharmacy-reimbursed per prescription, broken down by retail, mail-order, and specialty channels

### Full Platform
8. **Network Adequacy Analyzer** — Checks pharmacy coverage against employee zip codes, identifies phantom networks and geographic gaps
9. **Formulary Manipulation Detector** — Tracks mid-year formulary changes correlated with rebate incentives, flags suspicious brand-to-brand swaps
10. **Benchmarking Dashboard** — Anonymized peer comparison on cost per script, rebate passthrough rate, specialty spend, generic dispensing rate

### Advanced Modules
11. **NDC vs. J-Code Analysis** — Detects claims where J-code billing masks rebate-eligible NDCs (based on Segal consulting intelligence)
12. **Prior Auth Value Detector** — Analyzes PA rules at population level, outputs Keep/Remove/Modify with dollar impact per rule
13. **Provider Billing Anomaly Detection** — Uses free CMS Medicare utilization data to flag outlier billing patterns by specialty, geography, and procedure

### Tech Stack
- **Frontend:** Next.js 16, TypeScript, Tailwind CSS, Recharts
- **Backend:** Python FastAPI, Google Gemini 2.5 Flash (AI analysis), SQLite
- **Data:** NADAC API (real-time drug pricing from CMS), CMS NPPES pharmacy registry, CMS Medicare Provider Utilization PUF
- **Architecture:** API-first, modular, cloud-deployable

---

## 4. Why Zero Competitors Are Building This

| Company | What They Do | Why They're Not Us |
|---|---|---|
| **Xevant** | PBM analytics, VerX AI platform | Optimization, not compliance audit. Doesn't address DOL disclosure requirements. |
| **RxBenefits** ($51M raised) | Pharmacy benefits optimizer | PBM replacement model. Different buyer decision. |
| **Capital Rx** | Transparent PBM (JUDI platform) | They ARE a PBM. ClearScript audits PBMs. |
| **nirvanaHealth** | Real-time dashboards for plan vs. guarantee | Feature overlap but not purpose-built for CAA 2026/DOL mandates. |
| **Garner Health** ($1.2B valuation) | Provider quality scoring | Provider navigation. Different layer of the stack entirely. |
| **PlanSight** | Broker RFP/quoting workflow | Pre-sale tool. ClearScript is post-sale audit. Complementary. |
| **Gradient AI** ($56M Series C) | Insurance underwriting/claims prediction | Sells to insurers and underwriters, not employers. |
| **Segal / ARMSRx / 3 Axis** | Consulting firms | Manual audits. Can't scale. Natural partners, not competitors. |
| **Frier Levitt** | ERISA law firm | Legal practice, not software. Referral partner. |

**The structural reason nobody has built this:** Until February 2026, employers didn't have unrestricted audit rights. PBMs controlled the data, restricted audit scope in contracts, and refused methodologies. There was no regulatory mandate requiring disclosure. The product category literally didn't exist until the law changed.

---

## 5. The Market

**Primary buyer:** Self-insured employers with 200–5,000 employees
- ~33,000+ employers in this range
- ~65% of covered workers (118M enrollees) are in self-insured plans
- Decision maker: VP of Benefits, HR Director, CFO, or benefits committee

**Secondary channel:** Benefits brokers and consultants (~35,000 in the US)
- White-label ClearScript as part of their advisory offering
- Broker uses the tool, presents findings to their employer clients
- Revenue share model

**Tertiary channel:** ERISA litigation attorneys
- ClearScript as a litigation prevention tool for plan fiduciaries
- When prevention fails and violations are egregious → referral to ERISA counsel

**Pricing:** $30K–$50K/year per employer OR percentage of identified savings with $2,500/month floor

**TAM:** $990M–$1.65B (33,000 employers × $30–50K)

---

## 6. The Fiduciary Liability Angle

This is what makes employers move even when they're usually slow:

- ERISA plan fiduciaries have **personal liability** for monitoring service provider compensation
- If a PBM is earning undisclosed indirect compensation (spread, rebate retention, manufacturer payments), that's a **prohibited transaction** under ERISA 408(b)(2)
- The plan fiduciary — not the company, the individual — is personally exposed

**Active litigation proving the point:**
- **Stern v. JPMorgan Chase**: Employees sued alleging CVS Caremark marked up 366 generics by an average of 211%
- **Lewandowski v. J&J**: Dismissed on standing but appeal filed January 2026
- **Tiara Yachts ruling**: Established precedent for fiduciary breach claims related to PBM oversight

**The sales pitch writes itself:** "Your board has personal D&O liability for PBM oversight. The new law says your PBM has to disclose everything. Can you prove you actually looked at what they sent you?"

ClearScript gives plan fiduciaries documented evidence that they performed due diligence. Even when an audit finds nothing wrong, that's valuable — it proves the fiduciary looked.

---

## 7. Why Now (Timing)

| Date | Event | What It Means |
|---|---|---|
| Feb 3, 2026 | HR 7148 signed | Audit rights and 100% passthrough are law |
| Apr 15, 2026 | DOL comment period closes | Rule gets finalized shortly after |
| **Jul 2026** | **DOL rule takes effect (est.)** | **PBM disclosures begin. Audit cycle starts.** |
| 60 days after | Initial PBM disclosures due | ClearScript ingests first real disclosure data |
| Every 6 months | Semiannual disclosures | Recurring audit cycle = recurring SaaS revenue |
| Jan 1, 2028 | Full CAA 2026 provisions | Medicare Part D passthrough, twice-yearly reporting |

**The window:** Employers need this tooling before July 2026. Every month of delay is a month of unmonitored PBM spend. First mover captures the standard.

---

## 8. Go-to-Market

**Phase 1: Prove value (Now → June 2026)**
- Manual/semi-manual audits for 3–5 pilot employers to validate savings
- Every meeting = product feedback + case study
- Content marketing tied to regulatory deadlines (LinkedIn, DOL comment letters)

**Phase 2: Channel (July → December 2026)**
- White-label partnerships with 10 benefits brokers (exclusive territory + revenue share)
- Direct outreach to DOL Form 5500 self-insured employer list
- ERISA attorney referral network (litigation prevention positioning)

**Phase 3: Platform (2027)**
- Expand to full "CFO Health Plan Control Console"
- Pre-care commitment engine (member-facing)
- Provider compliance layer
- SPC-to-Excel automation (adjacent product wedge)

**Pipeline (active conversations):**
- Ken Coleman — PBM & Vendor Governance strategist (call scheduled)
- Nick Beckman (Segal) — Benefits consulting, active technical collaboration
- Julie Selesnick (JUDI Group) — ERISA litigation attorney, requested a call
- Jeremiah Shrack (Kincaid IQ) — PBM analytics, call scheduled Monday
- Matt Modafferi (Frier Levitt) — ERISA practice co-chair
- Brad Gallagher — scheduling
- Mark Pfleger (MBGH) — call booked
- Multiple broker/consultant outreach active (Holmes Murphy, ARMSRx, etc.)

---

## 9. The Thesis

PBM transparency is moving from advocacy to enforcement. The policy is written. The laws are signed. The penalties are set. What's missing is the operational infrastructure that turns legal rights into financial outcomes for employers.

Every other vendor relationship in business gets audited. PBMs have been the exception for 30 years because they controlled the data. That exception just ended.

ClearScript is the tool that makes the new law work.

**Conviction: 10/10.**
- Zero funded competitors building the exact same product
- Federal regulation creating forced buying on a hard deadline
- Massive dollar value ($150K–$400K/year per employer in recoverable savings)
- Buyers have budget, urgency, and personal liability exposure
- Working prototype with 13 modules, not a pitch deck
- Domain expert collaboration active (Segal Consulting)
- Multiple industry-validated conversations confirming product-market fit

---

## 10. What We Need

The product is built. The market is timed. The regulation is signed. What accelerates this:

1. **Domain expertise** — People who understand how employers actually make benefits decisions, what "decision-grade" output looks like, and how to translate PBM audit findings into board-level action
2. **Employer workflow validation** — Testing the product against real employer decision chains before launch
3. **Channel partnerships** — Broker and consultant relationships that can distribute ClearScript to their existing employer clients
4. **Advisory guidance** — Governance framework design, go-to-market messaging, and product-shaping strategy from people who've worked the employer side

The regulatory window is open. The question is who builds the standard before it closes.

---

*ClearScript is a product of Hikaflow, Inc.*
*Contact: Romir Jain — romirj@gmail.com*
