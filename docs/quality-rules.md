# Quality rules

> Demonstration only. All data is synthetic. Tollmere Software is a fictional company.

Every check run before go-live. **R** rules are fixed SQL checks: the same data always gives the same flags. **A** checks use Cortex AI for matching, mapping and explanations; their suggestions always go to a person for approval. Each rule stands on its own so the readiness agent can quote it when asked why a record was flagged.

Field formats and severities come from `docs/target-schema.md`.

## Summary

| ID | Check | Applies to | Severity | Type |
|---|---|---|---|---|
| R01 | Customer name missing | CRM, billing | Blocker | Rule |
| R02 | Country missing or not allowed | CRM, billing | Blocker | Rule |
| R03 | VAT number missing | CRM, billing | Blocker | Rule |
| R04 | VAT number in wrong format | CRM, billing | Blocker | Rule |
| R05 | Street or city missing | CRM, billing | Warning | Rule |
| R06 | Postcode in wrong format | CRM, billing | Warning | Rule |
| R07 | Picklist value not allowed | CRM, billing | Blocker | Rule |
| R08 | Picklist value empty | CRM, billing | Warning | Rule |
| R09 | Reseller missing for a reseller customer | CRM | Blocker | Rule |
| R10 | Renewal date missing for an active customer | CRM | Blocker | Rule |
| R11 | Renewal date not a valid `dd-mm-yyyy` date | CRM | Blocker | Rule |
| R12 | Status contradicts renewal date | CRM | Warning | Rule |
| R13 | Contract value or contract type missing for an active customer | Linked record | Blocker | Rule |
| R14 | Billing email missing for an active customer | Billing | Blocker | Rule |
| R15 | Email in wrong format | CRM, billing | Billing email: blocker. Sales email: warning | Rule |
| R16 | Phone in wrong format | CRM | Warning | Rule |
| R17 | Account manager not a Tollmere employee | CRM | Warning | Rule |
| R18 | Exact duplicate in the CRM | CRM | Blocker | Rule |
| A01 | Billing record with no matching CRM customer | Billing | Blocker | AI |
| A02 | Possible duplicate inside the CRM | CRM | Blocker | AI |
| A03 | Sector typed in different words or languages | CRM | Blocker (fails R07) | AI |
| A04 | Sector doesn't fit the company | CRM | Warning | AI |
| A05 | Renewal date written month-first | CRM | Blocker (fails R11) | AI |

## Rule checks

### R01 Customer name missing
**Checks:** the customer or legal name is empty.
**Why it matters:** a record without a name can't be matched, imported or invoiced.
**Fix:** take the name from the matching record in the other system.

### R02 Country missing or not allowed
**Checks:** country is empty or not Netherlands, Belgium or Germany.
**Why it matters:** country decides the VAT and postcode rules and the invoice tax treatment.
**Fix:** take the country from the VAT number's country code.

### R03 VAT number missing
**Checks:** VAT number is empty in a record that needs one.
**Why it matters:** invoices to EU businesses must show the customer's VAT number, and VAT number is the strongest field for matching records across systems.
**Fix:** take it from the matching record in the other system; if neither has it, ask the account manager.

### R04 VAT number in wrong format
**Checks:** VAT number doesn't follow its country's pattern. Netherlands: `NL` + 9 digits + `B` + 2 digits (NL123456789B01). Belgium: `BE0` + 9 digits (BE0123456789). Germany: `DE` + 9 digits (DE123456789).
**Why it matters:** a wrong VAT number makes invoices invalid and breaks matching.
**Common causes:** a digit missing or extra, the country prefix left off, or the Dutch `B01` suffix missing.
**Fix:** take it from the matching record in the other system.

### R05 Street or city missing
**Checks:** street or city is empty.
**Why it matters:** an incomplete address is untidy but doesn't stop invoicing by email.
**Fix:** take it from the other system.

### R06 Postcode in wrong format
**Checks:** postcode doesn't follow its country's pattern. Netherlands: 4 digits, a space, 2 capital letters (1234 AB). Belgium: 4 digits. Germany: 5 digits.
**Common causes:** a German leading zero lost (01067 became 1067), Dutch letters missing or lower case.
**Fix:** take it from the other system, or correct the formatting.

### R07 Picklist value not allowed
**Checks:** sector, customer type, account status or contract type holds a value that isn't in the new CRM's list.
**Allowed values:** sector: Builders' merchant, Plumbing & heating, Electrical wholesale, Industrial supplies, Other. Customer type: Direct, Via reseller. Account status: Active, Lapsed. Contract type: Maintenance, Subscription.
**Why it matters:** the new CRM rejects the record on import.
**Fix:** map the value to an allowed one (see A03).

### R08 Picklist value empty
**Checks:** sector, customer type or account status is empty.
**Why it matters:** the record imports, but reports and AI answers by that field will be incomplete.

### R09 Reseller missing for a reseller customer
**Checks:** customer type is Via reseller but no reseller is named.
**Why it matters:** the customer's invoices go to the reseller; without it, billing can't be set up.

### R10 Renewal date missing for an active customer
**Checks:** an active customer has no renewal date.
**Why it matters:** a renewal can be missed, and the revenue drops out of "what we have to close this quarter".
**Fix:** ask the account manager.

### R11 Renewal date not a valid `dd-mm-yyyy` date
**Checks:** the renewal date isn't a real date in the old CRM's standard `dd-mm-yyyy` format.
**Why it matters:** the new CRM can't import it, or imports the wrong date.
**Common cause:** dates written with slashes month-first (see A05).

### R12 Status contradicts renewal date
**Checks:** an active customer's renewal date is in the past, or a lapsed customer's is in the future.
**Why it matters:** either the status or the date is wrong, so the customer is counted in the wrong place: as active revenue, or as lost.
**Fix:** the account manager confirms which is right.

### R13 Contract value or contract type missing for an active customer
**Checks:** once a CRM customer is linked to its billing record, an active customer has no annual contract value (or a value of 0 or less), or no contract type.
**Why it matters:** the customer's revenue disappears from every revenue figure.

### R14 Billing email missing for an active customer
**Checks:** an active customer's billing record has no billing contact email.
**Why it matters:** invoices can't be sent after go-live.

### R15 Email in wrong format
**Checks:** an email address isn't valid: no `@`, two `@`, a space, no domain ending, or a trailing dot.
**Severity:** blocker for the billing email (invoices bounce), warning for the sales contact email.

### R16 Phone in wrong format
**Checks:** a phone number doesn't start with +31, +32 or +49.

### R17 Account manager not a Tollmere employee
**Checks:** the account manager isn't in the list of eight Tollmere employees.

### R18 Exact duplicate in the CRM
**Checks:** two CRM records are identical in every field except the record ID.
**Why it matters:** the customer would be imported twice. Duplicates also double revenue when CRM and billing are joined, so totals come out too high.
**Fix:** keep one record, remove the other.

## AI checks

### A01 Billing record with no matching CRM customer
**Checks:** a billing record whose name doesn't exactly match any CRM customer. The AI compares it with CRM records by name, address and VAT number, gives each candidate a similarity score from 0 to 1, and proposes the best match above the threshold.
**Why it matters:** an unmatched billing record means revenue with no customer behind it. The customer drops out of rankings such as the top 5, and its revenue is wrongly attributed.
**Common causes:** legal form left off, abbreviations, capitals, accents written out (ü as ue), a typo, or a branch billed separately.
**Not a match:** a different VAT number usually means a different company, even with an identical trade name in another city. A billing record whose bill-to name is a reseller belongs to the reseller's customer, not the reseller.
**Fix:** a person approves the link; the billing record's values are attached to the CRM customer.

### A02 Possible duplicate inside the CRM
**Checks:** two CRM records with different but similar names that the AI scores above the similarity threshold.
**Why it matters:** the customer would be imported twice, and counts and revenue would be inflated.
**Not a duplicate:** two records with different VAT numbers and cities are usually different companies with the same family name.
**Fix:** a person approves the merge. The billing values win for name, VAT number and address; the CRM wins for sector, account manager and status; both contacts are kept.

### A03 Sector typed in different words or languages
**Checks:** a sector value that isn't in the picklist. The AI maps it to the allowed value with the same meaning, or returns "no match".
**Examples:** Bouwmaterialen, Baustoffhandel and building supplies all map to Builders' merchant. Sanitär and plomberie map to Plumbing & heating.
**Guardrail:** code checks that the AI's answer is an allowed value; anything else is treated as "no match" and goes to a person.

### A04 Sector doesn't fit the company
**Checks:** the sector is an allowed value, but the company name clearly points to another trade, such as "Bakker Sanitair B.V." tagged Electrical wholesale.
**Why it matters:** sector reports and AI answers by sector are wrong, but the record still imports.
**Fix:** a person confirms the sector the AI suggests.

### A05 Renewal date written month-first
**Checks:** a renewal date written with slashes, such as 07/16/2027, which fails R11. In this system, slash dates come from an old export that wrote the month first.
**Why it matters:** read the normal way, 04/01/2027 becomes 4 January instead of 1 April, moving the renewal into the wrong quarter.
**Fix:** the AI suggests the corrected `dd-mm-yyyy` date with its reasoning; a person approves it.

## How results are used

- Every issue is stored with its rule ID, so any flag can be traced back to the rule above.
- No AI suggestion is applied without a person approving it, and every decision is logged.
- The scorecard counts open blockers and the warning pass rate against the thresholds the business set.
