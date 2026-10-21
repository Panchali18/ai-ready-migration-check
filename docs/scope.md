# Scope: AI-Ready Migration Check

> Demonstration only. All data is synthetic. Tollmere Software is a fictional company.

## Scenario

Tollmere Software is a fictional 60-person software company in the Netherlands. It sells on-premise stock control and job-costing software to trade distributors in the Netherlands, Belgium and Germany, directly and through a few resellers. It is moving customers from an old CRM and a billing system into a new CRM, and plans to switch on an AI assistant over that data afterwards.

**Persona:** the migration lead, who owns go-live readiness and approves every fix.

## Decisions

| # | Topic | Decision |
|---|---|---|
| D1 | Revenue | Each billing customer has one annual contract value (yearly maintenance and support). "Revenue" in all questions means this figure. |
| D2 | Merging two records | Billing wins legal name, VAT number and invoice address. CRM wins sector, account manager and account status. |
| D3 | Contacts | Each customer keeps two contacts: a sales contact (from the CRM) and a billing contact (from billing). A merge keeps both. Individual contact cleaning is out of scope. |
| D4 | Resellers | A reseller is stored in its own field and is never merged with the customer it sells to. |
| D5 | Picklists | Sector, country, customer type (direct or via reseller), account status (active or lapsed) and contract type (maintenance or subscription). Legal form stays part of the company name. |
| D6 | GO threshold | GO when there are 0 open blockers and at least 95% of records pass the warning checks. Thresholds are stored in a table and can be changed. |
| D7 | Region | An EU region where the Cortex AI features are available, chosen on trial day 1. |
| D8 | Reviewers | One reviewer approves all fixes. No second sign-off. |
| D9 | Demo | Most fixes are approved in batches before recording; the recording shows the last batch turning NO-GO into GO. The README says so. |
| D10 | Renewal date | Required for active customers; a blocker if missing. A status that contradicts the renewal date is a warning. |
| D11 | Picklist values | A value not in the list is a blocker (the new CRM rejects it); an empty value is a warning. |
| D12 | Contract type | Each active customer is on maintenance (old model) or subscription (new model), held in billing. This tracks the move to subscriptions. |

## User stories

### A. Data setup

**US-01 Synthetic source data**
As the migration lead, I want realistic CRM and billing customer data with known errors, so that every check can be measured against a ground truth.
- About 2,000 CRM customers and 1,500 billing customers across the Netherlands, Belgium and Germany.
- Planted error types: fuzzy duplicates across sources, value variants (in Dutch, German, French and English), missing required fields, invalid formats (VAT number, postcode, email, date), wrong categories and status contradicting renewal date.
- Two kinds of traps that must not be merged: look-alike companies, and customers billed through a reseller.
- About 15% of records carry one error, with at least 20 of each error type. The full plan is in `data/README.md`.
- Every planted error is listed in a ground-truth file with record ID, error type and correct value.
- One high-value customer is split across records so it drops out of the top 5 by revenue.
- The generator uses a fixed seed, so it produces the same data every time.
- No duplicates are created except the planted ones, and no generated name matches a real company.

**US-02 Target schema and data dictionary**
As the migration lead, I want the new CRM's fields written down, so that "ready" has a fixed definition.
- Each field has a type, a required yes/no and a format rule. Picklist fields list their allowed values. See `docs/target-schema.md`.
- The dictionary is loaded into Snowflake so the agent can search it (US-12).

**US-03 Go/no-go thresholds**
As the head of sales operations, I want to set the pass thresholds, so that the business decides what "ready" means.
- Thresholds are stored per check type (blocker or warning), not hard-coded.
- Changing a threshold changes the scorecard without changing code.

### B. Checks

**US-04 Rule checks (SQL)**
As the migration lead, I want fixed checks for required fields, formats and exact duplicates, so that factual errors are caught the same way every time.
- Each flag records the record ID, rule ID, field, value and severity.
- Running the checks twice on the same data gives identical flags.
- VAT number and postcode formats are checked per country.

**US-05 Fuzzy duplicate detection (AI)**
As the migration lead, I want likely duplicates across CRM and billing found even when names and addresses differ, so that one customer becomes one record.
- Each candidate pair has a similarity score from 0 to 1. Only pairs above a threshold, tuned against the ground truth, go to review.
- No pair is merged automatically.
- Precision and recall are measured against the ground truth.

**US-06 Picklist mapping (AI)**
As the migration lead, I want free-text values mapped to the new picklists, so that they import cleanly.
- The output is always an allowed value or "no match". Code checks this, not the prompt.
- Each mapping keeps the original value.

**US-07 Explanation and suggested fix (AI)**
As the reviewer, I want a plain-English reason and a suggested fix for each issue, so that I can decide quickly.
- Structured output: issue type, explanation, suggested fix and the fields affected.
- Malformed output is rejected and logged, not shown.

### C. Review app (Streamlit in Snowflake)

**US-08 Readiness scorecard**
As the head of sales operations, I want a scorecard per table showing GO or NO-GO, so that I know whether we can go live.
- It shows the pass rate per check, the open blockers and warnings, and the overall status against the thresholds.
- It recalculates after approvals.

**US-09 Review queue**
As the reviewer, I want to approve or reject each suggested fix, singly or in a batch, so that nothing changes without a person agreeing.
- Approved fixes are written to cleaned tables; the raw data is never changed.
- A merge shows both records side by side and the values that will be kept (D2, D3).

**US-10 Decision log**
As an auditor, I want every decision recorded, so that changes can be traced.
- Each entry records who, when, the record, the before and after values, the source (rule or AI) and the decision.
- The log is append-only, and a rejection needs a reason.

### D. Proof and agent

**US-11 Before/after AI accuracy**
As the head of sales operations, I want the same 20 business questions asked of raw and cleaned data, so that I can see what dirty data does to AI answers.
- The 20 questions are written before any run. Their correct answers are calculated from the generator's own logic, not by the AI.
- Results are reported as X/20 on raw data and Y/20 on cleaned data, listing every question still wrong and why.

**US-12 Read-only readiness agent**
As a manager, I want to ask "Are we ready to go live?", "What's blocking us?" and "Why was this record flagged?", so that I don't need to read the dashboard.
- Number questions go to Cortex Analyst, and questions about rules or definitions go to Cortex Search.
- The agent's role can only read. A request to change data is declined.
- A test set of about 15 questions records the expected tool for each.

### E. Evaluation and cost

**US-13 Evaluation report**
- Precision and recall per error type, comparing rules, AI and both together.
- Before/after accuracy, and the agent's tool-choice accuracy.
- Credits per 1,000 records, and whether a smaller model is good enough.

**US-14 Cost control**
- X-Small warehouse, 60-second auto-suspend, and a resource monitor alerting at 50% and 80% of credits.
- Credits used are recorded after each work session.

## Assumptions

1. Customer level only, with two contacts per customer (D3).
2. Raw tables are never changed; cleaned tables are built from approved decisions. This is what makes the before/after comparison possible.
3. The Cortex features are available in the trial and in an EU region. To be checked on trial day 1, with these fallbacks:
   - No Cortex Agents: a readiness chat inside the Streamlit app calling Analyst and Search directly.
   - No Cortex Analyst: text-to-SQL with `AI_COMPLETE` and the semantic definitions in the prompt.
   - No Streamlit in Snowflake: Snowsight dashboards and an approval table.
4. Standard edition is enough.

## Risks

- **Accidental duplicates:** random names can repeat. Any duplicate that isn't planted counts as a false positive, so the generator checks for and removes them.
- **Circular evaluation:** if the AI wrote the ground truth or the 20 answers, the scores would mean nothing. Both come from the generator's logic or are written by hand.
- **Trial limits:** 30 days and about $400 of credits. Credits are tracked from day one.

## Out of scope

dbt, Power BI, real data or system connections, orders, products and invoices, cleaning individual contacts, and the agent changing data.
