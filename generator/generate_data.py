"""
Generate synthetic CRM and billing customer data for Tollmere Software (fictional).

Demonstration only. Every company, person, address and number is invented.

Run:  python generator/generate_data.py
The fixed SEED means every run produces exactly the same files.

Outputs (in data/):
  raw/crm_customers.csv          old CRM export (about 2,000 rows)
  raw/billing_customers.csv      billing system export (about 1,500 rows)
  ground_truth/entities.csv      the true, clean record for every real customer
  ground_truth/record_links.csv  which real customer each raw record belongs to
  ground_truth/errors.csv        every planted error, with the correct value
"""

import csv
import random
import re
import unicodedata
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

SEED = 42
AS_OF = date(2027, 1, 1)  # "today" inside the scenario, fixed so results never drift

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
TRUTH = ROOT / "data" / "ground_truth"

# ----------------------------------------------------------------------------
# Plan: how many records and how many of each planted error
# ----------------------------------------------------------------------------
N_LINKED = 1498        # customers in both CRM and billing
N_CRM_ONLY = 432       # lapsed customers that only exist in the old CRM
N_LOOKALIKE_PAIRS = 30 # trap: different companies with near-identical names
N_RESELLER = 30        # trap: billed through a reseller, so invoice details are the reseller's

PLAN = {
    "name_variant_across_sources": 120,
    "exact_duplicate_in_crm": 30,
    "near_duplicate_in_crm": 40,
    "sector_free_text": 120,
    "wrong_sector": 30,
    "missing_vat_number": 20,
    "missing_billing_email": 20,
    "missing_renewal_date": 20,
    "invalid_vat_number": 30,
    "invalid_postcode": 30,
    "invalid_email": 30,
    "date_format_mixup": 30,
    "status_renewal_contradiction": 30,
}

COUNTRIES = [("Netherlands", 0.50), ("Germany", 0.30), ("Belgium", 0.20)]
SECTORS = ["Builders' merchant", "Plumbing & heating", "Electrical wholesale",
           "Industrial supplies", "Other"]
SECTOR_WEIGHTS = [0.32, 0.26, 0.18, 0.16, 0.08]

# Words that go into company names, so a reader (or the AI) can tell the trade
NAME_WORDS = {
    "Builders' merchant": {"nl": ["Bouwmaterialen", "Bouwcentrum", "Bouwstoffen"],
                           "de": ["Baustoffe", "Baucenter", "Baustoffhandel"],
                           "fr": ["Matériaux", "Matériaux de Construction"]},
    "Plumbing & heating": {"nl": ["Sanitair", "Installatietechniek", "Verwarming"],
                           "de": ["Haustechnik", "Sanitär", "Heizungsbedarf"],
                           "fr": ["Sanitaire", "Chauffage"]},
    "Electrical wholesale": {"nl": ["Elektro", "Elektrotechniek", "Elektrogroothandel"],
                             "de": ["Elektro", "Elektrogroßhandel", "Elektrotechnik"],
                             "fr": ["Électro", "Électricité"]},
    "Industrial supplies": {"nl": ["Techniek", "Industrie", "Technische Handel"],
                            "de": ["Industriebedarf", "Technik", "Werkzeughandel"],
                            "fr": ["Industrie", "Fournitures Techniques"]},
    "Other": {"nl": ["Groep", "Handel"], "de": ["Handel", "Gruppe"],
              "fr": ["Commerce", "Groupe"]},
}

# How staff typed the sector into the old CRM's free text box
SECTOR_FREE_TEXT = {
    "Builders' merchant": {"nl": ["Bouwmaterialen", "bouwmaterialenhandel", "bouwmat.", "Bouwhandel"],
                           "de": ["Baustoffhandel", "Baustoffe", "Baustoff-Fachhandel"],
                           "fr": ["Matériaux de construction", "négoce matériaux"],
                           "en": ["building supplies", "Builders merchants", "BUILDERS MERCHANT"]},
    "Plumbing & heating": {"nl": ["Sanitair", "sanitair & verwarming", "installatietechniek"],
                           "de": ["Sanitär", "SHK-Großhandel", "Heizung/Sanitär"],
                           "fr": ["Sanitaire et chauffage", "plomberie"],
                           "en": ["plumbing", "Plumbing/heating", "HVAC & plumbing"]},
    "Electrical wholesale": {"nl": ["Elektrotechniek", "elektro groothandel", "Elektra"],
                             "de": ["Elektrogroßhandel", "Elektro"],
                             "fr": ["Électricité", "matériel électrique"],
                             "en": ["electrical", "Elec. wholesale"]},
    "Industrial supplies": {"nl": ["Technische groothandel", "industriële benodigdheden"],
                            "de": ["Industriebedarf", "Technischer Handel"],
                            "fr": ["Fournitures industrielles"],
                            "en": ["industrial", "MRO supplies"]},
    "Other": {"nl": ["Diversen"], "de": ["Sonstiges"], "fr": ["Divers"], "en": ["misc"]},
}

LEGAL_FORMS = {"Netherlands": ["B.V.", "B.V.", "B.V.", "V.O.F."],
               "Germany": ["GmbH", "GmbH", "GmbH & Co. KG", "KG"],
               "Belgium-nl": ["BV", "NV"], "Belgium-fr": ["SRL", "SA"]}

FR_BE_CITIES = ["Liège", "Namur", "Charleroi", "Mons", "Tournai", "Wavre", "Arlon",
                "Verviers", "Nivelles", "La Louvière", "Ottignies", "Huy"]
TLD = {"Netherlands": "nl", "Germany": "de", "Belgium": "be"}
PHONE_PREFIX = {"Netherlands": "+31", "Germany": "+49", "Belgium": "+32"}
BILLING_MAILBOX = {"nl": ["facturen", "administratie", "crediteuren"],
                   "de": ["rechnung", "buchhaltung", "rechnungswesen"],
                   "fr": ["factures", "comptabilite"]}

rng = random.Random(SEED)
fakers = {}
for loc in ["nl_NL", "nl_BE", "fr_BE", "de_DE"]:
    fakers[loc] = Faker(loc)
    fakers[loc].seed_instance(SEED)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def strip_accents(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def name_key(name):
    """Name without legal form, punctuation or accents: used to stop accidental duplicates."""
    text = strip_accents(name.lower())
    text = re.sub(r"\b(b\.?v\.?|v\.?o\.?f\.?|gmbh( & co\.? kg)?|kg|nv|bv|srl|sa)\b", "", text)
    return re.sub(r"[^a-z0-9]", "", text)


def cap_surname(s):
    return s[0].upper() + s[1:]


PREFIXES = {"van", "de", "der", "den", "ten", "ter", "te", "von", "le", "la", "du", "'t", "in", "op"}


# Surnames that are also well-known brands in this trade: never used
BRAND_NAMES = {"legrand", "bosch", "siemens", "philips", "wurth", "würth", "hornbach", "gamma", "praxis", "otto",
               "miele", "vaillant", "viessmann", "grohe", "hager", "schneider", "rexel", "sonepar", "obi", "bauhaus",
               "hansgrohe", "kaldewei", "buderus", "stiebel", "eltron", "geberit", "makita", "hilti", "fischer",
               "knauf", "rockwool", "wienerberger", "saint", "dyckerhoff", "heidelberg", "lidl", "aldi", "metro"}


def surname(fk):
    """A realistic-looking surname: short, and at most a prefix plus one name (e.g. Van Dijk)."""
    for _ in range(100):
        s = fk.last_name()
        parts = s.split()
        prefixes_ok = all(p.lower() in PREFIXES for p in parts[:-1]) and parts[-1].lower() not in BRAND_NAMES
        if len(parts) <= 3 and prefixes_ok and 3 <= len(parts[-1]) <= 11 and parts[-1][0].isupper():
            return cap_surname(s)
    return cap_surname(s)


def slug(text):
    return re.sub(r"[^a-z0-9]", "", strip_accents(text.lower()))


def nl_postcode():
    return f"{rng.randint(1000, 9999)} {rng.choice('ABCDEGHJKLMNPRSTVWXZ')}{rng.choice('ABCDEGHJKLMNPRSTVWXZ')}"


def postcode_for(country):
    if country == "Netherlands":
        return nl_postcode()
    if country == "Belgium":
        return str(rng.randint(1000, 9999))
    return f"{rng.randint(1067, 99998):05d}"


def vat_for(country):
    if country == "Netherlands":
        return f"NL{rng.randint(10**8, 10**9 - 1)}B{rng.randint(1, 99):02d}"
    if country == "Belgium":
        return f"BE0{rng.randint(10**8, 10**9 - 1)}"
    return f"DE{rng.randint(10**8, 10**9 - 1)}"


def phone_for(country):
    return f"{PHONE_PREFIX[country]} {rng.randint(10, 99)} {rng.randint(100, 999)} {rng.randint(1000, 9999)}"


def fmt_date(d):
    return d.strftime("%d-%m-%Y")  # the old CRM's normal export format


def name_variant(name, entity):
    """A different spelling of the same company, as another system might hold it."""
    tricks = [
        lambda n: re.sub(r"\s(B\.V\.|BV|GmbH|NV|SRL|SA|V\.O\.F\.|KG)$", "", n),  # drop legal form
        lambda n: n.replace("B.V.", "BV").replace("V.O.F.", "VOF").replace("GmbH & Co. KG", "GmbH & Co KG"),
        lambda n: re.sub(r"(Bouwmaterialen|Installatietechniek|Elektrotechniek|Baustoffhandel|Elektrogroßhandel)",
                         lambda m: m.group(1)[:6] + ".", n),  # abbreviate the trade word
        lambda n: n.upper(),
        lambda n: n.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
                   .replace("é", "e").replace("è", "e"),
        lambda n: n.replace(" & ", " en " if entity["lang"] == "nl" else " und " if entity["lang"] == "de" else " et "),
        lambda n: re.sub(r"^(Van|De|Von) (\w)", lambda m: m.group(1) + m.group(2), n),  # Van Dijk -> VanDijk
        lambda n: typo(n),
        lambda n: f"{n} - {entity['city']}",
    ]
    for _ in range(50):
        picked = rng.sample(tricks, rng.choice([1, 1, 2]))
        out = name
        for t in picked:
            out = t(out)
        if out != name and name_key(out) != "" :
            return out
    return typo(name)


def typo(text):
    letters = [i for i, c in enumerate(text) if c.isalpha()]
    i = rng.choice(letters[1:-1])
    if rng.random() < 0.5:
        return text[:i] + text[i + 1:]                       # dropped letter
    return text[:i] + text[i + 1] + text[i] + text[i + 2:]   # swapped letters


# ----------------------------------------------------------------------------
# 1. The real customers (the ground truth)
# ----------------------------------------------------------------------------
used_keys = set()


def new_company(country=None, sector=None, forced_base=None):
    country = country or rng.choices([c for c, _ in COUNTRIES], [w for _, w in COUNTRIES])[0]
    if country == "Belgium":
        loc = "nl_BE" if rng.random() < 0.7 else "fr_BE"
    else:
        loc = {"Netherlands": "nl_NL", "Germany": "de_DE"}[country]
    lang = loc[:2]
    fk = fakers[loc]
    sector = sector or rng.choices(SECTORS, SECTOR_WEIGHTS)[0]
    city = rng.choice(FR_BE_CITIES) if loc == "fr_BE" else fk.city()
    legal_key = "Belgium-nl" if loc == "nl_BE" else "Belgium-fr" if loc == "fr_BE" else country

    for _ in range(200):
        if forced_base:
            base = forced_base
        else:
            family = surname(fk)
            if rng.random() < 0.75:
                base = f"{family} {rng.choice(NAME_WORDS[sector][lang])}"
            else:
                partner = surname(fk)
                base = f"{family} & {partner}" if rng.random() < 0.6 else f"{family} & Zonen" if lang == "nl" else f"{family} & Söhne" if lang == "de" else f"{family} & Fils"
        name = f"{base} {rng.choice(LEGAL_FORMS[legal_key])}"
        key = name_key(name)
        if forced_base or key not in used_keys:
            break
    used_keys.add(key)

    contact_first, contact_last = fk.first_name(), fk.last_name()
    domain = f"{slug(base)[:30]}.{TLD[country]}"
    return {
        "name": name, "base": base, "family": base.split(" & ")[0].rsplit(" ", 1)[0] if " & " not in base else base.split(" & ")[0], "country": country, "lang": lang, "city": city,
        "street": fk.street_address() if loc != "fr_BE" else f"Rue {surname(fk)} {rng.randint(1, 180)}",
        "postcode": postcode_for(country), "vat": vat_for(country), "sector": sector,
        "phone": phone_for(country),
        "sales_contact_name": f"{contact_first} {contact_last}",
        "sales_contact_email": f"{slug(contact_first)}.{slug(contact_last)}@{domain}",
        "billing_email": f"{rng.choice(BILLING_MAILBOX[lang])}@{domain}",
        "has_trade_word": any(w in name for w in NAME_WORDS[sector][lang]),
    }


account_managers = [f"{fakers['nl_NL'].first_name()} {fakers['nl_NL'].last_name()}" for _ in range(5)] + \
                   [f"{fakers['de_DE'].first_name()} {fakers['de_DE'].last_name()}" for _ in range(3)]

resellers = []
for country, label in [("Netherlands", "Software Partners"), ("Netherlands", "ICT Diensten"),
                       ("Germany", "Softwarepartner"), ("Belgium", "IT Solutions")]:
    r = new_company(country=country, sector="Other")
    r["base"] = f"{r['family']} {label}"
    r["name"] = f"{r['base']} {'GmbH' if country == 'Germany' else 'B.V.' if country == 'Netherlands' else 'BV'}"
    r["billing_email"] = f"{rng.choice(BILLING_MAILBOX[r['lang']])}@{slug(r['base'])}.{TLD[country]}"
    resellers.append(r)

entities = []


def add_entity(company, in_billing, status):
    e = dict(company)
    e["entity_id"] = f"E{len(entities) + 1:05d}"
    e["in_billing"] = in_billing
    e["status"] = status
    e["customer_type"] = "Direct"
    e["reseller"] = None
    e["account_manager"] = rng.choice(account_managers)
    if status == "Active":
        e["renewal"] = AS_OF + timedelta(days=rng.randint(5, 360))
        e["acv"] = int(min(max(rng.lognormvariate(9.0, 0.7), 1200), 90000) // 10 * 10)
    else:
        e["renewal"] = AS_OF - timedelta(days=rng.randint(30, 1500))
        e["acv"] = None
    e["role"] = "normal"
    entities.append(e)
    return e


# Linked customers (in both systems)
for _ in range(N_LINKED - 2 * N_LOOKALIKE_PAIRS):
    add_entity(new_company(), True, "Active" if rng.random() < 0.92 else "Lapsed")

# Trap: look-alike pairs. Same trade name, different company (city, VAT, legal form)
for _ in range(N_LOOKALIKE_PAIRS):
    a = add_entity(new_company(sector=rng.choice(SECTORS[:4])), True, "Active")
    b = add_entity(new_company(country=a["country"], sector=a["sector"], forced_base=a["base"]), True, "Active")
    if b["name"] == a["name"]:
        b["name"] = a["base"]  # no legal form at all
    a["role"] = b["role"] = "lookalike_trap"
    a["twin"], b["twin"] = b["entity_id"], a["entity_id"]

# CRM-only: lapsed customers never moved to the current billing system
for _ in range(N_CRM_ONLY):
    add_entity(new_company(), False, "Lapsed")

# Top customers: set contract values so the top 5 is clear
linked_active = [e for e in entities if e["in_billing"] and e["status"] == "Active" and e["role"] == "normal"]
rng.shuffle(linked_active)
top_values = [214000, 182000, 168000, 151000, 139000, 126000, 118000, 109000, 101000, 96000]
for e, v in zip(linked_active, top_values):
    e["acv"] = v
demo = linked_active[1]          # the second-biggest customer, split in billing for the demo
demo["role"] = "demo_split"

# Trap: customers billed through a reseller
for e in linked_active[len(top_values):len(top_values) + N_RESELLER]:
    e["customer_type"] = "Via reseller"
    e["reseller"] = rng.choice(resellers)
    e["role"] = "reseller_trap"

# Contract type: part of the move to subscriptions. Uses its own random stream so
# adding it changed no other value. Larger customers are slower to move.
contract_rng = random.Random(SEED + 1)
for e in entities:
    if e["status"] != "Active":
        e["contract_type"] = None
    else:
        p_sub = 0.10 if e["acv"] >= 50000 else 0.30
        e["contract_type"] = "Subscription" if contract_rng.random() < p_sub else "Maintenance"
demo["contract_type"] = "Maintenance"

# ----------------------------------------------------------------------------
# 2. Clean raw records (before errors are planted)
# ----------------------------------------------------------------------------
crm, billing, links, errors = [], [], [], []


def crm_row(e):
    return {
        "customer_name": e["name"], "street": e["street"], "postcode": e["postcode"], "city": e["city"],
        "country": e["country"], "vat_number": e["vat"], "sector": e["sector"],
        "customer_type": e["customer_type"], "reseller_name": e["reseller"]["name"] if e["reseller"] else "",
        "account_status": e["status"], "renewal_date": fmt_date(e["renewal"]),
        "account_manager": e["account_manager"], "sales_contact_name": e["sales_contact_name"],
        "sales_contact_email": e["sales_contact_email"], "phone": e["phone"],
        "_entity": e,
    }


def billing_row(e):
    r = e["reseller"]
    return {
        "legal_name": e["name"], "vat_number": e["vat"],
        "bill_to_name": r["name"] if r else "",
        "invoice_street": r["street"] if r else e["street"],
        "invoice_postcode": r["postcode"] if r else e["postcode"],
        "invoice_city": r["city"] if r else e["city"],
        "country": r["country"] if r else e["country"],
        "billing_contact_email": r["billing_email"] if r else e["billing_email"],
        "annual_contract_value_eur": e["acv"] if e["acv"] is not None else "",
        "contract_type": e["contract_type"] or "",
        "_entity": e,
    }


for e in entities:
    crm.append(crm_row(e))
    if e["in_billing"] and e["role"] != "demo_split":
        billing.append(billing_row(e))

# Demo customer: one CRM record, but billing holds three records that split its contract value
parts = [(82000, demo["name"]), (58000, name_variant(demo["name"], demo)),
         (42000, f"{demo['base']} - {fakers['nl_NL'].city() if demo['lang'] == 'nl' else demo['city']}")]
for value, name in parts:
    row = billing_row(demo)
    row["legal_name"], row["annual_contract_value_eur"] = name, value
    row["_demo"] = True
    billing.append(row)


def log_error(kind, source, row, field, raw, correct):
    errors.append({"error_type": kind, "source": source, "_row": row, "field": field,
                   "raw_value": raw, "correct_value": correct, "entity_id": row["_entity"]["entity_id"]})


def eligible_crm(pred=lambda e: True):
    return [r for r in crm if r["_entity"]["role"] == "normal" and not r.get("_touched") and pred(r["_entity"])]


def eligible_billing(pred=lambda e: True):
    return [r for r in billing if r["_entity"]["role"] == "normal" and not r.get("_touched") and pred(r["_entity"])]


def take(pool, n):
    picked = rng.sample(pool, n)
    for r in picked:
        r["_touched"] = True
    return picked


# ----------------------------------------------------------------------------
# 3. Plant errors (each record gets at most one, so the ground truth stays clear)
# ----------------------------------------------------------------------------
# Name differs between billing and CRM
for r in take(eligible_billing(), PLAN["name_variant_across_sources"]):
    new = name_variant(r["legal_name"], r["_entity"])
    log_error("name_variant_across_sources", "billing", r, "legal_name", new, r["legal_name"])
    r["legal_name"] = new

# Demo split records are logged as errors too
for r in billing:
    if r.get("_demo") and r["legal_name"] != demo["name"]:
        log_error("demo_split_customer", "billing", r, "legal_name", r["legal_name"], demo["name"])
    elif r.get("_demo"):
        r["_demo_primary"] = True

# Missing and invalid values in billing
for r in take(eligible_billing(lambda e: e["status"] == "Active"), PLAN["missing_billing_email"]):
    log_error("missing_billing_email", "billing", r, "billing_contact_email", "", r["billing_contact_email"])
    r["billing_contact_email"] = ""


def bad_vat(v):
    choice = rng.randint(0, 3)
    if v.startswith("NL") and choice == 0:
        return v[:-3]                                   # NL number without the B01 part
    if choice == 1:
        return v[:-1]                                   # one digit short
    if choice == 2:
        return v[2:]                                    # country prefix missing
    return v.replace(" ", "") + str(rng.randint(0, 9))  # one digit too many


for r in take(eligible_billing(), PLAN["invalid_vat_number"]):
    new = bad_vat(r["vat_number"])
    log_error("invalid_vat_number", "billing", r, "vat_number", new, r["vat_number"])
    r["vat_number"] = new

# Missing VAT only where billing can't fill the gap: CRM-only customers
for r in take(eligible_crm(lambda e: not e["in_billing"]), PLAN["missing_vat_number"]):
    log_error("missing_vat_number", "crm", r, "vat_number", "", r["vat_number"])
    r["vat_number"] = ""

# Sector typed in different words or languages
for r in take(eligible_crm(), PLAN["sector_free_text"]):
    e = r["_entity"]
    lang = "en" if rng.random() < 0.2 else e["lang"]
    new = rng.choice(SECTOR_FREE_TEXT[e["sector"]][lang])
    log_error("sector_free_text", "crm", r, "sector", new, e["sector"])
    r["sector"] = new

# Wrong sector (only where the company name gives the trade away)
for r in take(eligible_crm(lambda e: e["has_trade_word"] and e["sector"] != "Other"), PLAN["wrong_sector"]):
    e = r["_entity"]
    new = rng.choice([s for s in SECTORS[:4] if s != e["sector"]])
    log_error("wrong_sector", "crm", r, "sector", new, e["sector"])
    r["sector"] = new

# Missing renewal date for active customers
for r in take(eligible_crm(lambda e: e["status"] == "Active"), PLAN["missing_renewal_date"]):
    log_error("missing_renewal_date", "crm", r, "renewal_date", "", r["renewal_date"])
    r["renewal_date"] = ""


def bad_postcode(p, country):
    if country == "Netherlands":
        return rng.choice([p.replace(" ", "").lower(), p[:4], p[:4] + " " + p[5]])
    if country == "Germany":
        return p.lstrip("0") if p.startswith("0") else p[:4]  # leading zero lost, or a digit short
    return p + str(rng.randint(0, 9))


for r in take(eligible_crm(), PLAN["invalid_postcode"]):
    new = bad_postcode(r["postcode"], r["country"])
    log_error("invalid_postcode", "crm", r, "postcode", new, r["postcode"])
    r["postcode"] = new


def bad_email(m):
    user, domain = m.split("@")
    return rng.choice([f"{user}{domain}", f"{user}@@{domain}", f"{user}@{domain.split('.')[0]}",
                       f"{user} @{domain}", f"{user}@{domain}."])


for r in take(eligible_crm(), PLAN["invalid_email"]):
    new = bad_email(r["sales_contact_email"])
    log_error("invalid_email", "crm", r, "sales_contact_email", new, r["sales_contact_email"])
    r["sales_contact_email"] = new

# Date format mix-up: written month-first with slashes
for r in take(eligible_crm(lambda e: e["status"] == "Active"), PLAN["date_format_mixup"]):
    d = r["_entity"]["renewal"]
    new = d.strftime("%m/%d/%Y")
    log_error("date_format_mixup", "crm", r, "renewal_date", new, r["renewal_date"])
    r["renewal_date"] = new

# Status contradicts renewal date
half = PLAN["status_renewal_contradiction"] // 2
for r in take(eligible_crm(lambda e: e["status"] == "Active"), half):
    new = fmt_date(AS_OF - timedelta(days=rng.randint(30, 400)))
    log_error("status_renewal_contradiction", "crm", r, "renewal_date", new, r["renewal_date"])
    r["renewal_date"] = new
for r in take(eligible_crm(lambda e: e["status"] == "Lapsed"), PLAN["status_renewal_contradiction"] - half):
    new = fmt_date(AS_OF + timedelta(days=rng.randint(30, 300)))
    log_error("status_renewal_contradiction", "crm", r, "renewal_date", new, r["renewal_date"])
    r["renewal_date"] = new

# Duplicates inside the CRM
for r in take(eligible_crm(), PLAN["exact_duplicate_in_crm"]):
    dup = {k: v for k, v in r.items() if k != "_touched"}
    dup["_touched"] = True
    crm.append(dup)
    log_error("exact_duplicate_in_crm", "crm", dup, "(whole record)", "duplicate", "remove: same customer as another record")

for r in take(eligible_crm(), PLAN["near_duplicate_in_crm"]):
    e = r["_entity"]
    dup = {k: v for k, v in r.items() if k != "_touched"}
    dup["_touched"] = True
    dup["customer_name"] = name_variant(r["customer_name"], e)
    if rng.random() < 0.5:   # a second salesperson entered it with another contact
        fk = fakers["de_DE" if e["lang"] == "de" else "fr_BE" if e["lang"] == "fr" else "nl_NL"]
        first, last = fk.first_name(), fk.last_name()
        dup["sales_contact_name"] = f"{first} {last}"
        dup["sales_contact_email"] = f"{slug(first)}.{slug(last)}@{r['sales_contact_email'].split('@')[1]}"
    crm.append(dup)
    log_error("near_duplicate_in_crm", "crm", dup, "customer_name", dup["customer_name"], e["name"])

# ----------------------------------------------------------------------------
# 4. Shuffle, assign IDs, write files
# ----------------------------------------------------------------------------
rng.shuffle(crm)
rng.shuffle(billing)
for i, r in enumerate(crm, 1):
    r["crm_id"] = f"CRM-{i:05d}"
for i, r in enumerate(billing, 1):
    r["billing_id"] = f"BIL-{i:05d}"

RAW.mkdir(parents=True, exist_ok=True)
TRUTH.mkdir(parents=True, exist_ok=True)


def write(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


crm_fields = ["crm_id", "customer_name", "street", "postcode", "city", "country", "vat_number", "sector",
              "customer_type", "reseller_name", "account_status", "renewal_date", "account_manager",
              "sales_contact_name", "sales_contact_email", "phone"]
billing_fields = ["billing_id", "legal_name", "vat_number", "bill_to_name", "invoice_street", "invoice_postcode",
                  "invoice_city", "country", "billing_contact_email", "annual_contract_value_eur", "contract_type"]
write(RAW / "crm_customers.csv", crm, crm_fields)
write(RAW / "billing_customers.csv", billing, billing_fields)

entity_rows = [{
    "entity_id": e["entity_id"], "customer_name": e["name"], "country": e["country"], "vat_number": e["vat"],
    "street": e["street"], "postcode": e["postcode"], "city": e["city"], "sector": e["sector"],
    "customer_type": e["customer_type"], "reseller_name": e["reseller"]["name"] if e["reseller"] else "",
    "account_status": e["status"], "renewal_date": e["renewal"].isoformat(),
    "annual_contract_value_eur": e["acv"] if e["acv"] is not None else "",
    "contract_type": e["contract_type"] or "",
    "account_manager": e["account_manager"], "sales_contact_name": e["sales_contact_name"],
    "sales_contact_email": e["sales_contact_email"],
    "billing_contact_email": (e["reseller"]["billing_email"] if e["reseller"] else e["billing_email"]) if e["in_billing"] else "",
    "phone": e["phone"], "in_billing": e["in_billing"], "role": e["role"], "lookalike_of": e.get("twin", ""),
} for e in entities]
write(TRUTH / "entities.csv", entity_rows, list(entity_rows[0].keys()))

link_rows = [{"source": "crm", "record_id": r["crm_id"], "entity_id": r["_entity"]["entity_id"],
              "entity_role": r["_entity"]["role"]} for r in crm] + \
            [{"source": "billing", "record_id": r["billing_id"], "entity_id": r["_entity"]["entity_id"],
              "entity_role": r["_entity"]["role"]} for r in billing]
link_rows.sort(key=lambda x: (x["source"], x["record_id"]))
write(TRUTH / "record_links.csv", link_rows, ["source", "record_id", "entity_id", "entity_role"])

for err in errors:
    err["record_id"] = err["_row"].get("crm_id") or err["_row"].get("billing_id")
errors.sort(key=lambda x: (x["error_type"], x["record_id"]))
for i, err in enumerate(errors, 1):
    err["error_id"] = f"ERR-{i:04d}"
write(TRUTH / "errors.csv", errors,
      ["error_id", "error_type", "source", "record_id", "field", "raw_value", "correct_value", "entity_id"])

# ----------------------------------------------------------------------------
# 5. Checks and summary
# ----------------------------------------------------------------------------
counts = Counter(e["error_type"] for e in errors)
for kind, n in PLAN.items():
    assert counts[kind] == n, f"{kind}: planned {n}, planted {counts[kind]}"

records_with_error = len({e["record_id"] for e in errors})
total = len(crm) + len(billing)

true_top = sorted([e for e in entities if e["acv"]], key=lambda e: -e["acv"])[:5]
raw_top = sorted([r for r in billing if r["annual_contract_value_eur"] != ""],
                 key=lambda r: -int(r["annual_contract_value_eur"]))[:5]
assert demo in true_top, "demo customer should be in the true top 5"
assert all(r["_entity"] is not demo for r in raw_top), "demo customer should drop out of the raw top 5"

print(f"CRM rows: {len(crm)}   Billing rows: {len(billing)}   Real customers: {len(entities)}")
print(f"Planted errors: {len(errors)} on {records_with_error} records ({records_with_error / total:.1%} of all rows)")
print(f"Traps: {N_LOOKALIKE_PAIRS} look-alike pairs, {N_RESELLER} customers billed via reseller")
for kind, n in sorted(counts.items()):
    print(f"  {kind:32s} {n}")
print("\nTop 5 by contract value, true:")
for e in true_top:
    print(f"  {e['acv']:>8,}  {e['name']}")
print("Top 5 by contract value, raw billing data:")
for r in raw_top:
    print(f"  {int(r['annual_contract_value_eur']):>8,}  {r['legal_name']}")
