"""
validate_datasets.py
====================
Quick validation script for Phase 2 synthetic datasets.

Checks:
  1. All CSV files exist and have expected row counts.
  2. SQLite database exists.
  3. All SQL tables exist with expected row counts.
  4. Ground-truth file exists and has the expected columns.
  5. All 5 personal-data classes are represented in the ground truth.
  6. Ground truth contains both positive and negative examples.

Run:
  python validate_datasets.py
"""

import os
import csv
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
DATA_DIR     = PROJECT_ROOT / "data"

PASS = "  [PASS]"
FAIL = "  [FAIL]"

errors = 0

def ok(msg: str) -> None:
    print(f"{PASS} {msg}")

def fail(msg: str) -> None:
    global errors
    errors += 1
    print(f"{FAIL} {msg}")

# ==============================================================================
# 1. CSV files
# ==============================================================================
print("\n-- CSV Files --------------------------------------------------")
CSV_EXPECTED = {
    "customers.csv":    150,
    "employees.csv":    120,
    "transactions.csv": 175,
}

for fname, expected_rows in CSV_EXPECTED.items():
    fpath = DATA_DIR / "csv" / fname
    if not fpath.exists():
        fail(f"{fname} does not exist")
        continue
    with open(fpath, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    count = len(rows)
    if count == expected_rows:
        ok(f"{fname:<22}  {count} rows (expected {expected_rows})")
    else:
        fail(f"{fname:<22}  {count} rows (expected {expected_rows})")

# ==============================================================================
# 2. SQLite database
# ==============================================================================
print("\n-- SQLite Database --------------------------------------------")
db_path = DATA_DIR / "sql" / "privacy_demo.db"

if not db_path.exists():
    fail("privacy_demo.db does not exist")
else:
    ok(f"privacy_demo.db exists ({db_path.stat().st_size:,} bytes)")
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    SQL_EXPECTED = {
        "customers":    100,
        "employees":    80,
        "transactions": 120,
    }
    for tbl, expected_rows in SQL_EXPECTED.items():
        try:
            count = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            if count == expected_rows:
                ok(f"  table {tbl:<18}  {count} rows")
            else:
                fail(f"  table {tbl:<18}  {count} rows (expected {expected_rows})")
        except sqlite3.OperationalError as e:
            fail(f"  table {tbl}: {e}")
    con.close()

# ==============================================================================
# 3. Ground-truth file
# ==============================================================================
print("\n-- Ground Truth -----------------------------------------------")
gt_path = DATA_DIR / "ground_truth.csv"

if not gt_path.exists():
    fail("ground_truth.csv does not exist")
else:
    with open(gt_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    ok(f"ground_truth.csv exists  ({len(rows)} labelled fields)")

    required_cols = {"source_type","source_name","field_name","expected_class","is_personal_data"}
    actual_cols   = set(rows[0].keys()) if rows else set()
    missing_cols  = required_cols - actual_cols
    if missing_cols:
        fail(f"Missing columns: {missing_cols}")
    else:
        ok(f"Required columns present: {sorted(required_cols)}")

    # Five classes
    CLASSES = {"Identity", "Contact", "Location", "Financial", "Sensitive/Health"}
    found_classes = {r["expected_class"] for r in rows if r["expected_class"]}
    for cls in CLASSES:
        if cls in found_classes:
            count_cls = sum(1 for r in rows if r["expected_class"] == cls)
            ok(f"  Class '{cls}' has {count_cls} positive example(s)")
        else:
            fail(f"  Class '{cls}' has NO examples in ground truth")

    # Positive and negative examples
    positives = sum(1 for r in rows if r.get("is_personal_data","").lower() == "true")
    negatives = sum(1 for r in rows if r.get("is_personal_data","").lower() == "false")
    ok(f"Positive examples (is_personal_data=true):   {positives}")
    ok(f"Negative examples (is_personal_data=false):  {negatives}")
    if positives == 0:
        fail("No positive examples found")
    if negatives == 0:
        fail("No negative examples found")

# ==============================================================================
# Summary
# ==============================================================================
print("\n" + "-" * 52)
if errors == 0:
    print("  ALL CHECKS PASSED")
else:
    print(f"  {errors} CHECK(S) FAILED")
print("-" * 52)
