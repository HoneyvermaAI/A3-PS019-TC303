"""
tests/test_metadata_mapper.py
==============================
Unit tests for Phase 4 — Purpose & Retention Metadata Mapping.

All test data is entirely synthetic. No real personal information is used.
All tests verify that the mapper uses neutral, non-legal language.

Run:
  pytest tests/test_metadata_mapper.py -v
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest

from backend.metadata.mapper import MetadataMapper
from backend.metadata.models import (
    DeclaredMetadata,
    EvidenceGap,
    GapReportSummary,
    InventoryRecord,
    MetadataStatus,
    PresenceStatus,
)
from backend.metadata.inventory import EvidenceInventory
from backend.metadata.gap_report import GapReportGenerator
from backend.scanner.detector import EvidenceDetail, FieldDetectionResult

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
METADATA_PATH = Path(__file__).parent.parent / "backend" / "metadata" / "metadata.json"

# ---------------------------------------------------------------------------
# Helpers — build synthetic FieldDetectionResult
# ---------------------------------------------------------------------------

def _make_result(
    source_type: str,
    source_name: str,
    field_name: str,
    detected_class: Optional[str] = "Contact",
    confidence: float = 0.90,
) -> FieldDetectionResult:
    """Build a minimal synthetic FieldDetectionResult for testing."""
    return FieldDetectionResult(
        source_type      = source_type,
        source_name      = source_name,
        field_name       = field_name,
        detected_class   = detected_class,
        confidence       = confidence,
        confidence_level = "High" if confidence >= 0.75 else "Medium",
        review_required  = confidence < 0.75,
        evidence         = EvidenceDetail(
            keyword_match      = True,
            keyword_match_type = "exact",
            keyword_score      = 0.70,
            pattern_matched    = True,
            pattern_name       = "email",
            pattern_match_rate = 0.95,
            pattern_score      = 0.30,
            dtype              = "object",
            dtype_score        = 0.05,
        ),
        sample_count      = 100,
        non_null_count    = 98,
        pattern_match_rate= 0.95,
        reason            = "Test synthetic reason.",
    )


def _make_declared(
    source_type: str,
    source_name: str,
    field_name: str,
    purpose: Optional[str] = "Test purpose",
    retention_period: Optional[str] = "2 years",
    metadata_owner: Optional[str] = "Test Team",
) -> DeclaredMetadata:
    """Build a synthetic DeclaredMetadata object for in-memory testing."""
    return DeclaredMetadata(
        source_type      = source_type,
        source_name      = source_name,
        field_name       = field_name,
        purpose          = purpose,
        retention_period = retention_period,
        metadata_owner   = metadata_owner,
        notice_version   = "v1.0",
        notes            = None,
    )


class InMemoryMapper(MetadataMapper):
    """
    A MetadataMapper subclass that uses an in-memory list of DeclaredMetadata
    instead of loading from a JSON file. Used in unit tests to avoid
    dependency on the real metadata.json file content.
    """

    def __init__(self, declared: list[DeclaredMetadata]) -> None:
        # Bypass the file-loading __init__; set attributes directly
        self._declared = declared
        self._index = {dm.lookup_key: dm for dm in declared}


# ===========================================================================
# 1. Complete metadata mapping
# ===========================================================================

def test_complete_metadata_mapping() -> None:
    """Both purpose and retention declared → status Complete, no missing items."""
    mapper = InMemoryMapper([
        _make_declared("CSV", "test.csv", "email", "Comms", "2 years"),
    ])
    result = _make_result("CSV", "test.csv", "email")
    gap    = mapper.map_field(result)

    assert gap.overall_status   == MetadataStatus.COMPLETE
    assert gap.purpose_status   == PresenceStatus.PRESENT
    assert gap.retention_status == PresenceStatus.PRESENT
    assert gap.missing_items    == []


def test_complete_mapping_has_no_evidence_gap_note() -> None:
    """A complete record's evidence_note must say 'No evidence gap'."""
    mapper = InMemoryMapper([
        _make_declared("CSV", "test.csv", "email", "Comms", "2 years"),
    ])
    gap = mapper.map_field(_make_result("CSV", "test.csv", "email"))
    assert "No evidence gap" in gap.evidence_note


# ===========================================================================
# 2. Purpose missing
# ===========================================================================

def test_purpose_missing() -> None:
    """Purpose is null → status Purpose Missing."""
    mapper = InMemoryMapper([
        _make_declared("CSV", "test.csv", "phone", purpose=None, retention_period="1 year"),
    ])
    gap = mapper.map_field(_make_result("CSV", "test.csv", "phone"))

    assert gap.overall_status   == MetadataStatus.PURPOSE_MISSING
    assert gap.purpose_status   == PresenceStatus.MISSING
    assert gap.retention_status == PresenceStatus.PRESENT
    assert "purpose" in gap.missing_items
    assert "retention_period" not in gap.missing_items


def test_purpose_missing_note_is_neutral() -> None:
    """Purpose-missing evidence note must reference purpose and be neutral."""
    mapper = InMemoryMapper([
        _make_declared("CSV", "test.csv", "phone", purpose=None, retention_period="1 year"),
    ])
    gap = mapper.map_field(_make_result("CSV", "test.csv", "phone"))
    note = gap.evidence_note.lower()
    assert "purpose" in note
    assert "human review" in note


# ===========================================================================
# 3. Retention missing
# ===========================================================================

def test_retention_missing() -> None:
    """Retention is null → status Retention Missing."""
    mapper = InMemoryMapper([
        _make_declared("CSV", "test.csv", "salary", purpose="Payroll", retention_period=None),
    ])
    gap = mapper.map_field(_make_result("CSV", "test.csv", "salary", detected_class="Financial"))

    assert gap.overall_status   == MetadataStatus.RETENTION_MISSING
    assert gap.purpose_status   == PresenceStatus.PRESENT
    assert gap.retention_status == PresenceStatus.MISSING
    assert "retention_period" in gap.missing_items
    assert "purpose" not in gap.missing_items


def test_retention_missing_note_is_neutral() -> None:
    """Retention-missing evidence note must reference retention and be neutral."""
    mapper = InMemoryMapper([
        _make_declared("CSV", "test.csv", "salary", purpose="Payroll", retention_period=None),
    ])
    gap = mapper.map_field(_make_result("CSV", "test.csv", "salary", detected_class="Financial"))
    note = gap.evidence_note.lower()
    assert "retention" in note
    assert "human review" in note


# ===========================================================================
# 4. Both purpose and retention missing
# ===========================================================================

def test_both_purpose_and_retention_missing() -> None:
    """Both null → status Purpose & Retention Missing."""
    mapper = InMemoryMapper([
        _make_declared("CSV", "test.csv", "city", purpose=None, retention_period=None),
    ])
    gap = mapper.map_field(_make_result("CSV", "test.csv", "city", detected_class="Location"))

    assert gap.overall_status == MetadataStatus.BOTH_MISSING
    assert "purpose" in gap.missing_items
    assert "retention_period" in gap.missing_items
    assert gap.purpose_status   == PresenceStatus.MISSING
    assert gap.retention_status == PresenceStatus.MISSING


# ===========================================================================
# 5. No metadata record (Not Mapped)
# ===========================================================================

def test_no_metadata_record() -> None:
    """No declared metadata for the field → status Not Mapped."""
    mapper = InMemoryMapper([])   # empty — no records
    gap = mapper.map_field(_make_result("CSV", "test.csv", "country", detected_class="Location"))

    assert gap.overall_status   == MetadataStatus.NOT_MAPPED
    assert gap.purpose_status   == PresenceStatus.NOT_DECLARED
    assert gap.retention_status == PresenceStatus.NOT_DECLARED
    assert "purpose" in gap.missing_items
    assert "retention_period" in gap.missing_items


def test_not_mapped_note_is_neutral() -> None:
    """Not-mapped evidence note must reference review and be neutral."""
    mapper = InMemoryMapper([])
    gap = mapper.map_field(_make_result("CSV", "test.csv", "country", detected_class="Location"))
    note = gap.evidence_note.lower()
    assert "human review" in note or "evidence gap" in note


# ===========================================================================
# 6. Same field name in different sources — no cross-source match
# ===========================================================================

def test_same_field_different_sources_no_cross_match() -> None:
    """
    'email' in customers.csv and 'email' in employees.csv must be matched
    independently. Metadata for one must not pollute the other.
    """
    mapper = InMemoryMapper([
        _make_declared("CSV", "customers.csv", "email", "Customer comms", "2 years"),
        _make_declared("CSV", "employees.csv", "email", "HR comms",       None),    # retention missing
    ])

    cust_gap = mapper.map_field(_make_result("CSV", "customers.csv", "email"))
    emp_gap  = mapper.map_field(_make_result("CSV", "employees.csv",  "email"))

    assert cust_gap.overall_status == MetadataStatus.COMPLETE
    assert emp_gap.overall_status  == MetadataStatus.RETENTION_MISSING


# ===========================================================================
# 7. Correct source_type matching
# ===========================================================================

def test_source_type_matching() -> None:
    """
    A metadata record for source_type='CSV' must NOT match a SQL result
    with the same source_name and field_name.
    """
    mapper = InMemoryMapper([
        _make_declared("CSV", "customers.csv", "email", "CSV purpose", "2 years"),
    ])

    sql_result = _make_result("SQL", "customers.csv", "email")   # wrong type
    gap = mapper.map_field(sql_result)
    assert gap.overall_status == MetadataStatus.NOT_MAPPED


# ===========================================================================
# 8. Correct source_name matching
# ===========================================================================

def test_source_name_matching() -> None:
    """
    A metadata record for source_name='customers.csv' must NOT match
    source_name='employees.csv' even with the same field_name.
    """
    mapper = InMemoryMapper([
        _make_declared("CSV", "customers.csv", "email", "Customer comms", "2 years"),
    ])

    wrong_result = _make_result("CSV", "employees.csv", "email")
    gap = mapper.map_field(wrong_result)
    assert gap.overall_status == MetadataStatus.NOT_MAPPED


# ===========================================================================
# 9. Correct field_name matching
# ===========================================================================

def test_field_name_matching() -> None:
    """
    A metadata record for field_name='email' must NOT match field_name='phone'.
    """
    mapper = InMemoryMapper([
        _make_declared("CSV", "customers.csv", "email", "Purpose", "2 years"),
    ])

    phone_result = _make_result("CSV", "customers.csv", "phone")
    gap = mapper.map_field(phone_result)
    assert gap.overall_status == MetadataStatus.NOT_MAPPED


# ===========================================================================
# 10. Evidence inventory generation
# ===========================================================================

def test_evidence_inventory_generation() -> None:
    """build() must return one InventoryRecord per detected candidate field."""
    mapper = InMemoryMapper([
        _make_declared("CSV", "test.csv", "email", "Comms", "2 years"),
        _make_declared("CSV", "test.csv", "phone", "Support", None),
    ])
    inv_builder = EvidenceInventory(mapper)

    results = [
        _make_result("CSV", "test.csv", "email", "Contact", 0.95),
        _make_result("CSV", "test.csv", "phone", "Contact", 0.90),
        _make_result("CSV", "test.csv", "salary", "Financial", 0.75),  # not mapped
        # Below threshold (detected_class=None) — should be EXCLUDED
        FieldDetectionResult(
            source_type="CSV", source_name="test.csv", field_name="loyalty_points",
            detected_class=None, confidence=0.05, confidence_level="None",
            review_required=False,
            evidence=EvidenceDetail(
                keyword_match=False, keyword_match_type=None, keyword_score=0.0,
                pattern_matched=False, pattern_name=None, pattern_match_rate=None,
                pattern_score=0.0, dtype="int64", dtype_score=0.0,
            ),
            sample_count=100, non_null_count=100, pattern_match_rate=None,
            reason="Not a PII candidate.",
        ),
    ]

    inventory = inv_builder.build(results)

    # Only 3 detected candidates; loyalty_points (detected_class=None) excluded
    assert len(inventory) == 3
    field_names = {r.field_name for r in inventory}
    assert "email"  in field_names
    assert "phone"  in field_names
    assert "salary" in field_names
    assert "loyalty_points" not in field_names


def test_inventory_record_is_correct_type() -> None:
    """build() must return InventoryRecord instances."""
    mapper = InMemoryMapper([
        _make_declared("CSV", "test.csv", "email", "Comms", "2 years"),
    ])
    inv_builder = EvidenceInventory(mapper)
    inventory = inv_builder.build([_make_result("CSV", "test.csv", "email")])
    assert all(isinstance(r, InventoryRecord) for r in inventory)


# ===========================================================================
# 11. Evidence gap report generation
# ===========================================================================

def test_gap_report_summary_counts() -> None:
    """GapReportGenerator must correctly count gap types."""
    mapper = InMemoryMapper([
        _make_declared("CSV", "t.csv", "email",   "Comms",   "2 years"),    # complete
        _make_declared("CSV", "t.csv", "phone",   None,       "1 year"),    # purpose missing
        _make_declared("CSV", "t.csv", "city",    "Delivery", None),        # retention missing
        _make_declared("CSV", "t.csv", "salary",  None,       None),        # both missing
        # "country" has no declared metadata → not_mapped
    ])
    inv_builder = EvidenceInventory(mapper)
    results = [
        _make_result("CSV", "t.csv", "email",   "Contact",  0.95),
        _make_result("CSV", "t.csv", "phone",   "Contact",  0.90),
        _make_result("CSV", "t.csv", "city",    "Location", 0.75),
        _make_result("CSV", "t.csv", "salary",  "Financial",0.80),
        _make_result("CSV", "t.csv", "country", "Location", 0.75),   # not mapped
    ]
    inventory = inv_builder.build(results)
    reporter  = GapReportGenerator(inventory)
    summary   = reporter.build_summary()

    assert summary.complete_count          == 1
    assert summary.purpose_missing_count   == 1
    assert summary.retention_missing_count == 1
    assert summary.both_missing_count      == 1
    assert summary.not_mapped_count        == 1
    assert summary.total_gap_count         == 4
    assert summary.total_candidates        == 5


def test_gap_report_summary_is_correct_type() -> None:
    """build_summary() must return a GapReportSummary."""
    reporter = GapReportGenerator([])
    summary  = reporter.build_summary()
    assert isinstance(summary, GapReportSummary)


# ===========================================================================
# 12. No legal/compliance language generated by the mapper
# ===========================================================================

PROHIBITED_TERMS = [
    "illegal",
    "violation",
    "gdpr violation",
    "non-compliant",
    "non compliant",
    "noncompliant",
    "unlawful",
    "breach of law",
    "regulatory violation",
    "dpdp violation",
    "lawful basis",
    "consent invalid",
]


def _check_no_legal_language(text: str) -> None:
    lower = text.lower()
    for term in PROHIBITED_TERMS:
        assert term not in lower, (
            f"Legal/compliance language found in output: '{term}'. "
            f"Full text: {text!r}"
        )


@pytest.mark.parametrize("declared_kw,test_name", [
    ({"purpose": "Comms",   "retention_period": "2 years"}, "complete"),
    ({"purpose": None,      "retention_period": "2 years"}, "purpose_missing"),
    ({"purpose": "Comms",   "retention_period": None},      "retention_missing"),
    ({"purpose": None,      "retention_period": None},      "both_missing"),
])
def test_no_legal_language_in_evidence_note(declared_kw: dict, test_name: str) -> None:
    """Evidence notes must never contain legal/compliance language."""
    mapper = InMemoryMapper([
        _make_declared("CSV", "test.csv", "email", **declared_kw),
    ])
    result = _make_result("CSV", "test.csv", "email")
    gap    = mapper.map_field(result)
    _check_no_legal_language(gap.evidence_note)


def test_no_legal_language_when_not_mapped() -> None:
    """Not-mapped evidence notes must not contain legal language."""
    mapper = InMemoryMapper([])
    gap    = mapper.map_field(_make_result("CSV", "test.csv", "email"))
    _check_no_legal_language(gap.evidence_note)


# ===========================================================================
# 13. Real metadata.json loads and produces results
# ===========================================================================

def test_real_metadata_json_loads() -> None:
    """The actual metadata.json must load without errors."""
    mapper = MetadataMapper(METADATA_PATH)
    assert len(mapper.declared_records) > 0


def test_real_metadata_has_all_gap_types() -> None:
    """
    The actual metadata.json must have entries covering the gap status types
    (when mapped against synthetic detection results matching the declared fields).
    """
    mapper = MetadataMapper(METADATA_PATH)

    # Build synthetic results for known fields from the metadata
    test_results = [
        # Complete (customers.csv email has full metadata)
        _make_result("CSV", "customers.csv", "email",   "Contact"),
        # Retention missing (customers.csv full_name)
        _make_result("CSV", "customers.csv", "full_name","Identity"),
        # Purpose missing (customers.csv state)
        _make_result("CSV", "customers.csv", "state",   "Location"),
        # Both purpose and retention missing (customers.csv country)
        _make_result("CSV", "customers.csv", "country", "Location"),
        # Not mapped (customers.csv registration_date — no metadata entry)
        _make_result("CSV", "customers.csv", "registration_date", "Identity"),
    ]

    statuses = {mapper.map_field(r).overall_status for r in test_results}
    assert MetadataStatus.COMPLETE              in statuses
    assert MetadataStatus.RETENTION_MISSING     in statuses
    assert MetadataStatus.PURPOSE_MISSING       in statuses
    assert MetadataStatus.BOTH_MISSING          in statuses
    assert MetadataStatus.NOT_MAPPED            in statuses

