# Hackathon Live Demo Checklist: PS-019

Use this quick-reference step-by-step checklist to ensure a smooth, error-free presentation.

---

## Pre-Demo Checklist (5 Minutes Before Presentation)

- [ ] **Open PowerShell** in the project directory: `c:\Users\honey\OneDrive\Desktop\A3-PS019-TC303`
- [ ] **Run test suite** to ensure clean state:
  ```powershell
  .venv\Scripts\python -m pytest tests/ -q
  ```
  *(Expected: `87 passed, 1 warning`)*
- [ ] **Start the application**:
  ```powershell
  $env:PYTHONIOENCODING="utf-8"
  .venv\Scripts\python -m uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8000
  ```
- [ ] **Open browser** at: `http://127.0.0.1:8000`
- [ ] **Check connectivity**: Verify the green dot **API Connected** is visible in top right.

---

## Live Demo Step-by-Step Flow

### Step 1: Overview Tab
- [ ] Point out the **Header Title**: *Personal-Data Discovery & Evidence Inventory (PS-019 · TC-303)*.
- [ ] Point out the **Technical Evidence Scope Banner** (No legal compliance decisions).
- [ ] Note initial stat cards:
  - **Fields Scanned**: `84`
  - **PII Candidates Detected**: `50`
  - **Complete Metadata**: `15`
  - **Evidence Gaps**: `35`
  - **Human Review Required**: `26`

### Step 2: Trigger Live Scan
- [ ] Click **Run Full Scan** button.
- [ ] Observe spinner and toast confirmation: *"Scan complete: 50 candidates discovered across 84 fields."*
- [ ] Demonstrate that the data reloads smoothly without page refreshes.

### Step 3: Personal-Data Inventory Tab
- [ ] Click **Personal-Data Inventory** tab.
- [ ] In the search box, type `email`.
- [ ] Change the Class dropdown to `Contact`.
- [ ] Click the **Details** button on `customers.csv -> email`.
- [ ] Walk through the modal details:
  - Source: `customers.csv`
  - Detected Class: `Contact`
  - Confidence: `1.0000 (High)`
  - Declared Purpose: `Customer account communication...`
  - Declared Retention: `2 years after account closure`
  - Status: `Complete`
- [ ] Close the modal.

### Step 4: Evidence Gaps Tab
- [ ] Click **Evidence Gaps** tab.
- [ ] Filter by **Retention Missing**.
- [ ] Show fields like `salary` or `bank_account` (where purpose is declared, but retention is missing).
- [ ] Filter by **Not Mapped** to show candidates discovered with no entry in `metadata.json`.
- [ ] Explain that gaps are technical governance discrepancies for human review, not legal violations.

### Step 5: Ground-Truth Evaluation Tab
- [ ] Click **Ground-Truth Evaluation** tab.
- [ ] Highlight Binary Detection Metrics:
  - Precision: `80.0%`
  - Recall: `100.0%`
  - F1-Score: `0.889`
- [ ] Show the per-class table and point out the `Sensitive/Health` row:
  - Support: `2`
  - Status: `Limited Sample (Support=2 < 5)` (Demonstrates technical honesty).
- [ ] Scroll down to the **Confusion Matrix** and **Discrepancy Error Records**.

### Step 6: Reports & Downloads Tab
- [ ] Click **Reports & Downloads** tab.
- [ ] Click **Download CSV** on *Evidence Inventory (CSV)* or *Evidence Gaps (CSV)*.
- [ ] Confirm file downloads immediately into browser download folder.

---

## Troubleshooting Quick-Fixes

- **Browser can't connect?** Confirm Uvicorn is running on port 8000 and terminal hasn't paused (press `Enter` in PowerShell if selection mode is paused).
- **Reports missing?** Click **Run Pipeline** in the top navigation bar to regenerate all reports immediately.
