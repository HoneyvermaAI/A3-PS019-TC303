"""
backend/evaluation/models.py
============================
Pydantic data models for Phase 5 — Ground-Truth Evaluation & Performance Metrics.

SCOPE NOTE
----------
These models capture TECHNICAL evaluation metrics (precision, recall, F1, confusion matrices,
error classifications) comparing candidate detection engine predictions against hand-labelled
ground-truth records on synthetic benchmark datasets.
They do NOT represent legal compliance accuracy, universal coverage, or regulatory certification.
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class GroundTruthRecord(BaseModel):
    """
    A validated ground-truth entry representing expected classification for a dataset field.
    """
    source_type: str = Field(description="Normalized source type: 'CSV' or 'SQL'")
    source_name: str = Field(description="Name of the file or database table (e.g., 'customers.csv')")
    field_name: str = Field(description="Name of the field/column")
    expected_class: Optional[str] = Field(
        default=None,
        description="Expected 1 of 5 personal-data classes, or None for non-PII fields"
    )
    is_personal_data: bool = Field(description="Whether the field represents candidate personal data")
    notes: Optional[str] = Field(default=None, description="Human reviewer rationale or notes")

    @property
    def composite_key(self) -> tuple[str, str, str]:
        """(source_type, source_name, field_name) normalized key."""
        return (self.source_type, self.source_name, self.field_name)


class ClassMetrics(BaseModel):
    """
    Per-class one-vs-rest evaluation metrics.
    """
    class_name: str = Field(description="Target personal-data class name")
    tp: int = Field(ge=0, description="True Positives (predicted == class and expected == class)")
    fp: int = Field(ge=0, description="False Positives (predicted == class and expected != class)")
    fn: int = Field(ge=0, description="False Negatives (predicted != class and expected == class)")
    support: int = Field(ge=0, description="Total ground-truth positive instances for this class")
    precision: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="TP / (TP + FP); None if denominator is 0"
    )
    recall: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="TP / (TP + FN); None if denominator is 0"
    )
    f1: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Harmonic mean of precision and recall; None if undefined"
    )
    status: str = Field(
        default="Evaluated",
        description="Evaluation status note (e.g., 'Evaluated', 'Limited Sample (Support < 5)', 'Zero Predictions')"
    )


class DetectionMetrics(BaseModel):
    """
    Binary candidate detection performance (Personal-Data vs Non-Personal-Data).
    """
    tp: int = Field(ge=0, description="Fields correctly detected as candidate personal data")
    fp: int = Field(ge=0, description="Non-PII fields incorrectly flagged as personal data")
    fn: int = Field(ge=0, description="Personal-data fields missed by scanner")
    tn: int = Field(ge=0, description="Non-PII fields correctly left unflagged")
    total_evaluated: int = Field(ge=0)
    precision: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    recall: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    f1: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class EvaluationErrorRecord(BaseModel):
    """
    Details of an individual mismatch between ground truth and scanner output.
    """
    source_type: str
    source_name: str
    field_name: str
    expected_class: Optional[str] = None
    predicted_class: Optional[str] = None
    is_personal_data_expected: bool
    is_personal_data_predicted: bool
    error_type: str = Field(
        description="Category: 'False Positive Detection', 'False Negative Detection', 'Misclassification', 'False Positive Class'"
    )
    confidence: Optional[float] = None
    confidence_level: Optional[str] = None
    reason: Optional[str] = None


class EvaluationReportSummary(BaseModel):
    """
    Comprehensive summary report containing overall stats, warnings, and per-class results.
    """
    generated_at: str
    ground_truth_total: int
    scanner_predictions_total: int
    matched_records_count: int
    unmatched_ground_truth_count: int
    unmatched_scanner_count: int
    unmatched_ground_truth_keys: list[dict[str, str]] = Field(default_factory=list)
    unmatched_scanner_keys: list[dict[str, str]] = Field(default_factory=list)
    ground_truth_class_distribution: dict[str, int] = Field(default_factory=dict)
    scanner_class_distribution: dict[str, int] = Field(default_factory=dict)
    detection_metrics: DetectionMetrics
    per_class_metrics: list[ClassMetrics] = Field(default_factory=list)
    confusion_matrix: dict[str, dict[str, int]] = Field(default_factory=dict)
    total_errors: int = Field(ge=0)
    data_quality_warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "This evaluation is performed on synthetic benchmark data for technical evidence only. "
        "It does NOT evaluate legal compliance, lawful basis, or real-world regulatory posture."
    )
