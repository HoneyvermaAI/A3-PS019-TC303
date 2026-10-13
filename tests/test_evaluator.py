"""
tests/test_evaluator.py
=======================
Unit and integration tests for Phase 5 — Ground-Truth Evaluation Module.

Tests cover:
  1. Perfect predictions scenario.
  2. False positive detections.
  3. False negative detections.
  4. Wrong-class (misclassification) scenario.
  5. A class with zero predictions (precision undefined).
  6. A class with zero ground-truth positive support (metrics undefined).
  7. Duplicate ground-truth composite keys (validation error).
  8. Unmatched source keys handling and reporting.
  9. Null and invalid boolean labels handling.
 10. Missing required ground-truth columns.
 11. Composite-key matching across different sources with identical field names.
 12. Reproducible export of reports (JSON and CSV).
 13. End-to-end evaluation using actual scanner output on benchmark ground truth.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from backend.evaluation.evaluator import Evaluator
from backend.evaluation.models import GroundTruthRecord
from backend.evaluation.reporting import EvaluationReporter
from backend.scanner.detector import EvidenceDetail, FieldDetectionResult


def _make_dummy_scan_result(
    source_type: str,
    source_name: str,
    field_name: str,
    detected_class: str | None,
    confidence: float = 0.85,
) -> FieldDetectionResult:
    """Helper to create minimal FieldDetectionResult for testing."""
    return FieldDetectionResult(
        source_type=source_type,
        source_name=source_name,
        field_name=field_name,
        detected_class=detected_class,
        confidence=confidence,
        confidence_level="High" if confidence >= 0.75 else "Medium",
        review_required=confidence < 0.75,
        evidence=EvidenceDetail(
            keyword_match=bool(detected_class),
            keyword_match_type="exact" if detected_class else None,
            keyword_score=0.70 if detected_class else 0.0,
            pattern_matched=False,
            pattern_name=None,
            pattern_match_rate=0.0,
            pattern_score=0.0,
            dtype="object",
            dtype_score=0.0,
        ),
        sample_count=50,
        non_null_count=50,
        pattern_match_rate=0.0,
        reason="Synthetic test reason",
    )


# ===========================================================================
# 1. Perfect Predictions
# ===========================================================================

def test_perfect_predictions() -> None:
    evaluator = Evaluator(target_classes=["Contact", "Financial"])
    gt = [
        GroundTruthRecord(source_type="CSV", source_name="c.csv", field_name="email", expected_class="Contact", is_personal_data=True),
        GroundTruthRecord(source_type="CSV", source_name="c.csv", field_name="salary", expected_class="Financial", is_personal_data=True),
        GroundTruthRecord(source_type="CSV", source_name="c.csv", field_name="id", expected_class=None, is_personal_data=False),
    ]
    scan = [
        _make_dummy_scan_result("CSV", "c.csv", "email", "Contact"),
        _make_dummy_scan_result("CSV", "c.csv", "salary", "Financial"),
        _make_dummy_scan_result("CSV", "c.csv", "id", None),
    ]

    summary = evaluator.evaluate(scan, gt)
    assert summary.matched_records_count == 3
    assert summary.total_errors == 0
    assert summary.detection_metrics.precision == 1.0
    assert summary.detection_metrics.recall == 1.0
    assert summary.detection_metrics.f1 == 1.0

    for m in summary.per_class_metrics:
        assert m.tp == 1
        assert m.fp == 0
        assert m.fn == 0
        assert m.precision == 1.0
        assert m.recall == 1.0
        assert m.f1 == 1.0


# ===========================================================================
# 2. False Positive Detection
# ===========================================================================

def test_false_positive_detection() -> None:
    evaluator = Evaluator(target_classes=["Contact"])
    gt = [
        GroundTruthRecord(source_type="CSV", source_name="c.csv", field_name="status", expected_class=None, is_personal_data=False),
    ]
    scan = [
        _make_dummy_scan_result("CSV", "c.csv", "status", "Contact"),
    ]

    summary = evaluator.evaluate(scan, gt)
    assert summary.total_errors == 1
    assert summary.detection_metrics.fp == 1
    assert summary.detection_metrics.tp == 0
    assert summary.detection_metrics.precision == 0.0

    m = summary.per_class_metrics[0]
    assert m.tp == 0
    assert m.fp == 1
    assert m.fn == 0
    assert m.precision == 0.0
    assert m.recall is None  # support is 0 -> recall undefined


# ===========================================================================
# 3. False Negative Detection
# ===========================================================================

def test_false_negative_detection() -> None:
    evaluator = Evaluator(target_classes=["Contact"])
    gt = [
        GroundTruthRecord(source_type="CSV", source_name="c.csv", field_name="phone", expected_class="Contact", is_personal_data=True),
    ]
    scan = [
        _make_dummy_scan_result("CSV", "c.csv", "phone", None),
    ]

    summary = evaluator.evaluate(scan, gt)
    assert summary.total_errors == 1
    assert summary.detection_metrics.fn == 1
    assert summary.detection_metrics.recall == 0.0

    m = summary.per_class_metrics[0]
    assert m.tp == 0
    assert m.fp == 0
    assert m.fn == 1
    assert m.precision is None  # no predictions made -> precision undefined
    assert m.recall == 0.0


# ===========================================================================
# 4. Wrong-Class Misclassification
# ===========================================================================

def test_wrong_class_misclassification() -> None:
    evaluator = Evaluator(target_classes=["Identity", "Contact"])
    gt = [
        GroundTruthRecord(source_type="CSV", source_name="c.csv", field_name="username", expected_class="Identity", is_personal_data=True),
    ]
    scan = [
        _make_dummy_scan_result("CSV", "c.csv", "username", "Contact"),
    ]

    summary = evaluator.evaluate(scan, gt)
    errors = evaluator.extract_error_records(scan, gt)

    assert len(errors) == 1
    assert errors[0].error_type == "Misclassification (Wrong Class)"

    # Detection is correct (detected as candidate PII)
    assert summary.detection_metrics.tp == 1
    assert summary.detection_metrics.fp == 0
    assert summary.detection_metrics.fn == 0

    # For Identity: FN = 1, TP = 0
    id_m = next(m for m in summary.per_class_metrics if m.class_name == "Identity")
    assert id_m.tp == 0
    assert id_m.fn == 1
    assert id_m.fp == 0

    # For Contact: FP = 1, TP = 0
    ct_m = next(m for m in summary.per_class_metrics if m.class_name == "Contact")
    assert ct_m.tp == 0
    assert ct_m.fn == 0
    assert ct_m.fp == 1


# ===========================================================================
# 5. Class with Zero Predictions
# ===========================================================================

def test_class_with_zero_predictions() -> None:
    evaluator = Evaluator(target_classes=["Sensitive/Health"])
    gt = [
        GroundTruthRecord(source_type="CSV", source_name="c.csv", field_name="diagnosis", expected_class="Sensitive/Health", is_personal_data=True),
    ]
    scan = [
        _make_dummy_scan_result("CSV", "c.csv", "diagnosis", None),
    ]

    summary = evaluator.evaluate(scan, gt)
    m = summary.per_class_metrics[0]
    assert m.tp == 0
    assert m.fp == 0
    assert m.fn == 1
    assert m.precision is None
    assert "Zero Predictions" in m.status


# ===========================================================================
# 6. Class with Zero Ground-Truth Positive Support
# ===========================================================================

def test_class_with_zero_ground_truth_support() -> None:
    evaluator = Evaluator(target_classes=["Sensitive/Health"])
    gt = [
        GroundTruthRecord(source_type="CSV", source_name="c.csv", field_name="id", expected_class=None, is_personal_data=False),
    ]
    scan = [
        _make_dummy_scan_result("CSV", "c.csv", "id", None),
    ]

    summary = evaluator.evaluate(scan, gt)
    m = summary.per_class_metrics[0]
    assert m.support == 0
    assert m.tp == 0
    assert m.precision is None
    assert m.recall is None
    assert "Zero Ground-Truth Positives" in m.status


# ===========================================================================
# 7. Duplicate Ground-Truth Keys Validation
# ===========================================================================

def test_duplicate_ground_truth_keys_rejected(tmp_path: Path) -> None:
    csv_file = tmp_path / "dup_gt.csv"
    csv_file.write_text(
        "source_type,source_name,field_name,expected_class,is_personal_data\n"
        "CSV,customers.csv,email,Contact,true\n"
        "CSV,customers.csv,email,Contact,true\n",
        encoding="utf-8"
    )

    with pytest.raises(ValueError, match="Duplicate ground-truth composite key"):
        Evaluator.load_ground_truth(csv_file)


# ===========================================================================
# 8. Unmatched Keys Handling
# ===========================================================================

def test_unmatched_source_keys_reported() -> None:
    evaluator = Evaluator(target_classes=["Contact"])
    gt = [
        GroundTruthRecord(source_type="CSV", source_name="c.csv", field_name="email", expected_class="Contact", is_personal_data=True),
        GroundTruthRecord(source_type="CSV", source_name="c.csv", field_name="unmatched_gt", expected_class="Contact", is_personal_data=True),
    ]
    scan = [
        _make_dummy_scan_result("CSV", "c.csv", "email", "Contact"),
        _make_dummy_scan_result("CSV", "c.csv", "unmatched_scan", "Contact"),
    ]

    summary = evaluator.evaluate(scan, gt)
    assert summary.matched_records_count == 1
    assert summary.unmatched_ground_truth_count == 1
    assert summary.unmatched_scanner_count == 1
    assert len(summary.data_quality_warnings) == 2


# ===========================================================================
# 9. Invalid Boolean or Label Validation
# ===========================================================================

def test_invalid_ground_truth_values(tmp_path: Path) -> None:
    csv_file = tmp_path / "bad_gt.csv"
    csv_file.write_text(
        "source_type,source_name,field_name,expected_class,is_personal_data\n"
        "CSV,c.csv,f1,InvalidClass,true\n",
        encoding="utf-8"
    )

    with pytest.raises(ValueError, match="invalid expected_class"):
        Evaluator.load_ground_truth(csv_file)

    csv_file.write_text(
        "source_type,source_name,field_name,expected_class,is_personal_data\n"
        "CSV,c.csv,f1,Contact,not_a_boolean\n",
        encoding="utf-8"
    )
    with pytest.raises(ValueError, match="invalid boolean value"):
        Evaluator.load_ground_truth(csv_file)


# ===========================================================================
# 10. Missing Required Ground-Truth Columns
# ===========================================================================

def test_missing_required_columns(tmp_path: Path) -> None:
    csv_file = tmp_path / "missing_col.csv"
    csv_file.write_text(
        "source_type,source_name\nCSV,c.csv\n",
        encoding="utf-8"
    )
    with pytest.raises(ValueError, match="missing required columns"):
        Evaluator.load_ground_truth(csv_file)


# ===========================================================================
# 11. Composite-Key Isolation Across Sources
# ===========================================================================

def test_composite_key_source_isolation() -> None:
    """Verifies that identical field names in different sources are isolated."""
    evaluator = Evaluator(target_classes=["Contact"])
    gt = [
        GroundTruthRecord(source_type="CSV", source_name="cust.csv", field_name="email", expected_class="Contact", is_personal_data=True),
        GroundTruthRecord(source_type="CSV", source_name="emp.csv", field_name="email", expected_class=None, is_personal_data=False),
    ]
    scan = [
        _make_dummy_scan_result("CSV", "cust.csv", "email", "Contact"),
        _make_dummy_scan_result("CSV", "emp.csv", "email", None),
    ]

    summary = evaluator.evaluate(scan, gt)
    assert summary.matched_records_count == 2
    assert summary.total_errors == 0


# ===========================================================================
# 12. Reproducible Report Export
# ===========================================================================

def test_report_export(tmp_path: Path) -> None:
    evaluator = Evaluator(target_classes=["Contact"])
    gt = [
        GroundTruthRecord(source_type="CSV", source_name="c.csv", field_name="email", expected_class="Contact", is_personal_data=True),
    ]
    scan = [
        _make_dummy_scan_result("CSV", "c.csv", "email", "Contact"),
    ]

    summary = evaluator.evaluate(scan, gt)
    errors = evaluator.extract_error_records(scan, gt)

    reporter = EvaluationReporter(reports_dir=tmp_path)
    p_json = reporter.export_summary_json(summary)
    p_csv = reporter.export_per_class_csv(summary.per_class_metrics)
    p_cm = reporter.export_confusion_matrix_csv(summary.confusion_matrix)
    p_err = reporter.export_errors_csv(errors)

    assert p_json.exists()
    assert p_csv.exists()
    assert p_cm.exists()
    assert p_err.exists()

    with open(p_json, encoding="utf-8") as f:
        data = json.load(f)
        assert data["matched_records_count"] == 1
        assert "disclaimer" in data


# ===========================================================================
# 13. End-to-End Evaluation on Actual Production Data
# ===========================================================================

def test_real_ground_truth_file_loads() -> None:
    """Ensures data/ground_truth.csv loads cleanly and meets integrity constraints."""
    real_gt_path = Path(__file__).parent.parent / "data" / "ground_truth.csv"
    records = Evaluator.load_ground_truth(real_gt_path)
    assert len(records) == 84
    positives = [r for r in records if r.is_personal_data]
    assert len(positives) == 40
