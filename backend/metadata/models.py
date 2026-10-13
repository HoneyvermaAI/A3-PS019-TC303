"""
backend/metadata/models.py
===========================
Pydantic data models for Phase 4 — Purpose & Retention Metadata Mapping.

SCOPE NOTE
----------
These models represent TECHNICAL metadata inventory data only.
Missing metadata is classified as an evidence gap for human review.
No model field, value, or label implies legal compliance status.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ===========================================================================
# Declared metadata model
# ===========================================================================

class DeclaredMetadata(BaseModel):
    """
    A single declared metadata record as loaded from metadata.json.

    Represents what the organisation has *explicitly stated* about a field's
    processing purpose and retention period. Both fields are Optional because
    the presence of a partial record (purpose present, retention absent, or
    vice-versa) is itself meaningful evidence to be captured.
    """

    source_type: str = Field(
        description="'CSV' or 'SQL' — must match the scanner source_type exactly."
    )
    source_name: str = Field(
        description="File or db:table name — must match the scanner source_name exactly."
    )
    field_name: str = Field(
        description="Column name — must match the scanner field_name exactly."
    )
    purpose: Optional[str] = Field(
        default=None,
        description="Declared business or operational purpose for processing this field.",
    )
    retention_period: Optional[str] = Field(
        default=None,
        description="Declared retention period (human-readable string). None = not declared.",
    )
    metadata_owner: Optional[str] = Field(
        default=None,
        description="Team or role responsible for this metadata record.",
    )
    notice_version: Optional[str] = Field(
        default=None,
        description="Version of the privacy notice under which this field is covered.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Free-text notes from the metadata owner.",
    )

    @property
    def lookup_key(self) -> tuple[str, str, str]:
        """(source_type, source_name, field_name) — used for mapper index lookup."""
        return (self.source_type, self.source_name, self.field_name)


# ===========================================================================
# Metadata status enumeration
# ===========================================================================

class MetadataStatus(str, Enum):
    """
    Technical status of the metadata record for a detected candidate field.

    These are evidence-inventory labels. They indicate the presence or absence
    of declared metadata. They do NOT indicate legal compliance or violation.
    """

    COMPLETE              = "Complete"
    PURPOSE_MISSING       = "Purpose Missing"
    RETENTION_MISSING     = "Retention Missing"
    BOTH_MISSING          = "Purpose & Retention Missing"
    NOT_MAPPED            = "Not Mapped"


class PresenceStatus(str, Enum):
    """Status of a single metadata item (purpose or retention)."""
    PRESENT     = "Present"
    MISSING     = "Missing"
    NOT_DECLARED= "Not Declared"


# ===========================================================================
# Evidence gap model
# ===========================================================================

class EvidenceGap(BaseModel):
    """
    Represents a technical evidence gap: a candidate personal-data field
    for which declared metadata is absent or incomplete.

    IMPORTANT: An evidence gap is a technical observation. It is NOT a
    compliance finding, a legal violation determination, or a regulatory
    assessment of any kind.
    """

    source_type:      str = Field(description="'CSV' or 'SQL'.")
    source_name:      str = Field(description="File or db:table name.")
    field_name:       str = Field(description="Column / field name.")
    detected_class:   Optional[str] = Field(default=None, description="Detected personal-data class.")
    confidence:       float = Field(ge=0.0, le=1.0)
    purpose_status:   str = Field(description="'Present', 'Missing', or 'Not Declared'.")
    retention_status: str = Field(description="'Present', 'Missing', or 'Not Declared'.")
    overall_status:   str = Field(description="One of the MetadataStatus values.")
    missing_items:    list[str] = Field(
        default_factory=list,
        description="List of metadata items not declared (e.g. ['purpose', 'retention_period']).",
    )
    evidence_note:    str = Field(
        description=(
            "Human-readable technical note describing the evidence gap. "
            "Uses neutral language — no legal compliance conclusions."
        )
    )


# ===========================================================================
# Full evidence inventory record
# ===========================================================================

class InventoryRecord(BaseModel):
    """
    A single row in the unified evidence inventory.
    Combines scanner detection output with declared metadata (or its absence).

    This record is the primary output of Phase 4 and feeds CSV/JSON reports.
    """

    # ── Source identification ──────────────────────────────────────────────
    source_type:      str
    source_name:      str
    field_name:       str

    # ── Scanner detection output ───────────────────────────────────────────
    detected_class:   Optional[str] = None
    confidence:       float = Field(ge=0.0, le=1.0)
    confidence_level: str
    review_required:  bool
    detection_reason: str

    # ── Declared metadata ──────────────────────────────────────────────────
    purpose:          Optional[str] = None
    retention_period: Optional[str] = None
    metadata_owner:   Optional[str] = None
    notice_version:   Optional[str] = None

    # ── Metadata status ────────────────────────────────────────────────────
    purpose_status:   str = Field(description="'Present', 'Missing', or 'Not Declared'.")
    retention_status: str = Field(description="'Present', 'Missing', or 'Not Declared'.")
    overall_status:   str = Field(description="MetadataStatus label.")
    missing_items:    list[str] = Field(default_factory=list)

    # ── Human-review note ──────────────────────────────────────────────────
    evidence_note:    str


# ===========================================================================
# Gap report summary model
# ===========================================================================

class GapReportSummary(BaseModel):
    """
    Aggregated statistics for the evidence-gap report.

    All counts are technical observations. No count implies a legal
    compliance quantity or violation count.
    """

    generated_at:            str
    total_candidates:        int
    complete_count:          int
    purpose_missing_count:   int
    retention_missing_count: int
    both_missing_count:      int
    not_mapped_count:        int
    total_gap_count:         int

    gaps_by_class:  dict[str, int] = Field(default_factory=dict)
    gaps_by_source: dict[str, int] = Field(default_factory=dict)
    gaps_by_status: dict[str, int] = Field(default_factory=dict)

    disclaimer: str = (
        "These results are technical evidence inventory findings. "
        "Evidence gaps indicate missing declared metadata and require human review. "
        "They are NOT legal or regulatory compliance findings."
    )
