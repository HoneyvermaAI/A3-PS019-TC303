"""
backend/scanner/run_scan.py
============================
CLI scanner for PS-019 TC-303.

Scans all synthetic CSV files and the SQLite demo database, then prints
a human-readable evidence report.

Run from the project root:
  python backend/scanner/run_scan.py

IMPORTANT: This tool provides technical evidence for human review.
It does NOT make legal compliance decisions.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# Ensure project root is on sys.path so relative imports work
_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from backend.scanner.detector import FieldDetectionResult
from backend.scanner.scanner_service import (
    CSVScanResult,
    FullScanReport,
    SQLScanResult,
    ScannerService,
)

# ---------------------------------------------------------------------------
# Ordered class display list
# ---------------------------------------------------------------------------
DISPLAY_CLASSES = [
    "Identity",
    "Contact",
    "Location",
    "Financial",
    "Sensitive/Health",
]

# ---------------------------------------------------------------------------
# Formatting helpers  (ASCII-only for Windows console compatibility)
# ---------------------------------------------------------------------------

LINE_WIDE  = "=" * 68
LINE_MED   = "-" * 68
LINE_THIN  = "." * 68


def _confidence_badge(level: str) -> str:
    badges = {"High": "[HIGH]", "Medium": "[MED] ", "Low": "[LOW] ", "None": "[----]"}
    return badges.get(level, "[?]  ")


def _print_field_row(r: FieldDetectionResult, indent: int = 4) -> None:
    pad = " " * indent
    badge  = _confidence_badge(r.confidence_level)
    review = " [REVIEW]" if r.review_required else ""
    rate   = (
        f"  pattern_rate={r.pattern_match_rate:.0%}"
        if r.pattern_match_rate is not None
        else ""
    )
    kw = f"  kw={r.evidence.keyword_match_type}" if r.evidence.keyword_match_type else ""
    print(f"{pad}{badge}  {r.field_name:<30}  conf={r.confidence:.2f}{kw}{rate}{review}")


def _print_csv_result(csv_result: CSVScanResult) -> None:
    print()
    print(LINE_WIDE)
    print(f"  Source (CSV): {csv_result.source_name}")
    print(f"  Fields scanned: {len(csv_result.field_results)}")
    print(LINE_MED)

    # Group detected by class
    by_class: dict[str, list[FieldDetectionResult]] = {}
    for r in csv_result.field_results:
        if r.detected_class:
            by_class.setdefault(r.detected_class, []).append(r)

    for cls in DISPLAY_CLASSES:
        fields = by_class.get(cls, [])
        print(f"\n  [{cls}]")
        if fields:
            for r in fields:
                _print_field_row(r)
        else:
            print("      (none detected)")

    # Non-personal fields
    non_pii = [r for r in csv_result.field_results if r.detected_class is None]
    print(f"\n  [Non-personal / Below threshold]")
    if non_pii:
        for r in non_pii:
            print(f"      {r.field_name:<30}  conf={r.confidence:.2f}")
    else:
        print("      (all fields classified)")


def _print_sql_result(sql_result: SQLScanResult) -> None:
    print()
    print(LINE_WIDE)
    print(f"  Source (SQL): {sql_result.db_name}")
    print(f"  Tables: {', '.join(sql_result.tables.keys())}")
    print(LINE_MED)

    for table_name, results in sql_result.tables.items():
        print(f"\n  Table: {table_name}  ({len(results)} columns)")
        print("  " + "-" * 50)

        by_class: dict[str, list[FieldDetectionResult]] = {}
        for r in results:
            if r.detected_class:
                by_class.setdefault(r.detected_class, []).append(r)

        for cls in DISPLAY_CLASSES:
            fields = by_class.get(cls, [])
            if fields:
                print(f"    [{cls}]")
                for r in fields:
                    _print_field_row(r, indent=6)

        non_pii = [r for r in results if r.detected_class is None]
        if non_pii:
            print(f"    [Non-personal / Below threshold]")
            for r in non_pii:
                print(f"        {r.field_name:<30}  conf={r.confidence:.2f}")


def _print_review_section(report: FullScanReport) -> None:
    review_fields = report.all_review_required
    print()
    print(LINE_WIDE)
    print("  FIELDS REQUIRING HUMAN REVIEW")
    print(LINE_MED)
    if not review_fields:
        print("  None — all detections are high-confidence.")
        return

    for r in review_fields:
        kw_type = r.evidence.keyword_match_type or "none"
        pat_rate = (
            f"pattern_rate={r.pattern_match_rate:.0%}"
            if r.pattern_match_rate is not None
            else "no_pattern_checked"
        )
        cls = r.detected_class or "unclassified"
        print(
            f"  {r.source_name:<30}  {r.field_name:<25}  "
            f"class={cls:<18}  conf={r.confidence:.2f}  kw={kw_type}  {pat_rate}"
        )


def _print_summary(report: FullScanReport) -> None:
    all_results  = report.all_field_results
    all_detected = report.all_detected
    review_count = len(report.all_review_required)

    by_class = report.detected_by_class()

    print()
    print(LINE_WIDE)
    print("  SUMMARY")
    print(LINE_MED)
    print(f"  Total fields scanned      : {len(all_results)}")
    print(f"  Personal-data candidates  : {len(all_detected)}")
    print(f"  Fields requiring review   : {review_count}")
    print()
    print("  Detections by class:")
    for cls in DISPLAY_CLASSES:
        n = len(by_class.get(cls, []))
        bar = "#" * n
        print(f"    {cls:<22} {n:>3}  {bar}")
    print()
    print("  High-confidence detections only (conf >= 0.75):")
    high = [r for r in all_detected if r.confidence_level == "High"]
    for cls in DISPLAY_CLASSES:
        n = sum(1 for r in high if r.detected_class == cls)
        if n:
            print(f"    {cls:<22} {n:>3}")
    print()


def _print_evidence_detail(report: FullScanReport, max_fields: int = 5) -> None:
    """Print detailed evidence for a sample of detected fields."""
    print(LINE_WIDE)
    print(f"  EVIDENCE DETAIL (sample of up to {max_fields} detected fields)")
    print(LINE_MED)
    sample = report.all_detected[:max_fields]
    for r in sample:
        print(f"\n  Field       : {r.field_name}  ({r.source_name})")
        print(f"  Class       : {r.detected_class}")
        print(f"  Confidence  : {r.confidence:.4f}  [{r.confidence_level}]")
        print(f"  Review req. : {r.review_required}")
        e = r.evidence
        print(f"  Evidence:")
        print(f"    keyword_match      : {e.keyword_match}  ({e.keyword_match_type})")
        print(f"    keyword_score      : {e.keyword_score:.2f}")
        print(f"    pattern_name       : {e.pattern_name}")
        print(f"    pattern_match_rate : {e.pattern_match_rate}")
        print(f"    pattern_score      : {e.pattern_score:.2f}")
        print(f"    dtype              : {e.dtype}  (score={e.dtype_score:.2f})")
        print(f"  Reason      : {r.reason}")
    print()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print()
    print(LINE_WIDE)
    print("  PERSONAL-DATA DISCOVERY SCANNER")
    print("  PS-019 TC-303 -- Technical Evidence Report")
    print("  This tool identifies candidate fields for human review.")
    print("  It does NOT make legal compliance decisions.")
    print(LINE_WIDE)

    service = ScannerService()

    print("\nRunning full scan (CSV files + SQLite database) ...")
    report: FullScanReport = service.run_full_scan()

    # ── CSV results ───────────────────────────────────────────────────
    for csv_result in report.csv_results:
        _print_csv_result(csv_result)

    # ── SQL results ───────────────────────────────────────────────────
    for sql_result in report.sql_results:
        _print_sql_result(sql_result)

    # ── Review-required ───────────────────────────────────────────────
    _print_review_section(report)

    # ── Evidence detail ───────────────────────────────────────────────
    _print_evidence_detail(report, max_fields=5)

    # ── Summary ───────────────────────────────────────────────────────
    _print_summary(report)

    print(LINE_WIDE)
    print("  Scan complete. All results are technical evidence only.")
    print(LINE_WIDE)
    print()


if __name__ == "__main__":
    main()
