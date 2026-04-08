# ClearScript — Beta Program

## What ClearScript is

ClearScript is an AI-powered contract analyzer for self-insured employers. It reads pharmacy benefit management agreements, extracts the economic and governance terms that determine how much money the contract leaks, scores the deal against industry benchmarks, and produces a structured report that surfaces the risks, the leverage points, and the actions a plan sponsor can take into a renewal conversation.

The product is built around the new regulatory environment: HR 7148 (signed February 3, 2026), the DOL transparency rule (effective January 30, 2026), and the FTC's interim staff report on the Big 3 PBMs. Plan sponsors are about to receive an avalanche of disclosure data and have ten business days to act on audit findings — ClearScript exists so they don't walk into that conversation blind.

## How it works

A PBM contract is parsed by `pdfplumber`, sent through an OpenAI reasoning model with a structured extraction prompt tuned for PBM-specific clauses, and scored against a four-tier weighted risk model — economics, control, governance, administration. The full analysis takes roughly 60 seconds and is delivered both on screen and as a downloadable branded PDF report.

A single analysis includes:

- A deal score from 0 to 100 with a written diagnosis of where the contract advantages the PBM over the employer
- A top-risk inventory across rebate definitions, spread provisions, audit rights, MAC pricing, formulary clauses, gag clauses, termination penalties, dispute resolution, and statistical extrapolation rights
- An eleven-point audit-rights scorecard graded against gold-standard contract language
- A draft audit-request letter citing ERISA Section 404(a)(1), CAA 2021 Sections 201 and 204, the new DOL transparency rule, and HR 7148, with a 10-business-day response deadline pre-filled
- A redline starter pack identifying the clauses with the most renewal leverage
- An optional cross-reference report against a plan document (SBC, SPD, EOC) flagging mismatches between the contract and what members are actually told

## What to test

We are looking for honest reactions across the full experience, not just the analysis output:

- **Landing page.** Does the value proposition land in the first ten seconds? Is it clear who the product is for, what it does, and why now? Anything that reads as marketing fluff?
- **Sign-up flow.** How much friction is there from landing on the site to having an active account? Anything in the auth flow that feels off or unnecessary?
- **Onboarding.** When you first land in the dashboard, is it obvious where to go and what to do? Does the empty state guide you toward the first useful action?
- **Navigation.** Can you find the contract analyzer, the audit letter generator, the disclosure analyzer, and the compliance tracker without hunting? Is the sidebar grouping logical?
- **Contract analysis flow.** Is the upload experience clean? Does the wait feel reasonable? Does the results page lead with what matters most?
- **Analysis accuracy.** Did the model correctly identify the problem clauses in a contract you know well? Did it miss anything material? Did it flag anything that is not actually a problem?
- **Output clarity.** Could you hand the deal score and the written diagnosis to your CFO without a translation layer? Is the language plain enough for a benefits committee?
- **Action.** Is the draft audit letter actually ready to send, or does it need substantial editing? Would you be comfortable putting your name on it as written?
- **Coverage.** Are there contract terms, compliance areas, or PBM tactics that should be analyzed but are not? What is missing that you would expect to see?
- **Visual design and trust.** Does the interface feel trustworthy and professional? What about the output makes you more or less likely to rely on it?
- **Performance and reliability.** Anything slow, anything that broke, anything that left you confused about what was happening?
- **Pricing perception.** Setting aside that the beta is free, what does the product feel like it should cost? What would you be willing to pay annually for it if it worked exactly the way you wanted?
- **Comparison.** Have you used anything else — software, consultant, broker analysis, in-house spreadsheet — to evaluate a PBM contract? What did that approach do well or badly, and where does ClearScript fall short of it?
- **Likelihood to recommend.** Is there a colleague, peer, or industry contact you would forward ClearScript to after using it? If not, what would have to change for that to happen?

## Get started

- **Book a 15-minute kickoff call:** https://calendly.com/romirjain/30min
- **Or email** romirj@gmail.com **with the subject line** "ClearScript beta access" **and we will schedule the kickoff and send credentials within 24 hours**

---

**ClearScript — Plan Intelligence for Self-Insured Employers**
Romir Jain · romirj@gmail.com · https://calendly.com/romirjain/30min
