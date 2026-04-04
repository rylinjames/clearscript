# CMS DE-SynPUF PDE Public Claims Sample

- Source: https://downloads.cms.gov/files/DE1_0_2008_to_2010_Prescription_Drug_Events_Sample_18.zip
- Source file: `DE1_0_2008_to_2010_Prescription_Drug_Events_Sample_18.csv`
- Converted sample rows: 1500
- Output CSV: `cms_desynpuf_pde_sample18_clearscript.csv`

## Notes

- Base event rows come from the official CMS DE-SynPUF Prescription Drug Events public use file.
- `plan_paid` is derived from total Rx cost minus patient pay where possible.
- `pharmacy_reimbursed`, `awp`, `nadac_price`, `rebate_amount`, pharmacy identifiers, and channel labels are deterministic demo fields derived during conversion because the CMS source does not provide them directly.
- This file is suitable for ClearScript demos, benchmarking, and claims-backed UI testing. It is not raw adjudicated employer claims data.

## Summary

- Total plan paid: $93,747.50
- Total rebates: $11,818.05
- Total modeled spread: $4,269.02