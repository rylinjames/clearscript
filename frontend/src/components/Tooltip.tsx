"use client";

import { useState } from "react";
import { HelpCircle } from "lucide-react";

interface TooltipProps {
  term: string;
  children: React.ReactNode;
}

const glossary: Record<string, string> = {
  "spread pricing": "The difference between what the PBM charges the plan and what it pays the pharmacy. PBMs pocket the spread as hidden profit.",
  "NADAC": "National Average Drug Acquisition Cost — CMS benchmark for what pharmacies actually pay for drugs, updated weekly.",
  "rebate passthrough": "Rebates are discounts from drug manufacturers. '100% passthrough' means all rebates go to the plan, not retained by the PBM.",
  "NDC": "National Drug Code — an 11-digit identifier for every drug product. Used to match claims to rebate-eligible drugs.",
  "J-code": "HCPCS billing codes for physician-administered drugs. When used instead of NDCs, rebate eligibility can be masked.",
  "prior authorization": "A requirement to get PBM approval before a drug is covered. PA rules can be clinically appropriate or used to steer toward preferred drugs.",
  "gold carding": "Exempting high-performing providers from prior authorization requirements based on historical approval rates.",
  "formulary": "The list of drugs covered by the plan, organized into tiers with different cost-sharing levels.",
  "AWP": "Average Wholesale Price — the 'sticker price' for drugs. Often used as a benchmark in PBM contracts (e.g., AWP-15%).",
  "MAC": "Maximum Allowable Cost — the ceiling price a PBM will reimburse for generic drugs. MAC lists are proprietary and opaque.",
  "specialty pharmacy": "High-cost drugs for complex conditions (biologics, oncology). ~2% of claims, 50%+ of total spend.",
  "ERISA": "Employee Retirement Income Security Act — federal law governing employer health plans. Creates fiduciary duties for plan sponsors.",
  "408(b)(2)": "ERISA section requiring service provider (PBM) compensation to be reasonable and adequately disclosed. Violations are prohibited transactions.",
  "CAA 2026": "Consolidated Appropriations Act provisions giving employers unrestricted PBM audit rights and requiring 100% rebate passthrough.",
  "fiduciary": "A person or entity legally required to act in the best interest of plan participants. Employer plan sponsors are ERISA fiduciaries.",
  "PBM": "Pharmacy Benefit Manager — the middleman between drug manufacturers, pharmacies, and health plans. Manages the drug benefit.",
  "self-insured": "When an employer pays claims directly rather than buying insurance. The employer bears the financial risk and has direct PBM contracts.",
  "network adequacy": "Whether the plan's pharmacy network provides sufficient geographic access for all plan members.",
  "DOL": "Department of Labor — federal agency that enforces ERISA and oversees employer health plan compliance.",
};

export default function Tooltip({ term, children }: TooltipProps) {
  const [show, setShow] = useState(false);
  const definition = glossary[term.toLowerCase()];

  if (!definition) return <>{children}</>;

  return (
    <span
      className="relative inline-flex items-center gap-1 cursor-help"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children}
      <HelpCircle className="w-3.5 h-3.5 text-gray-400" />
      {show && (
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-xl z-50 leading-relaxed">
          <span className="font-semibold text-emerald-400">{term}</span>
          <br />
          {definition}
          <span className="absolute top-full left-1/2 -translate-x-1/2 -mt-px border-4 border-transparent border-t-gray-900" />
        </span>
      )}
    </span>
  );
}
