# Target schema: new CRM customer record

What every customer record must look like before go-live. Rule checks, AI checks and the scorecard all test against this.

**Blocker:** stops the business working after go-live (import fails, invoices can't be sent, AI answers go wrong). Must be 0 for GO.
**Warning:** untidy but survivable. At least 95% of records must pass for GO.

| Field | Required | Format or allowed values | If wrong |
|---|---|---|---|
| Customer name | Yes | Text | Blocker |
| Country | Yes | Netherlands, Belgium, Germany | Blocker |
| VAT number | Yes | NL: `NL` + 9 digits + `B` + 2 digits. BE: `BE0` + 9 digits. DE: `DE` + 9 digits | Blocker |
| Street, city | Yes | Text | Warning |
| Postcode | Yes | NL: `1234 AB`. BE: 4 digits. DE: 5 digits | Warning |
| Sector | Yes | Builders' merchant, Plumbing & heating, Electrical wholesale, Industrial supplies, Other | Value not in list: blocker. Empty: warning |
| Customer type | Yes | Direct, Via reseller | Value not in list: blocker. Empty: warning |
| Reseller name | If via reseller | Text | Blocker |
| Account status | Yes | Active, Lapsed | Value not in list: blocker. Empty: warning |
| Renewal date | If active | A valid date, `dd-mm-yyyy` | Blocker |
| Annual contract value | If active | Euros, greater than 0 | Blocker |
| Contract type | If active | Maintenance, Subscription | Value not in list: blocker. Empty: warning |
| Account manager | Yes | A Tollmere employee | Warning |
| Sales contact name and email | Yes | Valid email | Warning |
| Billing contact email | If active | Valid email | Blocker |
| Phone | No | International format (+31, +32, +49) | Warning |

## Cross-field check

| Check | If wrong |
|---|---|
| An active customer with a renewal date in the past, or a lapsed customer with one in the future | Warning |

## Where each field comes from

| Field | Old CRM | Billing | When both have it |
|---|---|---|---|
| Name, VAT number | Yes | Yes | Billing wins |
| Address | Yes | Invoice address | Billing wins (for reseller customers this is the reseller's address) |
| Sector, customer type, reseller, status, renewal date, account manager | Yes | No | CRM only |
| Sales contact | Yes | No | CRM only |
| Billing contact email, annual contract value, contract type | No | Yes | Billing only |
| Phone | Yes | No | CRM only |

Lapsed customers that were never moved to the current billing system exist only in the old CRM. Their VAT number comes from the CRM, and they need no billing email, contract value or contract type. For a lapsed customer, the renewal date is the date the contract ended.
