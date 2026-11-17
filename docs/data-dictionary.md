# Data dictionary

> Demonstration only. All data is synthetic. Tollmere Software is a fictional company.

What each table and field means, and the business definitions the AI assistant and the readiness agent must use. Each section stands on its own so it can be searched and quoted separately.

## Business definitions

### Today and this quarter
"Today" in the scenario is 1 January 2027. "This quarter" means 1 January to 31 March 2027. "The next 90 days" means 1 January to 31 March 2027.

### Customer
One real company that buys from Tollmere. A customer can appear as several records: once in the old CRM, once or more in billing, and sometimes twice in the CRM by mistake. After cleaning, each customer has exactly one record. Branches of the same company are rolled up into one customer.

### Active customer
A customer whose account status is Active: it currently pays for maintenance, support or a subscription. An active customer must have a renewal date in the future, an annual contract value and a contract type.

### Lapsed customer (lost customer)
A customer whose account status is Lapsed: it no longer pays Tollmere. For a lapsed customer, the renewal date is the date its contract ended. "Customers lost in 2026" means lapsed customers whose contract ended between 1 January and 31 December 2026.

### Revenue (annual contract value)
"Revenue" always means annual contract value: the amount an active customer pays per year, in euros, for maintenance and support or for a subscription. It comes from the billing system. Lapsed customers have no revenue. Revenue is not invoiced amounts or new sales; Tollmere's orders and invoices are not in this data.

### Renewal
The date an active customer's contract must be renewed. Renewals due this quarter are the revenue the sales team has to close this quarter.

### Contract type
How an active customer pays. **Maintenance** is the old model: a perpetual licence bought once, plus a yearly maintenance and support fee. **Subscription** is the new model Tollmere is moving to: one yearly fee covering the software and support. The share of active customers on subscription shows how far the move has got.

### Reseller
A partner company that sells Tollmere's software to a customer and is invoiced on the customer's behalf. For these customers, billing holds the reseller's name, invoice address and billing email. A reseller is never the same company as the customer it sells to, and its records are never merged with the customer's.

### Account manager
The Tollmere employee responsible for a customer. There are eight: Andrei Weihmann, Ayden Schellekens, Felicitas Dowerg, Floortje Heere, Imran Goyaerts van Waderle, Ivy van der Spaendonc, Karl Heinz Henschel and Liam Nek.

### Blocker and warning
A **blocker** is a problem that stops the business working after go-live: the new CRM rejects the record, invoices can't be sent, or AI answers go wrong. A **warning** is untidy but survivable. GO requires 0 open blockers and at least 95% of records passing all warning checks. These thresholds are set by the business and stored in a table.

## Source table: old CRM (`crm_customers`)

Export from Tollmere's old CRM, used by sales. About 2,000 rows. Holds every customer ever recorded, including lapsed customers that were never moved to the current billing system.

| Field | Meaning |
|---|---|
| `crm_id` | Record ID in the old CRM, such as CRM-00001. Not a customer ID: one customer can have two CRM records by mistake. |
| `customer_name` | Company name as sales typed it, usually with the legal form (B.V., GmbH, NV, SRL). |
| `street`, `postcode`, `city` | The customer's address. |
| `country` | Netherlands, Belgium or Germany. |
| `vat_number` | The customer's EU VAT number. |
| `sector` | The customer's trade. A free text box in the old CRM, so it holds values in Dutch, German, French and English. |
| `customer_type` | Direct, or Via reseller. |
| `reseller_name` | The reseller, if the customer buys through one. |
| `account_status` | Active or Lapsed. |
| `renewal_date` | Next renewal date for an active customer; contract end date for a lapsed one. Normal export format is `dd-mm-yyyy`. |
| `account_manager` | The Tollmere employee responsible for the customer. |
| `sales_contact_name`, `sales_contact_email` | The customer's main contact for sales. |
| `phone` | The customer's main phone number. |

## Source table: billing system (`billing_customers`)

Export from Tollmere's billing system, used by finance. About 1,500 rows. Holds only customers billed since the current billing system went live.

| Field | Meaning |
|---|---|
| `billing_id` | Record ID in billing, such as BIL-00001. One customer can have several billing records, for example one per branch. |
| `legal_name` | Company name as finance holds it. |
| `vat_number` | The customer's EU VAT number. |
| `bill_to_name` | The reseller invoiced on the customer's behalf; empty for direct customers. |
| `invoice_street`, `invoice_postcode`, `invoice_city` | Where invoices go. For reseller customers this is the reseller's address. |
| `country` | Country of the invoice address. |
| `billing_contact_email` | Where invoices are sent. For reseller customers this is the reseller's mailbox. |
| `annual_contract_value_eur` | Revenue per year in euros. Empty for lapsed customers. |
| `contract_type` | Maintenance or Subscription. Empty for lapsed customers. |

Billing has no account status. Status comes from the CRM once the two records are linked.

## Reference tables

| Table | What it holds |
|---|---|
| `picklist_values` | Allowed values for sector, country, customer type, account status and contract type |
| `readiness_thresholds` | The GO thresholds per check type (blocker or warning), set by the business |
| `account_managers` | The eight Tollmere employees who can own a customer |
| `quality_rules` | One row per rule in `docs/quality-rules.md`: ID, name, severity and check type (rule or AI) |

## Output tables

| Table | What it holds |
|---|---|
| `issues` | One row per problem found: record, rule ID, field, value found, severity, source (rule or AI) |
| `suggested_fixes` | The proposed fix for each issue, with the AI's explanation and, for duplicates, the similarity score |
| `review_decisions` | Every approve or reject decision: who, when, record, before and after values, source, decision and reason. Append-only. |
| `customers_clean` | One record per customer, built from the raw tables plus approved decisions. The raw tables are never changed. |

## Not available to the AI or the agent

The ground truth files in `data/ground_truth/` (true customer records, planted errors and correct answers) are used only to score results. They are never loaded where the AI checks, Cortex Analyst or the readiness agent can read them.
