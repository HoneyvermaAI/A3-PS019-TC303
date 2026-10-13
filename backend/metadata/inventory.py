"""
backend/metadata/inventory.py
==============================
Evidence inventory builder for PS-019 TC-303.

Combines scanner detection results with mapped metadata to produce
a unified InventoryRecord for every candidate personal-data field.

SCOPE NOTE
----------
This module generates a TECHNICAL evidence inventory only.
Missing metadata is reported as an evidence gap. It is NOT interpreted
as a legal or regulatory compliance finding.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from backend.metadata.mapper import MetadataMapper
from backend.metadata.models import (
    DeclaredMetadata,
    EvidenceGap,
    InventoryRecord,
    MetadataStatus,
    PresenceStatus,
)
from backend.scanner.detector import FieldDetectionResult


class EvidenceInventory:
    """
    Builds the unified evidence inventory by combining:
      - Scanner detection results (FieldDetectionResult)
      - Declared metadata (via MetadataMapper)

    The inventory covers EVERY detected candidate field (detected_class
    is not None) regardless of whether declared metadata exists.

    Parameters
    ----------
    mapper : A configured MetadataMapper instance.
    """

    def __init__(self, mapper: MetadataMapper) -> None:
        self._mapper = mapper

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def build(
        self,
        detection_results: list[FieldDetectionResult],
    ) -> list[InventoryRecord]:
        """
        Process a flat list of scanner results and return one
        InventoryRecord per detected candidate field.

        Fields where detected_class is None (below confidence threshold)
        are skipped — they are not candidate personal-data fields.

        Parameters
        ----------
        detection_results : Flat list of FieldDetectionResult objects from
                            the CSV scanner, SQL scanner, or both.

        Returns
        -------
        List of InventoryRecord, sorted by source_name then field_name.
        """
        records: list[InventoryRecord] = []

        for result in detection_results:
            if result.detected_class is None:
                continue  # Not a PII candidate — skip

            gap: EvidenceGap = self._mapper.map_field(result)
            declared: Optional[DeclaredMetadata] = self._mapper.lookup(
                result.source_type, result.source_name, result.field_name
            )

            record = InventoryRecord(
                # Source identification
                source_type      = result.source_type,
                source_name      = result.source_name,
                field_name       = result.field_name,

                # Scanner detection output
                detected_class   = result.detected_class,
                confidence       = result.confidence,
                confidence_level = result.confidence_level,
                review_required  = result.review_required,
                detection_reason = result.reason,

                # Declared metadata (None if not declared)
                purpose          = declared.purpose if declared else None,
                retention_period = declared.retention_period if declared else None,
                metadata_owner   = declared.metadata_owner if declared else None,
                notice_version   = declared.notice_version if declared else None,

                # Metadata status (from gap analysis)
                purpose_status   = gap.purpose_status,
                retention_status = gap.retention_status,
                overall_status   = gap.overall_status,
                missing_items    = gap.missing_items,

                # Human-review note (neutral language)
                evidence_note    = gap.evidence_note,
            )
            records.append(record)

        # Sort for consistent, readable output
        records.sort(key=lambda r: (r.source_name, r.field_name))
        return records

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    @staticmethod
    def filter_gaps(records: list[InventoryRecord]) -> list[InventoryRecord]:
        """Return only records with an evidence gap (overall_status != Complete)."""
        return [r for r in records if r.overall_status != MetadataStatus.COMPLETE]

    @staticmethod
    def group_by_class(
        records: list[InventoryRecord],
    ) -> dict[str, list[InventoryRecord]]:
        """Group inventory records by detected_class."""
        grouped: dict[str, list[InventoryRecord]] = {}
        for r in records:
            key = r.detected_class or "Unclassified"
            grouped.setdefault(key, []).append(r)
        return grouped

    @staticmethod
    def group_by_source(
        records: list[InventoryRecord],
    ) -> dict[str, list[InventoryRecord]]:
        """Group inventory records by source_name."""
        grouped: dict[str, list[InventoryRecord]] = {}
        for r in records:
            grouped.setdefault(r.source_name, []).append(r)
        return grouped
