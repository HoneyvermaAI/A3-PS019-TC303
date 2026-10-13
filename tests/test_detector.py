"""
tests/test_detector.py
======================
Unit tests for the PersonalDataDetector engine (PS-019 TC-303).

All test data is entirely synthetic.
No real personal information is used.

Run:
  pytest tests/test_detector.py -v
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from backend.scanner.detector import FieldDetectionResult, PersonalDataDetector

# ---------------------------------------------------------------------------
# Shared fixture — one detector instance per test session
# ---------------------------------------------------------------------------
RULES_PATH = Path(__file__).parent.parent / "backend" / "config" / "rules.json"


@pytest.fixture(scope="module")
def detector() -> PersonalDataDetector:
    return PersonalDataDetector(RULES_PATH)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _detect(detector: PersonalDataDetector, name: str, values: list) -> FieldDetectionResult:
    """Convenience wrapper for detector.detect()."""
    series = pd.Series(values)
    return detector.detect(name, series, "CSV", "test_data.csv")


# ===========================================================================
# 1. Email field detection
# ===========================================================================

def test_email_field_detected_as_contact(detector: PersonalDataDetector) -> None:
    """Column 'email' with valid email values → Contact, High confidence."""
    result = _detect(
        detector, "email",
        ["alice@example.com", "bob@test.org", "carol99@mailbox.test"] * 20,
    )
    assert result.detected_class == "Contact"
    assert result.confidence >= 0.75
    assert result.confidence_level == "High"
    assert result.evidence.keyword_match is True


def test_email_address_variant_detected(detector: PersonalDataDetector) -> None:
    """Column 'email_address' (underscore variant) also detected as Contact."""
    result = _detect(
        detector, "email_address",
        ["alice@example.com", "bob@test.org"] * 20,
    )
    assert result.detected_class == "Contact"


# ===========================================================================
# 2. Phone field detection
# ===========================================================================

def test_phone_field_detected_as_contact(detector: PersonalDataDetector) -> None:
    """Column 'phone' with international phone values → Contact."""
    result = _detect(
        detector, "phone",
        ["+1-555-123-4567", "+1-555-987-6543", "+1-555-234-5678"] * 20,
    )
    assert result.detected_class == "Contact"
    assert result.confidence >= 0.60


def test_mobile_field_detected_as_contact(detector: PersonalDataDetector) -> None:
    """Column 'mobile' is a Contact keyword."""
    result = _detect(
        detector, "mobile",
        ["+1-555-321-0987", "+1-555-111-2222"] * 20,
    )
    assert result.detected_class == "Contact"


# ===========================================================================
# 3. Name / Identity detection
# ===========================================================================

def test_full_name_detected_as_identity(detector: PersonalDataDetector) -> None:
    """Column 'full_name' → Identity (exact keyword match)."""
    result = _detect(
        detector, "full_name",
        ["Alice Smith", "Bob Jones", "Carol Williams"] * 20,
    )
    assert result.detected_class == "Identity"
    assert result.confidence >= 0.70
    assert result.evidence.keyword_match_type == "exact"


def test_dob_detected_as_identity(detector: PersonalDataDetector) -> None:
    """Column 'date_of_birth' with ISO dates → Identity, High confidence."""
    result = _detect(
        detector, "date_of_birth",
        ["1985-04-23", "1990-11-02", "1978-07-15"] * 20,
    )
    assert result.detected_class == "Identity"
    assert result.confidence >= 0.75
    assert result.evidence.pattern_matched is True


# ===========================================================================
# 4. Location detection
# ===========================================================================

def test_city_detected_as_location(detector: PersonalDataDetector) -> None:
    """Column 'city' → Location."""
    result = _detect(
        detector, "city",
        ["Springfield", "Riverside", "Fairview", "Maplewood"] * 20,
    )
    assert result.detected_class == "Location"


def test_postal_code_detected_as_location(detector: PersonalDataDetector) -> None:
    """Column 'postal_code' with US ZIP values → Location, High confidence."""
    result = _detect(
        detector, "postal_code",
        ["10001", "90210", "60614", "30301", "94102"] * 20,
    )
    assert result.detected_class == "Location"
    assert result.confidence >= 0.75
    assert result.evidence.pattern_matched is True


def test_country_detected_as_location(detector: PersonalDataDetector) -> None:
    result = _detect(detector, "country", ["USA", "Canada", "UK"] * 20)
    assert result.detected_class == "Location"


# ===========================================================================
# 5. Financial detection
# ===========================================================================

def test_salary_detected_as_financial(detector: PersonalDataDetector) -> None:
    """Column 'salary' with float values → Financial, High confidence."""
    result = _detect(
        detector, "salary",
        [50000.0, 75000.0, 90000.0, 120000.0] * 20,
    )
    assert result.detected_class == "Financial"
    assert result.confidence >= 0.70
    assert result.confidence_level in ("High", "Medium")


def test_bank_account_detected_as_financial(detector: PersonalDataDetector) -> None:
    """Column 'bank_account' with synthetic account numbers → Financial."""
    result = _detect(
        detector, "bank_account",
        ["ACC-12345678", "ACC-87654321", "ACC-99887766"] * 20,
    )
    assert result.detected_class == "Financial"
    assert result.confidence >= 0.75


def test_card_last4_detected_as_financial(detector: PersonalDataDetector) -> None:
    """Column 'card_last4' with 4-digit values → Financial."""
    result = _detect(
        detector, "card_last4",
        ["4521", "9834", "1107", "6655"] * 20,
    )
    assert result.detected_class == "Financial"
    assert result.confidence >= 0.75


# ===========================================================================
# 6. Sensitive / Health detection
# ===========================================================================

def test_health_insurance_id_detected(detector: PersonalDataDetector) -> None:
    """Column 'health_insurance_id' with HI-XXXXXX values → Sensitive/Health."""
    result = _detect(
        detector, "health_insurance_id",
        ["HI-123456", "HI-789012", "HI-345678"] * 20,
    )
    assert result.detected_class == "Sensitive/Health"
    assert result.confidence >= 0.75
    assert result.evidence.pattern_matched is True


def test_medical_field_detected(detector: PersonalDataDetector) -> None:
    """Column 'medical_record' → Sensitive/Health via keyword."""
    result = _detect(
        detector, "medical_record",
        ["MR-001", "MR-002", "MR-003"] * 20,
    )
    assert result.detected_class == "Sensitive/Health"


# ===========================================================================
# 7. Negative / Non-PII fields
# ===========================================================================

def test_loyalty_points_not_pii(detector: PersonalDataDetector) -> None:
    """Column 'loyalty_points' (integer metric) → not classified as personal data."""
    result = _detect(
        detector, "loyalty_points",
        [100, 200, 500, 1000, 0, 750] * 20,
    )
    assert result.detected_class is None
    assert result.confidence_level == "None"


def test_product_category_not_pii(detector: PersonalDataDetector) -> None:
    """Column 'product_category' → not personal data."""
    result = _detect(
        detector, "product_category",
        ["Electronics", "Apparel", "Groceries", "Books"] * 20,
    )
    assert result.detected_class is None


def test_order_status_not_pii(detector: PersonalDataDetector) -> None:
    """Column 'order_status' → not personal data."""
    result = _detect(
        detector, "order_status",
        ["completed", "pending", "refunded", "failed"] * 20,
    )
    assert result.detected_class is None


def test_merchant_id_not_pii(detector: PersonalDataDetector) -> None:
    """Column 'merchant_id' → not classified as personal data."""
    result = _detect(
        detector, "merchant_id",
        ["MER-1001", "MER-2345", "MER-9876"] * 20,
    )
    assert result.detected_class is None


# ===========================================================================
# 8. False-positive prevention: email_status
# ===========================================================================

def test_email_status_not_high_confidence_contact(detector: PersonalDataDetector) -> None:
    """
    Column 'email_status' contains keyword 'email' but values are status strings.
    The pattern check should fail, keeping confidence below High.
    """
    result = _detect(
        detector, "email_status",
        ["verified", "pending", "bounced", "active", "invalid"] * 20,
    )
    # Must NOT be classified as high-confidence Contact
    assert result.confidence < 0.75, (
        f"email_status should not be High confidence; got {result.confidence:.2f}"
    )
    # Keyword matched (email is in the tokens) so it should surface for review
    assert result.review_required is True


def test_email_status_pattern_rate_near_zero(detector: PersonalDataDetector) -> None:
    """Pattern match rate for email_status values must be near 0."""
    result = _detect(
        detector, "email_status",
        ["verified", "pending", "bounced"] * 20,
    )
    if result.pattern_match_rate is not None:
        assert result.pattern_match_rate < 0.10, (
            f"email_status pattern rate should be near 0; got {result.pattern_match_rate:.2f}"
        )


# ===========================================================================
# 9. False-positive prevention: phone_verified
# ===========================================================================

def test_phone_verified_not_high_confidence_contact(detector: PersonalDataDetector) -> None:
    """
    Column 'phone_verified' contains keyword 'phone' but values are booleans.
    Pattern check fails → not High confidence.
    """
    result = _detect(
        detector, "phone_verified",
        ["true", "false", "true", "false", "true"] * 20,
    )
    assert result.confidence < 0.75, (
        f"phone_verified should not be High confidence; got {result.confidence:.2f}"
    )
    assert result.review_required is True


# ===========================================================================
# 10. Case-insensitive column detection
# ===========================================================================

def test_uppercase_email_column_detected(detector: PersonalDataDetector) -> None:
    """Column 'EMAIL' (all caps) must normalise correctly → Contact."""
    result = _detect(
        detector, "EMAIL",
        ["alice@example.com", "bob@test.org"] * 20,
    )
    assert result.detected_class == "Contact"


def test_mixed_case_column_detected(detector: PersonalDataDetector) -> None:
    """Column 'FullName' (PascalCase) → Identity."""
    result = _detect(
        detector, "FullName",
        ["Alice Smith", "Bob Jones"] * 20,
    )
    assert result.detected_class == "Identity"


# ===========================================================================
# 11. Pattern matching — camelCase column names
# ===========================================================================

def test_camel_case_customer_email(detector: PersonalDataDetector) -> None:
    """Column 'customerEmail' (camelCase) → Contact via token 'email'."""
    result = _detect(
        detector, "customerEmail",
        ["alice@example.com", "bob@test.org"] * 20,
    )
    assert result.detected_class == "Contact"


def test_kebab_case_date_of_birth(detector: PersonalDataDetector) -> None:
    """Column 'date-of-birth' (kebab-case) → Identity."""
    result = _detect(
        detector, "date-of-birth",
        ["1985-04-23", "1990-11-02"] * 20,
    )
    assert result.detected_class == "Identity"


# ===========================================================================
# 12. Confidence always in [0.0, 1.0]
# ===========================================================================

@pytest.mark.parametrize("field_name,values", [
    ("email",              ["alice@example.com"] * 30),
    ("salary",             [50000.0] * 30),
    ("health_insurance_id",["HI-123456"] * 30),
    ("loyalty_points",     [100] * 30),
    ("email_status",       ["verified"] * 30),
    ("postal_code",        ["10001"] * 30),
    ("unknown_xyz_field",  ["foo", "bar"] * 15),
])
def test_confidence_is_bounded(
    detector: PersonalDataDetector,
    field_name: str,
    values: list,
) -> None:
    """Confidence score must always be within [0.0, 1.0]."""
    result = _detect(detector, field_name, values)
    assert 0.0 <= result.confidence <= 1.0, (
        f"{field_name}: confidence={result.confidence} out of bounds"
    )


# ===========================================================================
# 13. Ambiguous / review-required fields
# ===========================================================================

def test_ambiguous_field_review_required(detector: PersonalDataDetector) -> None:
    """
    A field like 'reference_id' with generic string values has no clear class
    → detected_class is None, or if classified it requires review.
    """
    result = _detect(
        detector, "reference_id",
        ["REF-001", "REF-002", "REF-003"] * 20,
    )
    if result.detected_class is not None:
        assert result.review_required is True, (
            "Ambiguous field classified without review flag"
        )
    # If unclassified, confidence should be low
    else:
        assert result.confidence < 0.45


def test_billing_email_detected_despite_prefix(detector: PersonalDataDetector) -> None:
    """
    Column 'billing_email' has a prefix 'billing' but token 'email' → Contact.
    Values confirm it's an email field.
    """
    result = _detect(
        detector, "billing_email",
        ["alice@example.com", "bob@test.org"] * 20,
    )
    assert result.detected_class == "Contact"


def test_result_is_field_detection_result_type(detector: PersonalDataDetector) -> None:
    """detect() must always return a FieldDetectionResult Pydantic model."""
    from backend.scanner.detector import FieldDetectionResult

    result = _detect(detector, "email", ["alice@example.com"] * 10)
    assert isinstance(result, FieldDetectionResult)


def test_evidence_fields_populated(detector: PersonalDataDetector) -> None:
    """Evidence object must have numeric scores populated for every result."""
    result = _detect(
        detector, "health_insurance_id",
        ["HI-123456", "HI-789012"] * 20,
    )
    assert result.evidence.keyword_score >= 0.0
    assert result.evidence.pattern_score >= 0.0
    assert result.evidence.dtype_score >= 0.0
    assert isinstance(result.evidence.dtype, str)
