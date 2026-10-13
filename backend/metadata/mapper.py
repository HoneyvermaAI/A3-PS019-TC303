"""
backend/metadata/mapper.py
===========================
Metadata mapper for PS-019 TC-303.

Maps scanner-detected candidate fields to declared purpose/retention metadata.
Identifies evidence gaps where declared metadata is absent or incomplete.

SCOPE NOTE
----------
This mapper compares technical scanner output against declared metadata records.
It identifies discrepancies as evidence gaps for human review.
It does NOT assess legal compliance, determine lawful basis, or make
regulatory conclusions of any kind.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from backend.metadata.models import (
    DeclaredMetadata,
    EvidenceGap,
    MetadataStatus,
    PresenceStatus,
)
from backend.scanner.detector import FieldDetectionResult

# ---------------------------------------------------------------------------
# Default metadata path
# ---------------------------------------------------------------------------
_DEFAULT_METADATA_PATH = Path(__file__).parent / "metadata.json"


# ===========================================================================
# MetadataMapper
# ===========================================================================

class MetadataMapper:
    """
    Matches scanner detection results to declared metadata records and
    computes the evidence gap for each candidate personal-data field.

    Matching is performed on a three-part key:
        (source_type, source_name, field_name)

    This prevents false matches when the same column name exists in
    multiple sources (e.g. 'email' in customers.csv vs employees.csv).

    Parameters
    ----------
    metadata_path : Path to metadata.json. Defaults to backend/metadata/metadata.json.
    """

    def __init__(self, metadata_path: str | Path = _DEFAULT_METADATA_PATH) -> None:
        metadata_path = Path(metadata_path)
        if not metadata_path.exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

        raw = self._load_json(metadata_path)
        self._declared: list[DeclaredMetadata] = [
            DeclaredMetadata(**entry) for entry in raw.get("metadata", [])
        ]

        # Build a lookup index keyed by (source_type, source_name, field_name)
        self._index: dict[tuple[str, str, str], DeclaredMetadata] = {
            dm.lookup_key: dm for dm in self._declared
        }

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def declared_records(self) -> list[DeclaredMetadata]:
        """All loaded declared metadata records (read-only)."""
        return list(self._declared)

    def lookup(
        self,
        source_type: str,
        source_name: str,
        field_name: str,
    ) -> Optional[DeclaredMetadata]:
        """
        Return the declared metadata for a specific field, or None if not found.

        Matching is case-sensitive and uses all three key components to avoid
        cross-source false matches.
        """
        return self._index.get((source_type, source_name, field_name))

    def map_field(self, result: FieldDetectionResult) -> EvidenceGap:
        """
        Produce an EvidenceGap for a single scanner detection result.

        Logic
        -----
        1. Look up declared metadata using the three-part key.
        2. If no record found → status = Not Mapped.
        3. If record found, check purpose and retention individually.
        4. Determine overall status based on what is missing.
        5. Build a neutral evidence_note (no legal language).
        """
        declared = self.lookup(result.source_type, result.source_name, result.field_name)

        if declared is None:
            return self._build_not_mapped_gap(result)

        return self._build_gap_from_declared(result, declared)

    def map_all(
        self, results: list[FieldDetectionResult]
    ) -> list[EvidenceGap]:
        """
        Map a list of scanner results to evidence gaps.
        Only processes results where detected_class is not None.
        """
        return [
            self.map_field(r)
            for r in results
            if r.detected_class is not None
        ]

    # ------------------------------------------------------------------
    # Private — gap builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_not_mapped_gap(result: FieldDetectionResult) -> EvidenceGap:
        """No declared metadata record found for this field."""
        note = (
            f"No declared metadata record found for "
            f"'{result.field_name}' in '{result.source_name}'. "
            "Evidence gap — human review required to determine whether "
            "purpose and retention metadata should be declared for this field."
        )
        return EvidenceGap(
            source_type      = result.source_type,
            source_name      = result.source_name,
            field_name       = result.field_name,
            detected_class   = result.detected_class,
            confidence       = result.confidence,
            purpose_status   = PresenceStatus.NOT_DECLARED,
            retention_status = PresenceStatus.NOT_DECLARED,
            overall_status   = MetadataStatus.NOT_MAPPED,
            missing_items    = ["purpose", "retention_period"],
            evidence_note    = note,
        )

    @staticmethod
    def _build_gap_from_declared(
        result:   FieldDetectionResult,
        declared: DeclaredMetadata,
    ) -> EvidenceGap:
        """Metadata record exists — check which items are present or absent."""
        purpose_present   = bool(declared.purpose and declared.purpose.strip())
        retention_present = bool(declared.retention_period and declared.retention_period.strip())

        purpose_status   = PresenceStatus.PRESENT if purpose_present   else PresenceStatus.MISSING
        retention_status = PresenceStatus.PRESENT if retention_present else PresenceStatus.MISSING

        missing_items: list[str] = []
        if not purpose_present:
            missing_items.append("purpose")
        if not retention_present:
            missing_items.append("retention_period")

        # Determine overall status
        if not missing_items:
            overall = MetadataStatus.COMPLETE
        elif "purpose" in missing_items and "retention_period" in missing_items:
            overall = MetadataStatus.BOTH_MISSING
        elif "purpose" in missing_items:
            overall = MetadataStatus.PURPOSE_MISSING
        else:
            overall = MetadataStatus.RETENTION_MISSING

        # Build neutral evidence note
        note = MetadataMapper._build_note(result.field_name, result.source_name, overall, missing_items)

        return EvidenceGap(
            source_type      = result.source_type,
            source_name      = result.source_name,
            field_name       = result.field_name,
            detected_class   = result.detected_class,
            confidence       = result.confidence,
            purpose_status   = purpose_status,
            retention_status = retention_status,
            overall_status   = overall,
            missing_items    = missing_items,
            evidence_note    = note,
        )

    @staticmethod
    def _build_note(
        field_name: str,
        source_name: str,
        overall: MetadataStatus,
        missing_items: list[str],
    ) -> str:
        """
        Build a neutral, non-legal evidence note for the inventory record.

        The note describes what metadata is present or absent. It uses
        evidence-inventory terminology and does not make compliance assertions.
        """
        if overall == MetadataStatus.COMPLETE:
            return (
                f"Purpose and retention metadata are declared for "
                f"'{field_name}' in '{source_name}'. No evidence gap."
            )

        if overall == MetadataStatus.PURPOSE_MISSING:
            return (
                f"Retention metadata is declared for '{field_name}' in '{source_name}', "
                "but purpose metadata is not declared. "
                "Evidence gap — human review required."
            )

        if overall == MetadataStatus.RETENTION_MISSING:
            return (
                f"Purpose metadata is declared for '{field_name}' in '{source_name}', "
                "but retention period metadata is not declared. "
                "Evidence gap — human review required."
            )

        if overall == MetadataStatus.BOTH_MISSING:
            return (
                f"A metadata record exists for '{field_name}' in '{source_name}', "
                "but neither purpose nor retention period has been declared. "
                "Evidence gap — human review required."
            )

        # NOT_MAPPED (fallback — shouldn't reach here via _build_gap_from_declared)
        return (
            f"No declared metadata found for '{field_name}' in '{source_name}'. "
            "Evidence gap — human review required."
        )

    # ------------------------------------------------------------------
    # Private — JSON loader
    # ------------------------------------------------------------------

    @staticmethod
    def _load_json(path: Path) -> dict:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
