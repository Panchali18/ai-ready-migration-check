# Business questions: before/after test

The same 20 questions are asked of the AI assistant on the raw data and on the cleaned data. They are written from a sales director's point of view.

The correct answers are calculated by `generator/compute_answers.py` from the ground truth, never by an AI. They are stored in `data/ground_truth/answers.csv`, which the AI never sees.

## Definitions

- **Today** in the scenario is 1 January 2027. **This quarter** is 1 January to 31 March 2027.
- **Revenue** means annual contract value: what an active customer pays per year for maintenance, support or subscription.
- **Lost** means a lapsed customer. For a lapsed customer, the renewal date is the date the contract ended.
- **Weakest** in a market means fewest active customers.

## Scoring

An answer is correct only if the name or number asked for is right **and** any figure given is within 1% of the correct value. Naming the right sector with the wrong revenue figure counts as wrong.

## The questions

| # | Theme | Question | Control |
|---|---|---|---|
| 1 | Closing this quarter | How much revenue is up for renewal this quarter? | |
| 2 | Closing this quarter | Which are the 10 biggest renewals we have to close this quarter? | |
| 3 | Closing this quarter | Which account manager has the most renewal revenue to close this quarter? | |
| 4 | Closing this quarter | What share of our active customers have moved to subscription? | |
| 5 | Where we're not tapping enough | Which sector brings in the smallest share of our revenue? | |
| 6 | Where we're not tapping enough | In which country are we weakest in electrical wholesale? | Yes |
| 7 | Where we're not tapping enough | Which sector brings in the most revenue? | |
| 8 | Where we're not tapping enough | Which sector has the highest average revenue per customer? | |
| 9 | Losing customers | How many customers did we lose in 2026? | Yes |
| 10 | Losing customers | Which sector loses the highest share of its customers? | |
| 11 | Losing customers | How many builders' merchants have we lost in the last two years? | |
| 12 | Our biggest customers | Who are our top 5 customers by revenue? | |
| 13 | Our biggest customers | How much does Van Gemert Bouwstoffen pay us per year? | |
| 14 | Our biggest customers | Who is the account manager for our largest Belgian customer? | Yes |
| 15 | Channels and the subscription move | What share of revenue comes through resellers? | Yes |
| 16 | Channels and the subscription move | Which reseller brings us the most customers? | Yes |
| 17 | Channels and the subscription move | Which 10 largest maintenance customers renew this quarter? | |
| 18 | Team and risk | Which account manager looks after the most revenue? | |
| 19 | Team and risk | What share of our revenue comes from our top 10 customers? | |
| 20 | Team and risk | What is our total annual revenue? | |

**Controls** are questions that dirty data does not change. If cleaning makes any of them wrong, the cleaning broke something.

## Expected effect of dirty data

A simple analysis of the raw data (CRM and billing joined only on exact name matches, dates read only in `dd-mm-yyyy`) gets a different answer on 15 of the 20 questions. The five controls give the same answer both ways.

This simulated baseline is a check that the questions are sensitive to the planted errors. The real before/after result is measured by asking the AI assistant in Snowflake.
