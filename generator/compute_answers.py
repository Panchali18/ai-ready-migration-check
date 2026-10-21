"""
Calculate the correct answer to each of the 20 business questions.

Correct answers come from the ground truth (data/ground_truth/entities.csv), never from an AI.

For comparison, it also answers each question the way a simple analysis of the RAW data would:
CRM and billing joined only where names match exactly, each raw record counted as it is, and dates
read only if they are in the expected dd-mm-yyyy format. This shows which questions dirty data
actually distorts. The five control questions give the same answer both ways.

Run:  python generator/compute_answers.py
Writes: data/ground_truth/answers.csv
"""

import csv
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
Q1_START, Q1_END = date(2027, 1, 1), date(2027, 3, 31)


def read(path):
    with open(ROOT / path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def eur(v):
    return f"€{v:,.0f}"


def pct(a, b):
    return f"{a / b:.1%}" if b else "n/a"


# ----------------------------------------------------------------------------
# Two views of the same customers, in one shape
# ----------------------------------------------------------------------------
def truth_view():
    rows = []
    for e in read("data/ground_truth/entities.csv"):
        rows.append({
            "name": e["customer_name"], "country": e["country"], "sector": e["sector"],
            "status": e["account_status"], "renewal": date.fromisoformat(e["renewal_date"]),
            "acv": float(e["annual_contract_value_eur"]) if e["annual_contract_value_eur"] else 0.0,
            "manager": e["account_manager"], "type": e["customer_type"], "reseller": e["reseller_name"],
            "contract": e["contract_type"],
        })
    return rows


def parse_raw_date(text):
    try:
        return datetime.strptime(text, "%d-%m-%Y").date()
    except ValueError:
        return None


def raw_view():
    """Each CRM record is a customer; billing values attach only on an exact name match.
    Billing records with no exact match still count towards revenue, with no other details."""
    crm = read("data/raw/crm_customers.csv")
    billing = read("data/raw/billing_customers.csv")
    by_name = defaultdict(list)
    for b in billing:
        by_name[b["legal_name"]].append(b)
    used = set()
    rows = []
    for c in crm:
        matches = by_name.get(c["customer_name"], [])
        acv = sum(float(b["annual_contract_value_eur"] or 0) for b in matches)
        for b in matches:
            used.add(b["billing_id"])
        rows.append({
            "name": c["customer_name"], "country": c["country"], "sector": c["sector"],
            "status": c["account_status"], "renewal": parse_raw_date(c["renewal_date"]), "acv": acv,
            "manager": c["account_manager"], "type": c["customer_type"], "reseller": c["reseller_name"],
            "contract": matches[0]["contract_type"] if matches else "",
        })
    for b in billing:
        if b["billing_id"] not in used:
            rows.append({"name": b["legal_name"], "country": b["country"], "sector": "", "status": "",
                         "renewal": None, "acv": float(b["annual_contract_value_eur"] or 0), "manager": "",
                         "type": "", "reseller": "", "contract": b["contract_type"]})
    return rows


# ----------------------------------------------------------------------------
# The 20 questions, each answered from a list of customer rows
# ----------------------------------------------------------------------------
def active(rows):
    return [r for r in rows if r["status"] == "Active"]


def renewing_q1(rows):
    return [r for r in active(rows) if r["renewal"] and Q1_START <= r["renewal"] <= Q1_END]


def top(rows, n, key="acv"):
    return sorted(rows, key=lambda r: -r[key])[:n]


def by_sector_revenue(rows):
    totals = Counter()
    for r in rows:
        totals[r["sector"] or "(no sector)"] += r["acv"]
    return totals


def q1(rows):
    return eur(sum(r["acv"] for r in renewing_q1(rows)))


def q2(rows):
    return "; ".join(f"{r['name']} ({eur(r['acv'])})" for r in top(renewing_q1(rows), 10))


def q3(rows):
    totals = Counter()
    for r in renewing_q1(rows):
        totals[r["manager"]] += r["acv"]
    m, v = totals.most_common(1)[0]
    return f"{m} ({eur(v)})"


def q4(rows):
    a = active(rows)
    return pct(sum(r["contract"] == "Subscription" for r in a), len(a))


def q5(rows):
    totals = by_sector_revenue(rows)
    known = {s: v for s, v in totals.items() if s in SECTORS}
    s = min(known, key=known.get)
    return f"{s} ({pct(known[s], sum(totals.values()))})"


def q6(rows):
    counts = Counter({c: 0 for c in ["Netherlands", "Germany", "Belgium"]})
    for r in active(rows):
        if r["sector"] == "Electrical wholesale":
            counts[r["country"]] += 1
    c = min(counts, key=counts.get)
    return f"{c} ({counts[c]} active customers)"


def q7(rows):
    totals = by_sector_revenue(rows)
    s = max(totals, key=totals.get)
    return f"{s} ({eur(totals[s])})"


def q8(rows):
    totals, counts = Counter(), Counter()
    for r in active(rows):
        if r["sector"] in SECTORS:
            totals[r["sector"]] += r["acv"]
            counts[r["sector"]] += 1
    avg = {s: totals[s] / counts[s] for s in counts}
    s = max(avg, key=avg.get)
    return f"{s} ({eur(avg[s])})"


def lost_between(rows, start, end):
    return [r for r in rows if r["status"] == "Lapsed" and r["renewal"] and start <= r["renewal"] <= end]


def q9(rows):
    return str(len(lost_between(rows, date(2026, 1, 1), date(2026, 12, 31))))


def q10(rows):
    lapsed, total = Counter(), Counter()
    for r in rows:
        if r["sector"] in SECTORS and r["status"] in ("Active", "Lapsed"):
            total[r["sector"]] += 1
            lapsed[r["sector"]] += r["status"] == "Lapsed"
    rate = {s: lapsed[s] / total[s] for s in total}
    s = max(rate, key=rate.get)
    return f"{s} ({rate[s]:.1%})"


def q11(rows):
    return str(sum(r["sector"] == "Builders' merchant"
                   for r in lost_between(rows, date(2025, 1, 1), date(2026, 12, 31))))


def q12(rows):
    return "; ".join(f"{r['name']} ({eur(r['acv'])})" for r in top(rows, 5))


def q13(rows):
    hits = [r for r in rows if r["name"] == "Van Gemert Bouwstoffen B.V."]
    return eur(sum(r["acv"] for r in hits)) if hits else "not found"


def q14(rows):
    be = [r for r in active(rows) if r["country"] == "Belgium"]
    r = top(be, 1)[0]
    return f"{r['manager']} (customer: {r['name']})"


def q15(rows):
    total = sum(r["acv"] for r in rows)
    return pct(sum(r["acv"] for r in rows if r["type"] == "Via reseller"), total)


def q16(rows):
    counts = Counter(r["reseller"] for r in rows if r["reseller"])
    s, n = counts.most_common(1)[0]
    return f"{s} ({n} customers)"


def q17(rows):
    maint = [r for r in renewing_q1(rows) if r["contract"] == "Maintenance"]
    return "; ".join(f"{r['name']} ({eur(r['acv'])})" for r in top(maint, 10))


def q18(rows):
    totals = Counter()
    for r in rows:
        if r["manager"]:
            totals[r["manager"]] += r["acv"]
    m, v = totals.most_common(1)[0]
    return f"{m} ({eur(v)})"


def q19(rows):
    total = sum(r["acv"] for r in rows)
    return pct(sum(r["acv"] for r in top(rows, 10)), total)


def q20(rows):
    return eur(sum(r["acv"] for r in rows))


SECTORS = ["Builders' merchant", "Plumbing & heating", "Electrical wholesale", "Industrial supplies", "Other"]

QUESTIONS = [
    (1, "Closing this quarter", "How much revenue is up for renewal this quarter?", q1),
    (2, "Closing this quarter", "Which are the 10 biggest renewals we have to close this quarter?", q2),
    (3, "Closing this quarter", "Which account manager has the most renewal revenue to close this quarter?", q3),
    (4, "Closing this quarter", "What share of our active customers have moved to subscription?", q4),
    (5, "Where we're not tapping enough", "Which sector brings in the smallest share of our revenue?", q5),
    (6, "Where we're not tapping enough", "In which country are we weakest in electrical wholesale?", q6),
    (7, "Where we're not tapping enough", "Which sector brings in the most revenue?", q7),
    (8, "Where we're not tapping enough", "Which sector has the highest average revenue per customer?", q8),
    (9, "Losing customers", "How many customers did we lose in 2026?", q9),
    (10, "Losing customers", "Which sector loses the highest share of its customers?", q10),
    (11, "Losing customers", "How many builders' merchants have we lost in the last two years?", q11),
    (12, "Our biggest customers", "Who are our top 5 customers by revenue?", q12),
    (13, "Our biggest customers", "How much does Van Gemert Bouwstoffen pay us per year?", q13),
    (14, "Our biggest customers", "Who is the account manager for our largest Belgian customer?", q14),
    (15, "Channels and the subscription move", "What share of revenue comes through resellers?", q15),
    (16, "Channels and the subscription move", "Which reseller brings us the most customers?", q16),
    (17, "Channels and the subscription move", "Which 10 largest maintenance customers renew this quarter?", q17),
    (18, "Team and risk", "Which account manager looks after the most revenue?", q18),
    (19, "Team and risk", "What share of our revenue comes from our top 10 customers?", q19),
    (20, "Team and risk", "What is our total annual revenue?", q20),
]
CONTROLS = {6, 9, 14, 15, 16}  # questions dirty data does not change

if __name__ == "__main__":
    truth, raw = truth_view(), raw_view()
    out = []
    for n, theme, question, fn in QUESTIONS:
        t, r = fn(truth), fn(raw)
        out.append({"id": n, "theme": theme, "question": question, "correct_answer": t,
                    "control": "yes" if n in CONTROLS else "no",
                    "raw_data_answer": r, "raw_differs": "yes" if t != r else "no"})
        flag = "same" if t == r else "DIFFERENT"
        print(f"Q{n:>2} [{flag:9s}] {question}\n     correct: {t}\n     raw:     {r}\n")
    with open(ROOT / "data/ground_truth/answers.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    differs = [o["id"] for o in out if o["raw_differs"] == "yes"]
    print(f"Raw data gives a different answer on {len(differs)} of 20 questions: {differs}")
    bad_controls = [o["id"] for o in out if o["control"] == "yes" and o["raw_differs"] == "yes"]
    print("Controls unaffected" if not bad_controls else f"Controls affected (need replacing): {bad_controls}")
