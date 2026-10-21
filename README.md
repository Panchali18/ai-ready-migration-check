# AI-Ready Migration Check

*Is your customer data ready for a new CRM, and for the AI on top of it?*

> **Demonstration only. All data is synthetic.** Tollmere Software is a fictional company. Any resemblance to a real business is unintended.

**Status:** in build. Synthetic data, ground truth and the 20 test questions are ready; the Snowflake build has not started.

## The problem

A growing B2B business moves its customers from an old CRM and a billing system into a new CRM, then switches on an AI assistant over that data. Dirty data moves with it:

- duplicates get imported
- free-text values don't fit the new system's dropdowns
- required fields are missing
- the AI gives wrong answers because one customer is split across several records

Teams usually find out after go-live.

## The scenario

**Tollmere Software** (fictional) is a 60-person software company based in the Netherlands. For over 20 years it has sold on-premise stock control and job-costing software to builders' merchants, plumbing suppliers and other trade distributors in the Netherlands, Belgium and Germany, through direct sales and a few resellers. Revenue comes from licences, annual maintenance and support contracts.

Tollmere is moving to subscriptions. Its customer records live in two places:

- **Old CRM** (sales): accounts, contacts, sites, reseller, sector
- **Billing system** (finance): who pays for maintenance and support, invoicing entity, payment terms

The same customer often appears differently in each: a head office in one, a branch in the other; a reseller's name instead of the end customer; legal forms written different ways (B.V., BV, GmbH, NV/SA); VAT numbers in mixed formats across three countries; free-text sectors typed over two decades in Dutch, German, French and English. The new CRM, and the AI assistant planned on top of it, need one clean record per customer.

## What the tool does

1. Checks whether customer data is ready for go-live, against required fields, formats and picklists the business defines.
2. Suggests fixes, with a human approving every change and every decision logged.
3. Proves the difference by asking the AI the same business questions before and after cleaning.

## Planned components

| # | Component | Built with |
|---|---|---|
| 1 | Synthetic data with planted errors and a ground-truth file | Python, Faker |
| 2 | Rule checks: required fields, formats, exact duplicates | SQL |
| 3 | AI checks: fuzzy duplicates across sources, picklist mapping, plain-English explanations | Snowflake Cortex AI functions |
| 4 | Review app: readiness scorecard, approval queue, decision log | Streamlit in Snowflake |
| 5 | Before/after proof: 20 business questions with known answers | Cortex Analyst |
| 6 | Read-only readiness agent | Cortex Agents, Cortex Search |
| 7 | Evaluation: precision and recall, accuracy before vs after, cost | SQL, Python |

## Design rules

- Rules where facts must be right; AI for fuzzy matching, mapping and explanations.
- The core checks are a repeatable workflow, not an agent: the same data produces the same flags.
- No fix is applied without human approval, and every decision is logged.
- The agent is read-only.
- Synthetic data only.

## What's in this repo so far

| Path | What it is |
|---|---|
| `docs/scope.md` | Decisions, user stories with acceptance criteria, assumptions and risks |
| `docs/target-schema.md` | What a customer record must look like before go-live: required fields, formats, blockers and warnings |
| `docs/business-questions.md` | The 20 sales-director questions asked before and after cleaning, and how answers are scored |
| `generator/` | Python scripts that create the synthetic data and calculate the correct answers |
| `data/` | Raw CRM and billing exports with planted errors, and the ground truth used for scoring (see `data/README.md`) |

## Not in scope

dbt, Power BI, real data or system connections, orders, products, invoices, sales pipeline, support tickets, cleaning individual contacts, parent-child account hierarchies (branches are rolled up into one customer), and the agent changing data.
