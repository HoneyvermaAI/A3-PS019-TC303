# Hackathon Presentation Script: PS-019 Privacy Evidence Inventory
**Target Duration:** 3 to 4 Minutes  
**Audience:** Technical Judges & Privacy Evaluation Panel  
**Tone:** Confident, precise, truthful, engineering-focused (no marketing fluff)

---

## 0:00 – 0:30 | Hook & Problem Definition

> *"Hello judges. We are presenting our prototype for **PS-019: Personal-Data Discovery and Privacy Evidence Inventory**.*
>
> *Organizations collect personal data across numerous files and databases, but privacy engineering teams struggle with a fundamental challenge: **they don’t have an accurate, real-time inventory of where personal-data fields actually live versus what governance policies claim**.*
>
> *Most teams rely on static spreadsheets that go stale instantly. Our prototype solves this by providing automated technical discovery, mapping candidate fields to declared purpose and retention metadata, highlighting evidence gaps, and evaluating performance against hand-labelled ground truth."*

---

## 0:30 – 1:15 | Architecture & Live Scan Execution

*(Navigate to Dashboard: `http://127.0.0.1:8000`)*

> *"Notice our interface: it is clean, dark-mode cybersecurity themed, and prominently displays our core scope boundary: **this is a technical evidence inventory prototype, not an automated legal compliance decider**.*
>
> *Let's run a live scan across our synthetic assets: three CSV files and three SQLite database tables.*
>
> *(Click **Run Full Scan**)*
>
> *In under two seconds, the engine scanned 84 total fields and identified **50 candidate personal-data fields** using our configurable multi-factor engine:*
> 1. *Column-name normalization for camelCase, snake_case, and kebab-case,*
> 2. *Data-type compatibility hints,*
> 3. *Pattern matching on sampled values (e.g. email regex, international phone, ISO dates).*

---

## 1:15 – 2:00 | Inventory & Governance Metadata Mapping

*(Switch to **Personal-Data Inventory** tab)*

> *"Here in the Personal-Data Inventory, we see all 50 candidate fields across our five technical classes: Identity, Contact, Location, Financial, and Sensitive/Health.*
>
> *Let’s filter by **Contact** and search for `email`.*
>
> *(Click **Details** on `customers.csv -> email`)*
>
> *In this modal, notice what our system unifies:*
> - *Technical evidence: exact keyword match, 100% regex pattern match rate, 1.0 confidence.*
> - *Governance metadata: declared purpose ('Customer account communication') and declared retention ('2 years after account closure').*
> - *Status: Complete.*

---

## 2:00 – 2:45 | Evidence Gaps (The Core Governance Value)

*(Switch to **Evidence Gaps** tab)*

> *"Now let’s look at where privacy risk actually emerges: **Evidence Gaps**.*
>
> *An evidence gap occurs when the scanner discovers a personal data candidate, but the organization’s declared metadata is incomplete or missing.*
>
> *For our 50 candidates, we identified **35 evidence gaps**:*
> - *9 fields with **Retention Missing** (such as employee `salary` or `bank_account`),*
> - *4 fields with **Purpose Missing** (such as `state`),*
> - *3 fields with **Both Missing** (such as `country`),*
> - *19 fields that are **Not Mapped** at all.*
>
> *Crucially, we do not call these 'GDPR violations' or 'Illegal'. We call them **Evidence Gaps requiring human review** — providing actionable engineering evidence for privacy teams."*

---

## 2:45 – 3:30 | Ground-Truth Evaluation & Technical Honesty

*(Switch to **Ground-Truth Evaluation** tab)*

> *"A detection tool is only as good as its measurable accuracy. In Phase 5, we built a one-vs-rest evaluation module benchmarked against 84 hand-labelled ground-truth records.*
>
> *Our real results:*
> - *Binary candidate detection: **80.0% Precision**, **100.0% Recall**, and **0.889 F1-Score**.*
> - *Why 80% precision? Because our scanner intentionally flagged business date fields like `registration_date` as candidates due to date patterns, correctly requiring human triage.*
>
> *Furthermore, look at our per-class metrics:*
> - *Contact, Location, and Financial achieved strong performance.*
> - *For `Sensitive/Health`, notice our status badge: **'Limited Sample (Support=2 < 5)'**. We don't claim universal perfection from two synthetic rows — we clearly report statistical limitations to the user."*

---

## 3:30 – 4:00 | Reports & Wrap-Up

*(Switch to **Reports & Downloads** tab)*

> *"Every report — including the evidence inventory, gaps list, confusion matrix, and error log — is downloadable via secure, path-traversal-protected REST endpoints.*
>
> *In conclusion:*
> - *PS-019 is fully working end-to-end,*
> - *Backed by 87 passing automated tests,*
> - *Architected with FastAPI and vanilla frontend without heavy dependencies,*
> - *And delivers honest, explainable technical evidence for privacy engineering.*
>
> *Thank you, judges. We welcome your questions."*
