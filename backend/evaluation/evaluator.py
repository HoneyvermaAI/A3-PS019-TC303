"""
backend/evaluation/evaluator.py
===============================
Core evaluator for Phase 5 — Ground-Truth Evaluation & Per-Class Precision/Recall.

Implements:
  1. Ground-truth loading, schema validation, and composite-key integrity verification.
  2. One-vs-rest per-class precision, recall, and F1 calculation with explicit zero handling.
  3. Binary personal-data candidate detection vs non-personal-data evaluation.
  4. Full confusion matrix construction with explicit 'Not Detected' column.
  5. Detailed error isolation distinguishing false positives, false negatives, and wrong-class classifications.
  6. Class imbalance awareness and sample-size warnings.

SCOPE NOTE
----------
Evaluation metrics are technical benchmarking indicators calculated against synthetic datasets.
Zero-denominator calculations are surfaced as None with informative status notes.
Missing labels are NOT treated as negative examples.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

import pandas as pd

from backend.evaluation.models import (
    ClassMetrics,
    DetectionMetrics,
    EvaluationErrorRecord,
    EvaluationReportSummary,
    GroundTruthRecord,
)
from backend.scanner.detector import FieldDetectionResult

# Predefined benchmark personal data classes
BENCHMARK_CLASSES: list[str] = [
    "Identity",
    "Contact",
    "Location",
    "Financial",
    "Sensitive/Health",
]

DEFAULT_GROUND_TRUTH_PATH = Path(__file__).parent.parent.parent / "data" / "ground_truth.csv"


class Evaluator:
    """
    Evaluator comparing Personal-Data Discovery Scanner predictions against ground-truth labels.
    """

    def __init__(
        self,
        target_classes: Sequence[str] = BENCHMARK_CLASSES,
        small_sample_threshold: int = 5,
    ) -> None:
        self.target_classes = list(target_classes)
        self.small_sample_threshold = small_sample_threshold

    # ----------------------------------------------------------------------
    # Ground-Truth Loading and Validation
    # ----------------------------------------------------------------------

    @staticmethod
    def load_ground_truth(file_path: str | Path = DEFAULT_GROUND_TRUTH_PATH) -> list[GroundTruthRecord]:
        """
        Loads and validates data/ground_truth.csv.
        
        Validates:
          - Existence of file and required headers.
          - Normalization of whitespace and casing on keys.
          - Duplicate composite keys (source_type, source_name, field_name).
          - Valid expected_class (None or one of benchmark classes).
          - Valid boolean format for is_personal_data.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Ground-truth file not found: {path}")

        # Read CSV with pandas to reliably parse types
        df = pd.read_csv(path)

        required_cols = {"source_type", "source_name", "field_name", "is_personal_data"}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            raise ValueError(f"Ground-truth CSV missing required columns: {sorted(missing_cols)}")

        records: list[GroundTruthRecord] = []
        seen_keys: set[tuple[str, str, str]] = set()

        for idx, row in df.iterrows():
            # Normalize harmless whitespace and casing
            st = str(row["source_type"]).strip().upper() if pd.notna(row["source_type"]) else ""
            sn = str(row["source_name"]).strip() if pd.notna(row["source_name"]) else ""
            fn = str(row["field_name"]).strip() if pd.notna(row["field_name"]) else ""

            if not st or not sn or not fn:
                raise ValueError(f"Row {idx+1} in ground-truth has empty composite key component: ({st}, {sn}, {fn})")

            key = (st, sn, fn)
            if key in seen_keys:
                raise ValueError(f"Duplicate ground-truth composite key found at row {idx+1}: {key}")
            seen_keys.add(key)

            # Validate expected_class
            exp_raw = row.get("expected_class")
            if pd.isna(exp_raw) or str(exp_raw).strip() == "" or str(exp_raw).strip().lower() == "nan":
                expected_class = None
            else:
                expected_class = str(exp_raw).strip()
                if expected_class not in BENCHMARK_CLASSES:
                    raise ValueError(
                        f"Row {idx+1} has invalid expected_class '{expected_class}'. "
                        f"Expected one of {BENCHMARK_CLASSES} or empty/None."
                    )

            # Validate is_personal_data boolean
            ipd_raw = row["is_personal_data"]
            if isinstance(ipd_raw, bool):
                is_personal_data = ipd_raw
            elif isinstance(ipd_raw, (int, float)):
                is_personal_data = bool(ipd_raw)
            elif str(ipd_raw).strip().lower() in {"true", "1", "yes", "t"}:
                is_personal_data = True
            elif str(ipd_raw).strip().lower() in {"false", "0", "no", "f"}:
                is_personal_data = False
            else:
                raise ValueError(f"Row {idx+1} has invalid boolean value for is_personal_data: '{ipd_raw}'")

            # Logical consistency check
            if expected_class is not None and not is_personal_data:
                raise ValueError(
                    f"Row {idx+1} is inconsistent: expected_class is '{expected_class}' but is_personal_data is False."
                )

            notes = str(row["notes"]).strip() if "notes" in row and pd.notna(row["notes"]) else None

            records.append(
                GroundTruthRecord(
                    source_type=st,
                    source_name=sn,
                    field_name=fn,
                    expected_class=expected_class,
                    is_personal_data=is_personal_data,
                    notes=notes,
                )
            )

        return records

    # ----------------------------------------------------------------------
    # Core Evaluation Logic
    # ----------------------------------------------------------------------

    def evaluate(
        self,
        scanner_results: list[FieldDetectionResult],
        ground_truth_records: list[GroundTruthRecord],
    ) -> EvaluationReportSummary:
        """
        Compares scanner predictions against ground-truth labels and returns
        the comprehensive evaluation summary.
        """
        # Index ground truth by composite key
        gt_map: dict[tuple[str, str, str], GroundTruthRecord] = {
            gt.composite_key: gt for gt in ground_truth_records
        }

        # Index scanner predictions by composite key (normalizing key matching)
        scan_map: dict[tuple[str, str, str], FieldDetectionResult] = {}
        for r in scanner_results:
            key = (r.source_type.strip().upper(), r.source_name.strip(), r.field_name.strip())
            scan_map[key] = r

        gt_keys = set(gt_map.keys())
        scan_keys = set(scan_map.keys())

        matched_keys = sorted(gt_keys.intersection(scan_keys))
        unmatched_gt = sorted(gt_keys - scan_keys)
        unmatched_scan = sorted(scan_keys - gt_keys)

        warnings: list[str] = []
        limitations: list[str] = []

        if unmatched_gt:
            warnings.append(
                f"{len(unmatched_gt)} ground-truth records did not match any scanner output keys."
            )
        if unmatched_scan:
            warnings.append(
                f"{len(unmatched_scan)} scanner output records did not match any ground-truth keys."
            )

        # 1. Binary Candidate Detection Metrics (PII vs Non-PII)
        det_tp = 0
        det_fp = 0
        det_fn = 0
        det_tn = 0

        for key in matched_keys:
            gt_rec = gt_map[key]
            scan_rec = scan_map[key]

            is_expected_pii = gt_rec.is_personal_data
            is_predicted_pii = scan_rec.detected_class is not None

            if is_expected_pii and is_predicted_pii:
                det_tp += 1
            elif not is_expected_pii and is_predicted_pii:
                det_fp += 1
            elif is_expected_pii and not is_predicted_pii:
                det_fn += 1
            else:
                det_tn += 1

        det_prec = (det_tp / (det_tp + det_fp)) if (det_tp + det_fp) > 0 else None
        det_rec = (det_tp / (det_tp + det_fn)) if (det_tp + det_fn) > 0 else None
        det_f1 = (
            (2 * det_prec * det_rec / (det_prec + det_rec))
            if (det_prec is not None and det_rec is not None and (det_prec + det_rec) > 0)
            else None
        )

        detection_metrics = DetectionMetrics(
            tp=det_tp,
            fp=det_fp,
            fn=det_fn,
            tn=det_tn,
            total_evaluated=len(matched_keys),
            precision=round(det_prec, 4) if det_prec is not None else None,
            recall=round(det_rec, 4) if det_rec is not None else None,
            f1=round(det_f1, 4) if det_f1 is not None else None,
        )

        # 2. Per-Class One-vs-Rest Evaluation
        per_class_metrics: list[ClassMetrics] = []
        gt_class_dist: dict[str, int] = {c: 0 for c in self.target_classes}
        gt_class_dist["Non-PII"] = 0
        scan_class_dist: dict[str, int] = {c: 0 for c in self.target_classes}
        scan_class_dist["Not Detected"] = 0

        for key in matched_keys:
            gt_cls = gt_map[key].expected_class
            if gt_cls is None:
                gt_class_dist["Non-PII"] += 1
            else:
                gt_class_dist[gt_cls] = gt_class_dist.get(gt_cls, 0) + 1

            pred_cls = scan_map[key].detected_class
            if pred_cls is None:
                scan_class_dist["Not Detected"] += 1
            else:
                scan_class_dist[pred_cls] = scan_class_dist.get(pred_cls, 0) + 1

        for c in self.target_classes:
            tp = sum(
                1 for k in matched_keys
                if gt_map[k].expected_class == c and scan_map[k].detected_class == c
            )
            fp = sum(
                1 for k in matched_keys
                if gt_map[k].expected_class != c and scan_map[k].detected_class == c
            )
            fn = sum(
                1 for k in matched_keys
                if gt_map[k].expected_class == c and scan_map[k].detected_class != c
            )
            support = sum(
                1 for k in matched_keys
                if gt_map[k].expected_class == c
            )

            # Strict zero handling
            prec = (tp / (tp + fp)) if (tp + fp) > 0 else None
            rec = (tp / (tp + fn)) if (tp + fn) > 0 else None
            f1 = (
                (2 * prec * rec / (prec + rec))
                if (prec is not None and rec is not None and (prec + rec) > 0)
                else None
            )

            # Class status & sample size warning
            if support == 0:
                status = "Zero Ground-Truth Positives (Metrics Undefined)"
                warnings.append(f"Class '{c}' has 0 ground-truth positive examples.")
            elif (tp + fp) == 0:
                status = "Zero Predictions for Class (Precision Undefined)"
            elif support < self.small_sample_threshold:
                status = f"Limited Sample (Support={support} < {self.small_sample_threshold})"
                limitations.append(
                    f"Class '{c}' has very few positive examples (support={support}). "
                    "Metrics indicate prototype behavior on benchmark data, not statistical generalization."
                )
            else:
                status = "Evaluated"

            per_class_metrics.append(
                ClassMetrics(
                    class_name=c,
                    tp=tp,
                    fp=fp,
                    fn=fn,
                    support=support,
                    precision=round(prec, 4) if prec is not None else None,
                    recall=round(rec, 4) if rec is not None else None,
                    f1=round(f1, 4) if f1 is not None else None,
                    status=status,
                )
            )

        # 3. Confusion Matrix: rows = Ground Truth (Classes + Non-PII), cols = Predicted (Classes + Not Detected)
        row_labels = self.target_classes + ["Non-PII"]
        col_labels = self.target_classes + ["Not Detected"]
        confusion_matrix: dict[str, dict[str, int]] = {
            r: {c: 0 for c in col_labels} for r in row_labels
        }

        for key in matched_keys:
            gt_row_label = gt_map[key].expected_class or "Non-PII"
            pred_col_label = scan_map[key].detected_class or "Not Detected"
            confusion_matrix[gt_row_label][pred_col_label] += 1

        # 4. Detailed Error Extraction
        errors: list[EvaluationErrorRecord] = []
        for key in matched_keys:
            gt_rec = gt_map[key]
            scan_rec = scan_map[key]

            exp_cls = gt_rec.expected_class
            pred_cls = scan_rec.detected_class

            if exp_cls == pred_cls:
                continue  # Exact match

            # Categorize error
            if exp_cls is None and pred_cls is not None:
                err_type = "False Positive Detection"
            elif exp_cls is not None and pred_cls is None:
                err_type = "False Negative Detection"
            else:  # exp_cls is not None and pred_cls is not None and exp_cls != pred_cls
                err_type = "Misclassification (Wrong Class)"

            errors.append(
                EvaluationErrorRecord(
                    source_type=gt_rec.source_type,
                    source_name=gt_rec.source_name,
                    field_name=gt_rec.field_name,
                    expected_class=exp_cls,
                    predicted_class=pred_cls,
                    is_personal_data_expected=gt_rec.is_personal_data,
                    is_personal_data_predicted=pred_cls is not None,
                    error_type=err_type,
                    confidence=scan_rec.confidence,
                    confidence_level=scan_rec.confidence_level,
                    reason=scan_rec.reason,
                )
            )

        # General prototype limitations
        limitations.append(
            "Evaluation was conducted on synthetic records with known rule structures. "
            "Real enterprise data will contain unseen schemas, ambiguous abbreviations, and noisy values."
        )

        return EvaluationReportSummary(
            generated_at=datetime.now(timezone.utc).isoformat(),
            ground_truth_total=len(ground_truth_records),
            scanner_predictions_total=len(scanner_results),
            matched_records_count=len(matched_keys),
            unmatched_ground_truth_count=len(unmatched_gt),
            unmatched_scanner_count=len(unmatched_scan),
            unmatched_ground_truth_keys=[
                {"source_type": k[0], "source_name": k[1], "field_name": k[2]}
                for k in unmatched_gt
            ],
            unmatched_scanner_keys=[
                {"source_type": k[0], "source_name": k[1], "field_name": k[2]}
                for k in unmatched_scan
            ],
            ground_truth_class_distribution=gt_class_dist,
            scanner_class_distribution=scan_class_dist,
            detection_metrics=detection_metrics,
            per_class_metrics=per_class_metrics,
            confusion_matrix=confusion_matrix,
            total_errors=len(errors),
            data_quality_warnings=warnings,
            limitations=limitations,
        )

    def extract_error_records(
        self,
        scanner_results: list[FieldDetectionResult],
        ground_truth_records: list[GroundTruthRecord],
    ) -> list[EvaluationErrorRecord]:
        """
        Returns full list of mismatch error records with scanner evidence details.
        """
        gt_map = {gt.composite_key: gt for gt in ground_truth_records}
        scan_map = {
            (r.source_type.strip().upper(), r.source_name.strip(), r.field_name.strip()): r
            for r in scanner_results
        }
        matched_keys = sorted(set(gt_map.keys()).intersection(set(scan_map.keys())))

        errors: list[EvaluationErrorRecord] = []
        for key in matched_keys:
            gt_rec = gt_map[key]
            scan_rec = scan_map[key]

            exp_cls = gt_rec.expected_class
            pred_cls = scan_rec.detected_class

            if exp_cls == pred_cls:
                continue

            if exp_cls is None and pred_cls is not None:
                err_type = "False Positive Detection"
            elif exp_cls is not None and pred_cls is None:
                err_type = "False Negative Detection"
            else:
                err_type = "Misclassification (Wrong Class)"

            errors.append(
                EvaluationErrorRecord(
                    source_type=gt_rec.source_type,
                    source_name=gt_rec.source_name,
                    field_name=gt_rec.field_name,
                    expected_class=exp_cls,
                    predicted_class=pred_cls,
                    is_personal_data_expected=gt_rec.is_personal_data,
                    is_personal_data_predicted=pred_cls is not None,
                    error_type=err_type,
                    confidence=scan_rec.confidence,
                    confidence_level=scan_rec.confidence_level,
                    reason=scan_rec.reason,
                )
            )

        return errors
