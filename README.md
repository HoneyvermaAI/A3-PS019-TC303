# A3-PS019-TC303 · Personal-Data Discovery & Privacy Evidence Inventory

> **Hackathon Project · PS-019**  
> Technical evidence/inventory prototype — for human review only.

---

## Problem Statement (PS-019)

Organisations collect and process personal data across many systems, file formats, and databases, but often lack a consistent, automated way to:

1. **Discover** where personal-data fields actually reside in their data assets.
2. **Map** those fields to declared data-processing purposes and retention policies.
3. **Flag** assets where purpose or retention metadata is absent or incomplete.
4. **Evaluate** the quality of detection using measurable precision and recall metrics.

Without this inventory, privacy teams rely on manual spreadsheets that quickly become stale, making proactive risk management difficult.

---

## Project Objective

Build a **technical evidence/inventory prototype** (TC-303) that:

- Scans **synthetic CSV files** and a **synthetic SQLite database**.
- Identifies **candidate personal-data fields** across five predefined data classes.
- Maps detected fields to **declared purpose and retention metadata**.
- **Flags** data assets with missing or incomplete metadata for human follow-up.
- **Evaluates** detection quality using per-class precision and recall.

> **⚠️ Scope Limitation**  
> This system provides **technical evidence for human review** and does **not** make legal compliance decisions. It does not determine lawful basis, consent validity, GDPR / DPDP compliance status, or automatically infer universal data flows. All data used is synthetic / demo data.

---

## Planned Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        Frontend                         │
│          (HTML / CSS / JavaScript — no framework)       │
│  Dashboard · Scan trigger · Results table · Reports     │
└──────────────────────────┬──────────────────────────────┘
                           │  HTTP (REST)
┌──────────────────────────▼──────────────────────────────┐
│                    FastAPI Backend                       │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │   Scanner   │  │   Metadata   │  │  Evaluation   │  │
│  │  (Pandas /  │  │   Layer      │  │  (Precision / │  │
│  │ SQLAlchemy) │  │  (Pydantic)  │  │   Recall)     │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
│           ▲                ▲                            │
│           │                │                            │
│  ┌────────┴────────────────┴───────────────────────┐   │
│  │             Data Sources (synthetic)             │   │
│  │   CSV files (data/csv/)   SQLite (data/sql/)     │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Planned Data Classes

The scanner will identify candidate fields across **five predefined classes**:

| # | Class | Example Fields |
|---|-------|----------------|
| 1 | **Identity** | name, full_name, national_id, passport_number, dob, gender |
| 2 | **Contact** | email, phone, mobile, address, zip_code, postal_code |
| 3 | **Location** | latitude, longitude, city, country, ip_address, gps_coords |
| 4 | **Financial** | credit_card, iban, bank_account, salary, tax_id, cvv |
| 5 | **Sensitive / Health** | medical_record, diagnosis, blood_type, disability, religion, biometric |

Classification is based on **field-name pattern matching** and **configurable keyword dictionaries** — no machine-learning models, no external APIs.

---

## Planned Features

- **CSV Scanner** — reads synthetic CSV files, inspects column names, applies regex/keyword matching per data class.
- **SQL Schema Scanner** — connects to a SQLite database via SQLAlchemy, introspects table and column metadata without reading row data.
- **Metadata Mapper** — loads a YAML/JSON sidecar file declaring purpose and retention policy per asset; maps detected fields to declared metadata.
- **Gap Flagging** — identifies fields or assets that have no declared purpose or retention entry and marks them for human review.
- **Evaluation Engine** — compares scanner detections against a hand-labelled ground-truth file; computes precision, recall, and F1 per data class.
- **REST API** — FastAPI endpoints to trigger scans, retrieve results, and download reports.
- **Report Export** — JSON and CSV report generation saved to `reports/`.
- **Simple Dashboard** — plain HTML/CSS/JS page to display scan results and flag summary.

---

## Planned Evaluation Methodology

Detection quality will be measured per data class using:

$$\text{Precision} = \frac{TP}{TP + FP}$$

$$\text{Recall} = \frac{TP}{TP + FN}$$

$$F_1 = 2 \cdot \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$

Where:
- **TP** = field correctly identified as belonging to a class.
- **FP** = field incorrectly assigned to a class.
- **FN** = field belonging to a class that was missed.

A hand-labelled **ground-truth file** (`tests/ground_truth.json`) will serve as the reference. Metrics are computed at scan time and written to `reports/`.

> Numeric results will only appear after the detection engine is built and tested against real synthetic data. **No fake numbers are presented here.**

---

## Data Sources

| Source | Format | Location | Purpose |
|--------|--------|----------|---------|
| Synthetic customer data | CSV | `data/csv/` | Identity, Contact, Location fields |
| Synthetic transactions | CSV | `data/csv/` | Financial fields |
| Synthetic HR/health records | CSV | `data/csv/` | Sensitive/Health fields |
| Synthetic multi-table schema | SQLite | `data/sql/` | Cross-table schema scanning |

All data is **synthetic and generated for demo purposes only**. No real personal data is used.

---

## Project Structure

```
A3-PS019-TC303/
│
├── backend/
│   ├── scanner/       # CSV & SQL scanning logic
│   ├── metadata/      # Metadata loading, mapping & gap flagging
│   ├── config/        # Keyword dictionaries, settings, class definitions
│   └── evaluation/    # Precision/recall computation
│
├── data/
│   ├── csv/           # Synthetic CSV data files
│   └── sql/           # Synthetic SQLite database(s)
│
├── frontend/          # HTML/CSS/JS dashboard (no build step)
│
├── reports/           # Generated JSON/CSV scan reports (git-ignored)
│
├── tests/             # pytest unit & integration tests + ground_truth.json
│
├── docs/              # Architecture diagrams, design notes
│
├── README.md
├── requirements.txt
└── .gitignore
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.x |
| API Framework | FastAPI |
| Data Processing | Pandas |
| Database Inspection | SQLAlchemy |
| Demo Database | SQLite |
| Data Models / Validation | Pydantic |
| Testing | pytest + httpx |
| Frontend | HTML · CSS · Vanilla JS |

---

## Getting Started

```bash
# 1. Clone / enter project
cd A3-PS019-TC303

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run tests (placeholder — suite will grow)
pytest tests/ -v

# 5. Start API server (once backend is implemented)
uvicorn backend.main:app --reload
```

---

## Synthetic Data

### Why Synthetic Data?

This prototype operates on **entirely synthetic, fictional datasets**.  
No real personal information has been used at any stage. Synthetic data allows the scanner to be developed, tested, and demonstrated without creating any privacy risk.

### Datasets Created

| File | Location | Records | Description |
|------|----------|---------|-------------|
| `customers.csv` | `data/csv/` | 150 | Fictional customer profiles |
| `employees.csv` | `data/csv/` | 120 | Fictional employee records |
| `transactions.csv` | `data/csv/` | 175 | Fictional purchase transactions |
| `privacy_demo.db` | `data/sql/` | 3 tables | SQLite database mirroring the above structure |

All CSV files are generated reproducibly by `data/csv/generate_csv.py` (seed = 42).  
The SQLite database is generated reproducibly by `data/sql/create_database.py` (seed = 42).

### Five Personal-Data Classes Represented

| Class | Example fields in datasets |
|-------|---------------------------|
| **Identity** | `full_name`, `employee_name`, `date_of_birth` |
| **Contact** | `email`, `phone`, `billing_email` |
| **Location** | `city`, `state`, `country`, `postal_code`, `billing_city` |
| **Financial** | `salary`, `bank_account`, `amount`, `card_last4` |
| **Sensitive/Health** | `health_insurance_id` |

### Intentional Design Choices

- Some fields have **names that clearly indicate** personal data (e.g. `full_name`, `email`).
- Some fields are **ambiguous by name** but meaningful in context (e.g. `city` could be personal or not depending on schema).
- Several fields are **clearly non-PII business fields** (e.g. `loyalty_points`, `merchant_id`, `office_floor`).
- A small number of fields are **intentionally left NULL/empty** to test preprocessing robustness.
- Transaction records store only `card_last4` (4 digits) — no full card numbers are present anywhere.

### Ground-Truth Evaluation File

`data/ground_truth.csv` contains **hand-labelled annotations** for every field across all CSV files and all SQLite tables.

| Column | Meaning |
|--------|---------|
| `source_type` | `CSV` or `SQL` |
| `source_name` | File or `db:table` reference |
| `field_name` | Column name |
| `expected_class` | One of the 5 classes, or empty for non-PII |
| `is_personal_data` | `true` / `false` |
| `notes` | Human reviewer rationale |

This file serves as the reference for computing per-class **precision, recall, and F1** once the detection engine is built. It includes both positive and negative examples, plus borderline/ambiguous fields, to ensure realistic evaluation.

> **No fake scanner results or precision/recall numbers are presented here.** Evaluation metrics will be computed against real scanner output in a later phase.

---

## Detection Engine

> **This scanner identifies candidate personal-data fields based on configurable technical evidence. It does not determine whether processing is lawful or compliant with any specific regulation.**

### Configurable Rules (`backend/config/rules.json`)

All detection rules are stored in a single JSON file. A developer can add or remove keywords and patterns without modifying Python source code. The file controls:

- **Keywords** — column-name terms for each data class
- **Regex patterns** — value-level patterns (email, phone, date, postal code, account numbers)
- **Dtype hints** — pandas dtype associations per class
- **Scoring weights** — contribution of each evidence source to confidence
- **Confidence thresholds** — boundaries for High / Medium / Low / None labels

### Column-Name Evidence (Source A)

Column names are normalised before matching to handle all common naming conventions:

| Input | Normalised tokens |
|-------|------------------|
| `customerEmail` | `["customer", "email"]` |
| `full_name` | `["full", "name"]` |
| `EMAIL` | `["email"]` |
| `date-of-birth` | `["date", "of", "birth"]` |

**Match strength:**
- **Exact** (+0.70): full column name equals a keyword (e.g. `full_name` → keyword `full_name`)
- **Token** (+0.60): a column token equals a keyword (e.g. `customer_email` → token `email`)
- **Substring** (+0.30): keyword appears as a substring of the normalised name

### Data-Type Evidence (Source B)

The pandas dtype of the column contributes a small supporting score (+0.05) when it is consistent with the class's type hints (e.g. `float64` for Financial). **Dtype alone is never sufficient to reach High confidence.**

### Value-Pattern Evidence (Source C)

A random sample of up to 100 non-null values is tested against configurable regex patterns. The fraction that matches (`pattern_match_rate`) determines the pattern score:

| Match rate | Score contribution |
|-----------|-------------------|
| ≥ 80% | +0.30 (High) |
| 50–79% | +0.18 (Medium) |
| 20–49% | +0.08 (Low) |
| 1–19% | +0.02 (Minimal) |
| 0% | +0.00 |

### Confidence Scoring

```
confidence = min(1.0, keyword_score + pattern_score + dtype_score)
```

| Level | Threshold |
|-------|-----------|
| **High** | ≥ 0.75 |
| **Medium** | 0.45 – 0.74 |
| **Low** | 0.20 – 0.44 |
| **None** | < 0.20 — field not classified |

### Review-Required Flag

`review_required = True` when:
- Confidence is below 0.75 **and** a class was detected (Medium / Low classifications always require human review)
- Keyword matched but value patterns do not confirm (conflict between evidence sources)

### False-Positive Prevention

The engine is designed to avoid blindly classifying vague fields:

- `email_status` with values `["verified", "pending", "bounced"]` → keyword "email" matches, but email pattern matches 0% of values → **Medium confidence, review required** (not classified as high-confidence Contact)
- `phone_verified` with values `["true", "false"]` → same logic → **Medium confidence, review required**
- `loyalty_points` with integer values → no keyword match, `currency_amount` pattern requires `$` or decimal → **not classified**

### Architecture

```
CSV file  ──→  CSVScanner  ─┐
                             ├──→  PersonalDataDetector  ──→  FieldDetectionResult
SQL table ──→  SQLScanner  ─┘
```

The `PersonalDataDetector` is the **single source of classification logic**. Both scanners are thin I/O wrappers. The `ScannerService` orchestrates them and is ready to be connected to FastAPI endpoints in a later phase.

---

## Purpose and Retention Metadata

> **Scope Limitation**  
> This component compares technically discovered candidate fields with declared metadata. Missing metadata is reported as an evidence gap for human review and is not interpreted as a legal or regulatory violation.

Phase 4 bridges technical discovery with governance documentation by mapping candidate personal-data fields to declared purpose and retention metadata.

### Three Distinct Concepts

1. **Detected Field**: The scanner discovered technical evidence (column names, regex patterns, data types) suggesting that a field contains personal data.
2. **Declared Metadata**: The organisation has explicitly declared a business purpose and/or retention period for that field in `backend/metadata/metadata.json`.
3. **Evidence Gap**: The scanner identified a candidate field, but the corresponding declared metadata is missing, incomplete, or not yet declared.

### Metadata Configuration (`backend/metadata/metadata.json`)

Metadata entries are defined with source isolation to prevent cross-source ambiguities:
- `source_type`: Data source type (`CSV` or `SQL`)
- `source_name`: File name (`customers.csv`) or table (`privacy_demo.db:customers`)
- `field_name`: Exact column name
- `purpose`: Declared operational or business purpose (nullable)
- `retention_period`: Declared retention schedule or statutory limit (nullable)
- `metadata_owner`: Team or division responsible
- `notice_version`: Associated privacy notice version (optional)
- `notes`: Operational or audit notes (optional)

### Three-Part Key Mapping (`backend/metadata/mapper.py`)

Matching uses `(source_type, source_name, field_name)` rather than column name alone. This ensures fields such as `email` in customer-facing datasets are evaluated independently from employee internal directory records.

### Evidence Gap Classification

Every detected candidate field receives a neutral status:
- **Complete**: Both purpose and retention period are declared.
- **Purpose Missing**: Retention period is declared, but purpose is missing.
- **Retention Missing**: Purpose is declared, but retention period is missing.
- **Purpose & Retention Missing**: Record exists, but neither purpose nor retention is declared.
- **Not Mapped**: No declared metadata entry exists for this field.

### Generated Inventory & Gap Reports

The pipeline produces:
- `reports/evidence_inventory.csv`: Full tabular inventory linking discovered fields, detection confidence, declared metadata, and gap statuses.
- `reports/evidence_gaps.csv`: Filtered report containing only fields with evidence gaps.
- `reports/evidence_inventory.json`: Machine-readable output for upcoming API endpoints and frontend dashboards.

Run the end-to-end mapping pipeline via CLI:
```bash
python backend/metadata/run_metadata_mapping.py
```

---

## Ground-Truth Evaluation & Performance Metrics (Phase 5)

> **Scope Limitation**  
> Evaluation metrics are calculated against hand-labelled synthetic benchmark datasets. They provide technical evidence of detector behavior, not legal certification, GDPR/DPDP compliance audits, or universal real-world performance guarantees.

Phase 5 introduces a reproducible, explainable evaluation framework that verifies scanner predictions against `data/ground_truth.csv`.

### Architecture & Matching Strategy

```
Scanner Engine Output (84 fields) ──┐
                                     ├──→ Composite Key Matching ──→ Evaluator Engine ──→ Reports (CSV / JSON)
Ground Truth CSV (84 labels)     ──┘    (source_type, source_name, field_name)
```

1. **Composite Key Matching**:
   Records are paired strictly on `(source_type, source_name, field_name)`. Sources are completely isolated so that identical column names across multiple tables/files are never conflated.
2. **Whitespace and Casing Normalization**:
   Only harmless formatting differences (e.g., source type casing `csv` vs `CSV`) are normalized. No unmatched records are silently ignored.
3. **No Ground-Truth Leakage**:
   Ground-truth labels are never fed into the scanner engine or detection logic.

### Candidate Detection vs Class Classification

The evaluation clearly separates two distinct types of detector outcomes:

1. **Binary Candidate Detection** (Personal Data vs Non-Personal Data):
   - **True Positive (TP)**: Field is labelled as personal data and detected as a candidate by scanner.
   - **False Positive (FP)**: Field is non-personal data, but scanner detected it as a personal-data candidate.
   - **False Negative (FN)**: Field is labelled as personal data, but scanner failed to detect it.
   - **True Negative (TN)**: Field is non-personal data and scanner correctly left it unflagged.

2. **Per-Class Classification** (One-vs-Rest for each of the 5 classes):
   - **True Positive (TP)**: Ground-truth class equals $C$ and predicted class equals $C$.
   - **False Positive (FP)**: Scanner predicted class $C$, but ground truth is not $C$.
   - **False Negative (FN)**: Ground truth is class $C$, but scanner predicted something else (or nothing).
   - If a field is predicted as the wrong class, it is correctly accounted for as a **False Negative** for its expected class and a **False Positive** for the predicted class.

### Metrics Definitions & Zero Handling

$$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}}$$
$$\text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}}$$
$$\text{F1-Score} = \frac{2 \times \text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$

- **Zero Denominator Handling**: When $(\text{TP} + \text{FP}) = 0$ or $(\text{TP} + \text{FN}) = 0$, the metric is explicitly recorded as `None` (undefined) with an informative status label (`Zero Predictions` or `Zero Ground-Truth Positives`).
- **Unlabelled Fields**: Missing labels are never treated as negative examples.

### Benchmark Evaluation Results

On the 84-field synthetic benchmark dataset:
- **Binary Candidate Detection**:
  - TP: 40, FP: 10, FN: 0, TN: 34
  - Precision: **80.0%**, Recall: **100.0%**, F1-Score: **0.889**
- **Per-Class Metrics**:
  - `Identity`: Precision = 0.429, Recall = 1.000, F1 = 0.600 (Support: 6)
  - `Contact`: Precision = 1.000, Recall = 1.000, F1 = 1.000 (Support: 10)
  - `Location`: Precision = 1.000, Recall = 1.000, F1 = 1.000 (Support: 14)
  - `Financial`: Precision = 0.800, Recall = 1.000, F1 = 0.889 (Support: 8)
  - `Sensitive/Health`: Precision = 1.000, Recall = 1.000, F1 = 1.000 (Support: 2 — Limited Sample)

### Dataset Limitations & Sample Size Notice

- **Class Imbalance**: `Sensitive/Health` contains only 2 positive benchmark examples in the demo database. Its 100% metrics reflect prototype accuracy on known test schema, not generalized statistical performance.
- **False Positive Causes**: Dates (`registration_date`, `hire_date`, `transaction_date`) match ISO date regex patterns and are currently flagged as candidate `Identity` fields with low/medium confidence, requiring human review.

### Running the Evaluation CLI

Run the full evaluation pipeline via PowerShell:
```powershell
$env:PYTHONIOENCODING="utf-8"
.venv\Scripts\python backend\evaluation\run_evaluation.py
```

### Generated Reports
- `reports/evaluation_summary.json`: Complete dataset counts, per-class metrics, warnings, and limitations.
- `reports/evaluation_per_class.csv`: Tabular TP, FP, FN, support, precision, recall, and F1 per class.
- `reports/evaluation_confusion_matrix.csv`: Full ground-truth vs predicted confusion matrix with explicit `Not Detected` column.
- `reports/evaluation_errors.csv`: Detailed mismatch logs with source keys, error categories, and detection reasoning.

---

## Disclaimer

> This prototype is developed for a **hackathon demonstration** using **entirely synthetic data**.  
> It provides a **technical evidence inventory** to assist human privacy reviewers.  
> It does **not** constitute legal advice, determine regulatory compliance, or replace a formal Data Protection Impact Assessment (DPIA).


