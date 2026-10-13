"""
backend/metadata/run_metadata_mapping.py
==========================================
CLI script: runs the complete Phase 4 pipeline.

Steps
-----
1. Run the existing scanner (all CSV files + SQLite database).
2. Load declared metadata from backend/metadata/metadata.json.
3. Map scanner results to metadata using MetadataMapper.
4. Build the unified evidence inventory using EvidenceInventory.
5. Generate the evidence-gap report using GapReportGenerator.
6. Export:
     reports/evidence_inventory.csv
     reports/evidence_gaps.csv
     reports/evidence_inventory.json
7. Print a readable summary to stdout.

Run from the project root:
  python backend/metadata/run_metadata_mapping.py

IMPORTANT: This script provides technical evidence for human review.
It does NOT make legal compliance decisions.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from backend.metadata.gap_report import GapReportGenerator
from backend.metadata.inventory import EvidenceInventory
from backend.metadata.mapper import MetadataMapper
from backend.metadata.models import MetadataStatus
from backend.scanner.detector import FieldDetectionResult
from backend.scanner.scanner_service import FullScanReport, ScannerService


# ---------------------------------------------------------------------------
# Display helpers (ASCII-safe for Windows console)
# ---------------------------------------------------------------------------
LINE_WIDE = "=" * 68
LINE_MED  = "-" * 68


def _status_badge(status: str) -> str:
    badges = {
        MetadataStatus.COMPLETE:        "[COMPLETE ]",
        MetadataStatus.PURPOSE_MISSING: "[PURP-MISS]",
        MetadataStatus.RETENTION_MISSING:"[RET-MISS ]",
        MetadataStatus.BOTH_MISSING:    "[BOTH-MISS]",
        MetadataStatus.NOT_MAPPED:      "[NOT-MAPD ]",
    }
    return badges.get(status, "[?????????]")


def _print_inventory_sample(records, max_rows: int = 10) -> None:
    """Print a sample of inventory records."""
    print()
    print(LINE_WIDE)
    print(f"  EVIDENCE INVENTORY SAMPLE (first {max_rows} records)")
    print(LINE_MED)
    header = f"  {'Source':<32} {'Field':<22} {'Class':<18} {'Conf':>4}  Status"
    print(header)
    print("  " + "-" * 90)
    for r in records[:max_rows]:
        badge = _status_badge(r.overall_status)
        print(
            f"  {r.source_name:<32} {r.field_name:<22} "
            f"{r.detected_class or '':<18} {r.confidence:>4.2f}  {badge}"
        )
    if len(records) > max_rows:
        print(f"  ... and {len(records) - max_rows} more records (see CSV/JSON exports)")


def _print_gap_detail(gaps, max_rows: int = 15) -> None:
    """Print detailed evidence-gap records."""
    print()
    print(LINE_WIDE)
    print(f"  EVIDENCE GAPS DETAIL (first {max_rows})")
    print(LINE_MED)
    for r in gaps[:max_rows]:
        missing = ", ".join(r.missing_items) if r.missing_items else "none"
        print(
            f"  [{r.overall_status:<30}]  "
            f"{r.source_name:<30}  {r.field_name:<22}  missing={missing}"
        )
    if len(gaps) > max_rows:
        print(f"  ... and {len(gaps) - max_rows} more gaps (see evidence_gaps.csv)")


def _print_class_breakdown(records) -> None:
    """Print per-class breakdown of complete vs gap."""
    classes = ["Identity", "Contact", "Location", "Financial", "Sensitive/Health"]
    print()
    print(LINE_WIDE)
    print("  PER-CLASS METADATA STATUS")
    print(LINE_MED)
    print(f"  {'Class':<22}  {'Total':>5}  {'Complete':>8}  {'Gaps':>5}")
    print("  " + "-" * 50)
    for cls in classes:
        cls_records = [r for r in records if r.detected_class == cls]
        complete    = sum(1 for r in cls_records if r.overall_status == MetadataStatus.COMPLETE)
        gaps        = sum(1 for r in cls_records if r.overall_status != MetadataStatus.COMPLETE)
        if cls_records:
            print(f"  {cls:<22}  {len(cls_records):>5}  {complete:>8}  {gaps:>5}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print()
    print(LINE_WIDE)
    print("  PS-019 TC-303 — EVIDENCE INVENTORY & GAP ANALYSIS")
    print("  Purpose and Retention Metadata Mapping")
    print("  Technical evidence for human review only.")
    print("  This tool does NOT make legal compliance decisions.")
    print(LINE_WIDE)

    # ── Step 1: Run the scanner ───────────────────────────────────────
    print("\n[1/6] Running personal-data discovery scanner ...")
    service = ScannerService()
    report: FullScanReport = service.run_full_scan()

    all_results: list[FieldDetectionResult] = report.all_field_results
    candidates  = report.all_detected
    print(f"      Fields scanned    : {len(all_results)}")
    print(f"      PII candidates    : {len(candidates)}")

    # ── Step 2: Load metadata ─────────────────────────────────────────
    print("\n[2/6] Loading declared metadata ...")
    mapper = MetadataMapper()
    print(f"      Metadata records  : {len(mapper.declared_records)}")

    # ── Step 3: Build evidence inventory ─────────────────────────────
    print("\n[3/6] Building evidence inventory ...")
    inv_builder = EvidenceInventory(mapper)
    inventory   = inv_builder.build(all_results)
    print(f"      Inventory records : {len(inventory)}")

    # ── Step 4: Prepare gap report ────────────────────────────────────
    print("\n[4/6] Computing evidence gaps ...")
    reporter = GapReportGenerator(inventory)
    summary  = reporter.build_summary()
    print(f"      Complete          : {summary.complete_count}")
    print(f"      Purpose missing   : {summary.purpose_missing_count}")
    print(f"      Retention missing : {summary.retention_missing_count}")
    print(f"      Both missing      : {summary.both_missing_count}")
    print(f"      Not mapped        : {summary.not_mapped_count}")
    print(f"      Total gaps        : {summary.total_gap_count}")

    # ── Step 5: Export reports ────────────────────────────────────────
    print("\n[5/6] Exporting reports ...")
    csv_path  = reporter.export_inventory_csv()
    gaps_path = reporter.export_gaps_csv()
    json_path = reporter.export_inventory_json()
    print(f"      {csv_path}")
    print(f"      {gaps_path}")
    print(f"      {json_path}")

    # ── Step 6: Print detailed output ─────────────────────────────────
    print("\n[6/6] Generating report output ...")

    _print_inventory_sample(inventory, max_rows=12)
    _print_gap_detail(reporter._gaps, max_rows=15)
    _print_class_breakdown(inventory)

    # Full gap report
    reporter.print_report(summary)

    # ── Final summary ─────────────────────────────────────────────────
    print(LINE_WIDE)
    print("  PIPELINE COMPLETE")
    print(LINE_MED)
    print(f"  PII candidates discovered : {len(candidates)}")
    print(f"  Metadata records loaded   : {len(mapper.declared_records)}")
    print(f"  Inventory records built   : {len(inventory)}")
    print(f"  Evidence gaps identified  : {summary.total_gap_count}")
    print()
    print("  Exports:")
    print(f"    evidence_inventory.csv  -> {csv_path.name}")
    print(f"    evidence_gaps.csv       -> {gaps_path.name}")
    print(f"    evidence_inventory.json -> {json_path.name}")
    print()
    print("  REMINDER: These are technical evidence inventory findings.")
    print("  Missing metadata requires human review.")
    print("  These findings are NOT legal or regulatory compliance findings.")
    print(LINE_WIDE)
    print()


if __name__ == "__main__":
    main()
