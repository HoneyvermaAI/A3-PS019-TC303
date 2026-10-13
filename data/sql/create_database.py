"""
create_database.py
==================
Reproducibly creates (or resets) the synthetic SQLite demo database:

  data/sql/privacy_demo.db

Tables created:
  customers    – Identity, Contact, Location fields
  employees    – Identity, Contact, Financial, Sensitive/Health fields
  transactions – Financial, Contact, Location fields

Run from the project root:
  python data/sql/create_database.py

Safe to re-run: database is dropped and recreated deterministically.
All data is entirely fictional. No real personal information is used.
"""

import os
import random
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import (
    create_engine, text,
    Column, Integer, String, Float, Date, Boolean,
    MetaData, Table, inspect,
)
from sqlalchemy.orm import declarative_base, Session

# ── reproducibility ────────────────────────────────────────────────────────────
SEED = 42
random.seed(SEED)

# ── database path ──────────────────────────────────────────────────────────────
DB_DIR  = Path(__file__).parent
DB_PATH = DB_DIR / "privacy_demo.db"
DB_URL  = f"sqlite:///{DB_PATH}"

Base = declarative_base()

# ══════════════════════════════════════════════════════════════════════════════
# ORM Models
# ══════════════════════════════════════════════════════════════════════════════

class Customer(Base):
    __tablename__ = "customers"

    customer_id       = Column(String(20),  primary_key=True)
    full_name         = Column(String(100))
    email             = Column(String(150))
    phone             = Column(String(30))
    date_of_birth     = Column(String(10))   # ISO date string
    city              = Column(String(80))
    state             = Column(String(50))
    country           = Column(String(60))
    postal_code       = Column(String(20))
    # ambiguous / borderline
    customer_segment  = Column(String(40))
    account_status    = Column(String(20))
    registration_date = Column(String(10))
    # clearly non-PII business fields
    loyalty_points    = Column(Integer)
    preferred_language= Column(String(10))


class Employee(Base):
    __tablename__ = "employees"

    employee_id        = Column(String(20),  primary_key=True)
    employee_name      = Column(String(100))
    email              = Column(String(150))
    phone              = Column(String(30))
    department         = Column(String(60))
    job_title          = Column(String(80))
    # Financial
    salary             = Column(Float,       nullable=True)
    bank_account       = Column(String(30),  nullable=True)
    # Location
    city               = Column(String(80))
    # Sensitive / Health
    health_insurance_id= Column(String(30),  nullable=True)
    # Ambiguous / business
    hire_date          = Column(String(10))
    employment_status  = Column(String(20))
    # Clearly non-PII
    office_floor       = Column(Integer)
    team_size          = Column(Integer)


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id   = Column(String(20),  primary_key=True)
    customer_id      = Column(String(20))
    transaction_date = Column(String(10))
    amount           = Column(Float)
    currency         = Column(String(10))
    payment_method   = Column(String(30))
    # Contact — billing email
    billing_email    = Column(String(150),  nullable=True)
    # Location
    billing_city     = Column(String(80))
    billing_country  = Column(String(60))
    # Financial — safe: last-4 only
    card_last4       = Column(String(4),    nullable=True)
    # Business / non-PII
    product_category = Column(String(60))
    order_status     = Column(String(20))
    discount_applied = Column(String(5))
    merchant_id      = Column(String(20))


# ══════════════════════════════════════════════════════════════════════════════
# Data-generation helpers  (same pools as generate_csv.py for consistency)
# ══════════════════════════════════════════════════════════════════════════════

FIRST_NAMES = [
    "Alice", "Bob", "Carol", "David", "Eva", "Frank", "Grace", "Hank",
    "Iris", "Jack", "Kara", "Leo", "Mia", "Nate", "Olivia", "Paul",
    "Quinn", "Rose", "Sam", "Tina", "Uma", "Victor", "Wendy", "Xander",
    "Yara", "Zoe", "Aaron", "Beth", "Chris", "Diana", "Ethan", "Fiona",
    "George", "Hannah", "Ivan", "Julia", "Kevin", "Laura", "Mike", "Nancy",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Martinez", "Wilson", "Anderson", "Taylor", "Thomas", "Jackson",
    "White", "Harris", "Martin", "Thompson", "Young", "Robinson", "Walker",
    "Hall", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill",
    "Flores", "Green", "Adams", "Nelson", "Baker", "Carter", "Mitchell",
]
CITIES    = ["Springfield", "Riverside", "Fairview", "Maplewood", "Lakeside",
             "Greenville", "Hillcrest", "Centerville", "Newport", "Oakland"]
STATES    = ["CA", "TX", "NY", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]
COUNTRIES = ["USA", "Canada", "UK", "Australia", "Germany"]
SEGMENTS  = ["retail", "enterprise", "smb", "education", "government"]
DEPTS     = ["Engineering", "Sales", "HR", "Finance", "Marketing",
             "Operations", "Legal", "Support", "Product", "IT"]
TITLES    = ["Engineer", "Analyst", "Manager", "Director", "Specialist",
             "Coordinator", "Consultant", "Associate", "Lead", "Officer"]
PAY_METHODS = ["credit_card", "debit_card", "bank_transfer", "paypal", "wallet"]
PROD_CATS   = ["Electronics", "Apparel", "Groceries", "Software", "Books",
               "Home & Garden", "Automotive", "Health & Beauty", "Toys", "Sports"]

def rand_date(y1: int, y2: int) -> str:
    s = date(y1, 1, 1)
    e = date(y2, 12, 31)
    return (s + timedelta(days=random.randint(0, (e - s).days))).isoformat()

def rand_phone() -> str:
    return f"+1-555-{random.randint(100,999)}-{random.randint(1000,9999)}"

def rand_email(name: str, domains=None) -> str:
    if domains is None:
        domains = ["mailbox.test","example.net","demomail.org","syntheticco.io"]
    slug = name.lower().replace(" ", ".").replace("'", "")
    return f"{slug}{random.randint(10,999)}@{random.choice(domains)}"

def rand_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

def maybe(value, p: float = 0.05):
    """Return None (NULL) with probability p."""
    return None if random.random() < p else value


# ══════════════════════════════════════════════════════════════════════════════
# Row builders
# ══════════════════════════════════════════════════════════════════════════════

def build_customers(n: int = 100) -> list[Customer]:
    rows = []
    for i in range(1, n + 1):
        name = rand_name()
        rows.append(Customer(
            customer_id       = f"CUST-{i:05d}",
            full_name         = name,
            email             = maybe(rand_email(name), 0.03),
            phone             = maybe(rand_phone(), 0.05),
            date_of_birth     = maybe(rand_date(1950, 2003), 0.04),
            city              = random.choice(CITIES),
            state             = random.choice(STATES),
            country           = random.choice(COUNTRIES),
            postal_code       = str(random.randint(10000, 99999)),
            customer_segment  = random.choice(SEGMENTS),
            account_status    = random.choice(["active", "inactive", "suspended"]),
            registration_date = rand_date(2015, 2024),
            loyalty_points    = random.randint(0, 10000),
            preferred_language= random.choice(["en", "fr", "de", "es"]),
        ))
    return rows


def build_employees(n: int = 80) -> list[Employee]:
    health_ids = [f"HI-{random.randint(100000,999999)}" for _ in range(200)]
    rows = []
    for i in range(1, n + 1):
        name = rand_name()
        rows.append(Employee(
            employee_id        = f"EMP-{i:05d}",
            employee_name      = name,
            email              = rand_email(name, ["corp.internal", "hrmail.test"]),
            phone              = maybe(rand_phone(), 0.06),
            department         = random.choice(DEPTS),
            job_title          = random.choice(TITLES),
            salary             = maybe(round(random.uniform(30000, 200000), 2), 0.02),
            bank_account       = maybe(f"ACC-{random.randint(10000000,99999999)}", 0.03),
            city               = random.choice(CITIES),
            health_insurance_id= maybe(random.choice(health_ids), 0.05),
            hire_date          = rand_date(2005, 2024),
            employment_status  = random.choice(["full-time", "part-time", "contract"]),
            office_floor       = random.randint(1, 20),
            team_size          = random.randint(2, 50),
        ))
    return rows


def build_transactions(n: int = 120) -> list[Transaction]:
    cust_pool = [f"CUST-{i:05d}" for i in range(1, 101)]
    rows = []
    for i in range(1, n + 1):
        bname = rand_name()
        rows.append(Transaction(
            transaction_id   = f"TXN-{i:06d}",
            customer_id      = random.choice(cust_pool),
            transaction_date = rand_date(2022, 2024),
            amount           = round(random.uniform(5.0, 4999.99), 2),
            currency         = random.choice(["USD", "EUR", "GBP", "CAD"]),
            payment_method   = random.choice(PAY_METHODS),
            billing_email    = maybe(rand_email(bname), 0.04),
            billing_city     = random.choice(CITIES),
            billing_country  = random.choice(COUNTRIES),
            card_last4       = maybe(str(random.randint(1000, 9999)), 0.08),
            product_category = random.choice(PROD_CATS),
            order_status     = random.choice(["completed","pending","refunded","failed"]),
            discount_applied = random.choice(["yes", "no"]),
            merchant_id      = f"MER-{random.randint(1000,9999)}",
        ))
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print(f"Target database: {DB_PATH}\n")

    # Drop and recreate schema
    engine = create_engine(DB_URL, echo=False)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("  [OK] Schema created (tables: customers, employees, transactions)")

    with Session(engine) as session:
        customers    = build_customers(100)
        employees    = build_employees(80)
        transactions = build_transactions(120)

        session.add_all(customers)
        session.add_all(employees)
        session.add_all(transactions)
        session.commit()

    # Verification
    with engine.connect() as conn:
        for tbl in ("customers", "employees", "transactions"):
            count = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            print(f"  [OK] {tbl:20s}  {count:>4} rows")

    print(f"\nDatabase ready: {DB_PATH}")


if __name__ == "__main__":
    main()
