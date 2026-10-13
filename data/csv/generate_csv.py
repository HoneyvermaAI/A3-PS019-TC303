"""
generate_csv.py
===============
Reproducibly generates three synthetic CSV datasets for the
A3-PS019-TC303 Privacy Evidence Inventory prototype.

Files produced (relative to this script's directory):
  customers.csv    – 150 records
  employees.csv    – 120 records
  transactions.csv – 175 records

Run:
  python data/csv/generate_csv.py

Safe to re-run: existing files are overwritten deterministically.
All data is entirely fictional. No real personal information is used.
"""

import csv
import random
import os
from datetime import date, timedelta

# ── reproducibility ────────────────────────────────────────────────────────────
SEED = 42
random.seed(SEED)

# ── output directory (same folder as this script) ─────────────────────────────
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── helpers ───────────────────────────────────────────────────────────────────

def rand_date(start_year: int, end_year: int) -> str:
    start = date(start_year, 1, 1)
    end   = date(end_year, 12, 31)
    delta = (end - start).days
    return (start + timedelta(days=random.randint(0, delta))).isoformat()

def rand_phone() -> str:
    """Synthetic phone: +1-555-XXX-XXXX  (555 block is reserved/non-real)."""
    return f"+1-555-{random.randint(100,999)}-{random.randint(1000,9999)}"

def rand_email(name: str, domains=None) -> str:
    if domains is None:
        domains = ["mailbox.test", "example.net", "demomail.org",
                   "syntheticco.io", "fakepost.com"]
    slug = name.lower().replace(" ", ".").replace("'", "")
    suffix = random.randint(10, 999)
    return f"{slug}{suffix}@{random.choice(domains)}"

def rand_postal() -> str:
    return f"{random.randint(10000, 99999)}"

def maybe_missing(value, probability: float = 0.04):
    """Return empty string instead of value with given probability."""
    return "" if random.random() < probability else value

# ── name pools ────────────────────────────────────────────────────────────────
FIRST_NAMES = [
    "Alice", "Bob", "Carol", "David", "Eva", "Frank", "Grace", "Hank",
    "Iris", "Jack", "Kara", "Leo", "Mia", "Nate", "Olivia", "Paul",
    "Quinn", "Rose", "Sam", "Tina", "Uma", "Victor", "Wendy", "Xander",
    "Yara", "Zoe", "Aaron", "Beth", "Chris", "Diana", "Ethan", "Fiona",
    "George", "Hannah", "Ivan", "Julia", "Kevin", "Laura", "Mike", "Nancy",
    "Oscar", "Patricia", "Roger", "Susan", "Tom", "Ursula", "Vince", "Wanda",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Martinez", "Wilson", "Anderson", "Taylor", "Thomas", "Jackson",
    "White", "Harris", "Martin", "Thompson", "Young", "Robinson", "Walker",
    "Hall", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill",
    "Flores", "Green", "Adams", "Nelson", "Baker", "Carter", "Mitchell",
    "Perez", "Roberts", "Turner", "Phillips",
]

def rand_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

# ── geo pools ─────────────────────────────────────────────────────────────────
CITIES   = ["Springfield", "Riverside", "Fairview", "Maplewood", "Lakeside",
            "Greenville", "Hillcrest", "Centerville", "Newport", "Oakland",
            "Brookfield", "Westfield", "Eastport", "Northgate", "Southtown"]
STATES   = ["CA", "TX", "NY", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]
COUNTRIES= ["USA", "Canada", "UK", "Australia", "Germany"]

# ── domain-specific pools ─────────────────────────────────────────────────────
SEGMENTS      = ["retail", "enterprise", "smb", "education", "government"]
DEPARTMENTS   = ["Engineering", "Sales", "HR", "Finance", "Marketing",
                 "Operations", "Legal", "Support", "Product", "IT"]
JOB_TITLES    = ["Engineer", "Analyst", "Manager", "Director", "Specialist",
                 "Coordinator", "Consultant", "Associate", "Lead", "Officer"]
PAY_METHODS   = ["credit_card", "debit_card", "bank_transfer", "paypal", "wallet"]
PROD_CATS     = ["Electronics", "Apparel", "Groceries", "Software", "Books",
                 "Home & Garden", "Automotive", "Health & Beauty", "Toys", "Sports"]
HEALTH_IDS    = [f"HI-{random.randint(100000,999999)}" for _ in range(200)]

# ══════════════════════════════════════════════════════════════════════════════
# 1. customers.csv  (150 records)
# ══════════════════════════════════════════════════════════════════════════════

def generate_customers(n: int = 150) -> list[dict]:
    records = []
    for i in range(1, n + 1):
        name = rand_name()
        dob  = rand_date(1950, 2003)
        records.append({
            "customer_id":        f"CUST-{i:05d}",
            "full_name":          name,
            "email":              maybe_missing(rand_email(name), 0.03),
            "phone":              maybe_missing(rand_phone(), 0.05),
            "date_of_birth":      maybe_missing(dob, 0.04),
            "city":               random.choice(CITIES),
            "state":              random.choice(STATES),
            "country":            random.choice(COUNTRIES),
            "postal_code":        rand_postal(),
            # ambiguous — looks like it could be personal but is actually business
            "customer_segment":   random.choice(SEGMENTS),
            "account_status":     random.choice(["active", "inactive", "suspended"]),
            "registration_date":  rand_date(2015, 2024),
            # purely business / non-PII
            "loyalty_points":     random.randint(0, 10000),
            "preferred_language": random.choice(["en", "fr", "de", "es"]),
        })
    return records

# ══════════════════════════════════════════════════════════════════════════════
# 2. employees.csv  (120 records)
# ══════════════════════════════════════════════════════════════════════════════

def generate_employees(n: int = 120) -> list[dict]:
    records = []
    for i in range(1, n + 1):
        name = rand_name()
        records.append({
            "employee_id":       f"EMP-{i:05d}",
            "employee_name":     name,
            "email":             rand_email(name, ["corp.internal", "hrmail.test"]),
            "phone":             maybe_missing(rand_phone(), 0.06),
            "department":        random.choice(DEPARTMENTS),
            "job_title":         random.choice(JOB_TITLES),
            # Financial
            "salary":            maybe_missing(round(random.uniform(30000, 200000), 2), 0.02),
            "bank_account":      maybe_missing(f"ACC-{random.randint(10000000,99999999)}", 0.03),
            # Location
            "city":              random.choice(CITIES),
            # Sensitive/Health
            "health_insurance_id": maybe_missing(random.choice(HEALTH_IDS), 0.05),
            # Ambiguous/business
            "hire_date":         rand_date(2005, 2024),
            "employment_status": random.choice(["full-time", "part-time", "contract"]),
            "office_floor":      random.randint(1, 20),           # clearly non-PII
            "team_size":         random.randint(2, 50),           # clearly non-PII
        })
    return records

# ══════════════════════════════════════════════════════════════════════════════
# 3. transactions.csv  (175 records)
# ══════════════════════════════════════════════════════════════════════════════

def generate_transactions(n: int = 175) -> list[dict]:
    # customer_ids pool drawn from the customers dataset range
    cust_pool = [f"CUST-{i:05d}" for i in range(1, 151)]
    records = []
    for i in range(1, n + 1):
        billing_name = rand_name()
        records.append({
            "transaction_id":   f"TXN-{i:06d}",
            "customer_id":      random.choice(cust_pool),
            "transaction_date": rand_date(2022, 2024),
            "amount":           round(random.uniform(5.0, 4999.99), 2),
            "currency":         random.choice(["USD", "EUR", "GBP", "CAD"]),
            "payment_method":   random.choice(PAY_METHODS),
            # Contact — billing email
            "billing_email":    maybe_missing(rand_email(billing_name), 0.04),
            # Location — billing city
            "billing_city":     random.choice(CITIES),
            "billing_country":  random.choice(COUNTRIES),
            # Financial — safe: only last 4 digits
            "card_last4":       maybe_missing(f"{random.randint(1000,9999)}", 0.08),
            # Business / non-PII
            "product_category": random.choice(PROD_CATS),
            "order_status":     random.choice(["completed", "pending", "refunded", "failed"]),
            "discount_applied": random.choice(["yes", "no"]),
            "merchant_id":      f"MER-{random.randint(1000,9999)}",  # non-PII merchant ref
        })
    return records

# ══════════════════════════════════════════════════════════════════════════════
# writer
# ══════════════════════════════════════════════════════════════════════════════

def write_csv(filename: str, records: list[dict]) -> None:
    path = os.path.join(OUT_DIR, filename)
    if not records:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    print(f"  [OK] {filename:30s}  {len(records):>4} records  ->  {path}")

# ══════════════════════════════════════════════════════════════════════════════
# main
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Generating synthetic CSV datasets (seed=42) ...")
    write_csv("customers.csv",    generate_customers(150))
    write_csv("employees.csv",    generate_employees(120))
    write_csv("transactions.csv", generate_transactions(175))
    print("\nDone. All CSV files written to data/csv/")
