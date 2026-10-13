"""
backend/metadata/gap_report.py
================================
Evidence-gap report generator for PS-019 TC-303.

Computes summary statistics and exports structured reports from the
evidence inventory. Only records with evidence gaps are included in
the gap-specific outputs.

SCOPE NOTE
----------
This report identifies TECHNICAL evidence gaps — fields where declared
purpose and/or retention metadata is absent. Gap counts are inventory
metrics only. They are NOT legal or regulatory compliance counts.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from backend.metadata.models import (
    GapReportSummary,
    InventoryRecord,
    MetadataStatus,
)

# ---------------------------------------------------------------------------
# Default report output paths
# ---------------------------------------------------------------------------
_PROJECT_ROOT      = Path(__file__).parent.parent.parent
_REPORTS_DIR       = _PROJECT_ROOT / "reports"
_INVENTORY_CSV     = _REPORTS_DIR / "evidence_inventory.csv"
_GAPS_CSV          = _REPORTS_DIR / "evidence_gaps.csv"
_INVENTORY_JSON    = _REPORTS_DIR / "evidence_inventory.json"


# ===========================================================================
# GapReportGenerator
# ===========================================================================

class GapReportGenerator:
    """
    Generates summary statistics, CSV exports, and JSON exports from a
    completed evidence inventory.

    Parameters
    ----------
    inventory_records : Full inventory (all candidate fields, complete or not).
    """

    # Ordered classes for consistent display
    DISPLAY_CLASSES = [
        "Identity", "Contact", "Location", "Financial", "Sensitive/Health"
    ]

    def __init__(self, inventory_records: list[InventoryRecord]) -> None:
        self._all = inventory_records
        self._gaps = [r for r in inventory_records if r.overall_status != MetadataStatus.COMPLETE]

    # ------------------------------------------------------------------
    # Summary statistics
    # ------------------------------------------------------------------

    def build_summary(self) -> GapReportSummary:
        """Compute aggregated gap statistics."""
        all_    = self._all
        gaps    = self._gaps

        complete_count          = sum(1 for r in all_ if r.overall_status == MetadataStatus.COMPLETE)
        purpose_missing_count   = sum(1 for r in gaps if r.overall_status == MetadataStatus.PURPOSE_MISSING)
        retention_missing_count = sum(1 for r in gaps if r.overall_status == MetadataStatus.RETENTION_MISSING)
        both_missing_count      = sum(1 for r in gaps if r.overall_status == MetadataStatus.BOTH_MISSING)
        not_mapped_count        = sum(1 for r in gaps if r.overall_status == MetadataStatus.NOT_MAPPED)

        # Gaps by detected class
        gaps_by_class: dict[str, int] = {}
        for r in gaps:
            key = r.detected_class or "Unclassified"
            gaps_by_class[key] = gaps_by_class.get(key, 0) + 1

        # Gaps by source
        gaps_by_source: dict[str, int] = {}
        for r in gaps:
            gaps_by_source[r.source_name] = gaps_by_source.get(r.source_name, 0) + 1

        # Gaps by status type
        gaps_by_status: dict[str, int] = {
            MetadataStatus.PURPOSE_MISSING:   purpose_missing_count,
            MetadataStatus.RETENTION_MISSING: retention_missing_count,
            MetadataStatus.BOTH_MISSING:      both_missing_count,
            MetadataStatus.NOT_MAPPED:        not_mapped_count,
        }

        return GapReportSummary(
            generated_at            = datetime.now(timezone.utc).isoformat(),
            total_candidates        = len(all_),
            complete_count          = complete_count,
            purpose_missing_count   = purpose_missing_count,
            retention_missing_count = retention_missing_count,
            both_missing_count      = both_missing_count,
            not_mapped_count        = not_mapped_count,
            total_gap_count         = len(gaps),
            gaps_by_class           = gaps_by_class,
            gaps_by_source          = gaps_by_source,
            gaps_by_status          = gaps_by_status,
        )

    # ------------------------------------------------------------------
    # CSV exports
    # ------------------------------------------------------------------

    _INVENTORY_COLUMNS = [
        "source_type", "source_name", "field_name",
        "detected_class", "confidence", "confidence_level", "review_required",
        "purpose", "retention_period", "metadata_owner", "notice_version",
        "purpose_status", "retention_status", "overall_status",
        "missing_items", "detection_reason", "evidence_note",
    ]

    _GAP_COLUMNS = [
        "source_type", "source_name", "field_name",
        "detected_class", "confidence", "confidence_level",
        "purpose_status", "retention_status", "overall_status",
        "missing_items", "purpose", "retention_period",
        "metadata_owner", "evidence_note",
    ]

    def export_inventory_csv(self, path: str | Path = _INVENTORY_CSV) -> Path:
        """Write the full inventory (all candidate fields) to a CSV file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self._INVENTORY_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            for r in self._all:
                writer.writerow(self._record_to_dict(r))
        return path

    def export_gaps_csv(self, path: str | Path = _GAPS_CSV) -> Path:
        """Write only evidence-gap records to a CSV file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self._GAP_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            for r in self._gaps:
                writer.writerow(self._record_to_dict(r))
        return path

    # ------------------------------------------------------------------
    # JSON export
    # ------------------------------------------------------------------

    def export_inventory_json(self, path: str | Path = _INVENTORY_JSON) -> Path:
        """Write the full inventory plus summary to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        summary = self.build_summary()
        payload: dict[str, Any] = {
            "generated_at": summary.generated_at,
            "disclaimer": summary.disclaimer,
            "summary": summary.model_dump(exclude={"disclaimer"}),
            "inventory": [self._record_to_dict(r) for r in self._all],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return path

    # ------------------------------------------------------------------
    # CLI-printable report
    # ------------------------------------------------------------------

    def print_report(self, summary: Optional[GapReportSummary] = None) -> None:
        """Print an ASCII-safe, readable gap report to stdout."""
        if summary is None:
            summary = self.build_summary()

        LINE = "=" * 64
        SEP  = "-" * 64

        print()
        print(LINE)
        print("  EVIDENCE GAP REPORT  (PS-019 TC-303)")
        print(SEP)
        print(f"  Generated  : {summary.generated_at[:19].replace('T',' ')} UTC")
        print(f"  Candidates : {summary.total_candidates}")
        print(f"  Complete   : {summary.complete_count}")
        print(SEP)
        print("  Gap breakdown:")
        print(f"    Purpose missing            : {summary.purpose_missing_count}")
        print(f"    Retention missing          : {summary.retention_missing_count}")
        print(f"    Purpose & Retention missing: {summary.both_missing_count}")
        print(f"    Not mapped (no record)     : {summary.not_mapped_count}")
        print(f"    --------------------------------")
        print(f"    Total evidence gaps        : {summary.total_gap_count}")
        print()
        print("  Gaps by detected class:")
        for cls in self.DISPLAY_CLASSES:
            n = summary.gaps_by_class.get(cls, 0)
            bar = "#" * n
            print(f"    {cls:<22} {n:>3}  {bar}")
        unclassified = summary.gaps_by_class.get("Unclassified", 0)
        if unclassified:
            print(f"    {'Unclassified':<22} {unclassified:>3}")

        print()
        print("  Gaps by source:")
        for src, n in sorted(summary.gaps_by_source.items()):
            print(f"    {src:<40} {n:>3}")

        print()
        print(LINE)
        print("  IMPORTANT DISCLAIMER")
        print(SEP)
        print("  These results are TECHNICAL EVIDENCE INVENTORY findings.")
        print("  Evidence gaps indicate missing declared metadata.")
        print("  They require human review.")
        print("  They are NOT legal or regulatory compliance findings.")
        print(LINE)
        print()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _record_to_dict(r: InventoryRecord) -> dict:
        return {
            "source_type":      r.source_type,
            "source_name":      r.source_name,
            "field_name":       r.field_name,
            "detected_class":   r.detected_class or "",
            "confidence":       r.confidence,
            "confidence_level": r.confidence_level,
            "review_required":  r.review_required,
            "purpose":          r.purpose or "",
            "retention_period": r.retention_period or "",
            "metadata_owner":   r.metadata_owner or "",
            "notice_version":   r.notice_version or "",
            "purpose_status":   r.purpose_status,
            "retention_status": r.retention_status,
            "overall_status":   r.overall_status,
            "missing_items":    "; ".join(r.missing_items),
            "detection_reason": r.detection_reason,
            "evidence_note":    r.evidence_note,
        }
