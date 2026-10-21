# Data

All data is synthetic, created by `generator/generate_data.py`. Every company, person, address and number is invented. Company names are built from common surnames and trade words, so a name may match a real business by coincidence; no real business is meant.

The generator uses a fixed seed, so running it again produces exactly the same files.

## Files

| File | What it is | Rows |
|---|---|---|
| `raw/crm_customers.csv` | Export from the old CRM, with planted errors | 2,000 |
| `raw/billing_customers.csv` | Export from the billing system, with planted errors | 1,500 |
| `ground_truth/entities.csv` | The true, clean record for each real customer | 1,930 |
| `ground_truth/record_links.csv` | Which real customer each raw record belongs to | 3,500 |
| `ground_truth/errors.csv` | Every planted error, with the raw and correct value | 552 |

The ground truth is used only to score the checks. It is never loaded where the AI checks or the agent can read it.

## Planted errors

552 errors on 552 records (15.8% of all rows). Each record carries at most one error, so every flag can be scored as right or wrong.

| Error type | Where | Count | Expected to be caught by |
|---|---|---|---|
| Name differs between CRM and billing | Billing | 120 | AI |
| Exact duplicate inside the CRM | CRM | 30 | Rules |
| Near-duplicate inside the CRM | CRM | 40 | AI |
| Sector typed in different words or languages | CRM | 120 | AI |
| Wrong sector (the company name gives the trade away) | CRM | 30 | AI |
| Missing VAT number (CRM-only customers) | CRM | 20 | Rules |
| Missing billing email | Billing | 20 | Rules |
| Missing renewal date | CRM | 20 | Rules |
| Invalid VAT number | Billing | 30 | Rules |
| Invalid postcode | CRM | 30 | Rules |
| Invalid email | CRM | 30 | Rules |
| Date written month-first (`mm/dd/yyyy`) | CRM | 30 | Rules flag, AI suggests the fix |
| Status contradicts renewal date | CRM | 30 | Rules |
| Demo customer split across billing records | Billing | 2 | AI |

## Traps (not errors: these must not be merged)

| Trap | Count | Why it matters |
|---|---|---|
| Look-alike companies: same trade name, different city, VAT number and legal form | 30 pairs | Catches a matcher that merges everything that looks similar |
| Customers billed through a reseller: the invoice address and billing email belong to the reseller, so several billing records share them | 30 customers, 4 resellers | Catches a duplicate check that treats a shared address as the same customer |

## The demo customer

The second-biggest customer by annual contract value (€182,000) has one CRM record but three billing records (€82,000, €58,000 and €42,000) under different spellings. In the raw billing data it drops out of the top 5; once the records are merged it is back at number 2.
