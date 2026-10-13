"""
backend/evaluation/reporting.py
===============================
Report generators and exporters for Phase 5 — Evaluation.

Exports:
  1. reports/evaluation_summary.json
  2. reports/evaluation_per_class.csv
  3. reports/evaluation_confusion_matrix.csv
  4. reports/evaluation_errors.csv

SCOPE NOTE
----------
Reports provide technical evidence metrics only. They do not evaluate legal compliance.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Sequence

from backend.evaluation.models import (
    ClassMetrics,
    EvaluationErrorRecord,
    EvaluationReportSummary,
)

PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports"


class EvaluationReporter:
    """
    Handles report generation, CSV/JSON file export, and clean console rendering.
    """

    def __init__(self, reports_dir: str | Path = DEFAULT_REPORTS_DIR) -> None:
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def export_summary_json(
        self,
        summary: EvaluationReportSummary,
        filename: str = "evaluation_summary.json",
    ) -> Path:
        """Export comprehensive summary to structured JSON."""
        target = self.reports_dir / filename
        data = summary.model_dump()
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return target

    def export_per_class_csv(
        self,
        per_class_metrics: Sequence[ClassMetrics],
        filename: str = "evaluation_per_class.csv",
    ) -> Path:
        """Export per-class metrics table to CSV."""
        target = self.reports_dir / filename
        headers = ["class_name", "tp", "fp", "fn", "support", "precision", "recall", "f1", "status"]
        with open(target, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for m in per_class_metrics:
                writer.writerow({
                    "class_name": m.class_name,
                    "tp": m.tp,
                    "fp": m.fp,
                    "fn": m.fn,
                    "support": m.support,
                    "precision": f"{m.precision:.4f}" if m.precision is not None else "undefined",
                    "recall": f"{m.recall:.4f}" if m.recall is not None else "undefined",
                    "f1": f"{m.f1:.4f}" if m.f1 is not None else "undefined",
                    "status": m.status,
                })
        return target

    def export_confusion_matrix_csv(
        self,
        confusion_matrix: dict[str, dict[str, int]],
        filename: str = "evaluation_confusion_matrix.csv",
    ) -> Path:
        """Export confusion matrix to CSV."""
        target = self.reports_dir / filename
        row_keys = list(confusion_matrix.keys())
        col_keys = list(next(iter(confusion_matrix.values())).keys()) if confusion_matrix else []
        headers = ["expected_class"] + col_keys

        with open(target, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for row_label, cols in confusion_matrix.items():
                writer.writerow([row_label] + [cols.get(c, 0) for c in col_keys])
        return target

    def export_errors_csv(
        self,
        errors: Sequence[EvaluationErrorRecord],
        filename: str = "evaluation_errors.csv",
    ) -> Path:
        """Export detailed discrepancy error records to CSV."""
        target = self.reports_dir / filename
        headers = [
            "source_type",
            "source_name",
            "field_name",
            "expected_class",
            "predicted_class",
            "is_personal_data_expected",
            "is_personal_data_predicted",
            "error_type",
            "confidence",
            "confidence_level",
            "reason",
        ]
        with open(target, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for err in errors:
                writer.writerow({
                    "source_type": err.source_type,
                    "source_name": err.source_name,
                    "field_name": err.field_name,
                    "expected_class": err.expected_class or "",
                    "predicted_class": err.predicted_class or "",
                    "is_personal_data_expected": err.is_personal_data_expected,
                    "is_personal_data_predicted": err.is_personal_data_predicted,
                    "error_type": err.error_type,
                    "confidence": f"{err.confidence:.2f}" if err.confidence is not None else "",
                    "confidence_level": err.confidence_level or "",
                    "reason": err.reason or "",
                })
        return target

    def print_console_summary(
        self,
        summary: EvaluationReportSummary,
        errors: Sequence[EvaluationErrorRecord],
    ) -> None:
        """Print ASCII-safe formatted summary to console."""
        LINE = "=" * 70
        SUB = "-" * 70

        print()
        print(LINE)
        print("  PS-019 TC-303 — GROUND-TRUTH EVALUATION REPORT")
        print("  Precision, Recall, F1 and Error Analysis (Phase 5)")
        print(SUB)
        print(f"  Generated at: {summary.generated_at[:19].replace('T', ' ')} UTC")
        print(f"  Ground-Truth Records:    {summary.ground_truth_total}")
        print(f"  Scanner Output Records:  {summary.scanner_predictions_total}")
        print(f"  Matched Records:         {summary.matched_records_count}")
        if summary.unmatched_ground_truth_count or summary.unmatched_scanner_count:
            print(f"  Unmatched GT Records:    {summary.unmatched_ground_truth_count}")
            print(f"  Unmatched Scan Records:  {summary.unmatched_scanner_count}")

        print(LINE)
        print("  1. BINARY CANDIDATE DETECTION METRICS (PII vs Non-PII)")
        print(SUB)
        dm = summary.detection_metrics
        p_str = f"{dm.precision * 100:.1f}%" if dm.precision is not None else "N/A"
        r_str = f"{dm.recall * 100:.1f}%" if dm.recall is not None else "N/A"
        f_str = f"{dm.f1:.3f}" if dm.f1 is not None else "N/A"
        print(f"  TP: {dm.tp:<4}  FP: {dm.fp:<4}  FN: {dm.fn:<4}  TN: {dm.tn:<4}  (Total: {dm.total_evaluated})")
        print(f"  Precision: {p_str:<8} Recall: {r_str:<8} F1-Score: {f_str}")

        print()
        print(LINE)
        print("  2. PER-CLASS EVALUATION METRICS (One-vs-Rest)")
        print(SUB)
        print(f"  {'Class':<18} {'TP':>3} {'FP':>3} {'FN':>3} {'Supp':>5} {'Prec':>8} {'Recall':>8} {'F1':>8}  Status")
        print("  " + "-" * 85)
        for m in summary.per_class_metrics:
            prec_s = f"{m.precision:.3f}" if m.precision is not None else "    N/A"
            rec_s = f"{m.recall:.3f}" if m.recall is not None else "    N/A"
            f1_s = f"{m.f1:.3f}" if m.f1 is not None else "    N/A"
            print(f"  {m.class_name:<18} {m.tp:>3} {m.fp:>3} {m.fn:>3} {m.support:>5} {prec_s:>8} {rec_s:>8} {f1_s:>8}  {m.status}")

        print()
        print(LINE)
        print("  3. CONFUSION MATRIX (Expected vs Predicted)")
        print(SUB)
        col_names = list(next(iter(summary.confusion_matrix.values())).keys())
        col_header = "  " + f"{'Expected ↓ / Pred →':<22}" + "".join(f"{c[:8]:>9}" for c in col_names)
        print(col_header)
        print("  " + "-" * (22 + 9 * len(col_names)))
        for r_name, cols in summary.confusion_matrix.items():
            row_str = f"  {r_name:<22}" + "".join(f"{cols.get(c, 0):>9}" for c in col_names)
            print(row_str)

        print()
        print(LINE)
        print(f"  4. EVALUATION ERRORS & DISCREPANCIES (Total: {summary.total_errors})")
        print(SUB)
        if not errors:
            print("  No classification or detection discrepancies observed.")
        else:
            for i, err in enumerate(errors[:12], 1):
                exp = err.expected_class or "Non-PII"
                pred = err.predicted_class or "Not Detected"
                print(f"  [{i:>2}] {err.source_name:<26} {err.field_name:<20}")
                print(f"       Expected: {exp:<16} Predicted: {pred:<16} ({err.error_type})")
            if len(errors) > 12:
                print(f"       ... and {len(errors) - 12} additional errors (see evaluation_errors.csv)")

        if summary.limitations:
            print()
            print(LINE)
            print("  DATASET LIMITATIONS & QUALITY WARNINGS")
            print(SUB)
            for lim in summary.limitations:
                print(f"  * {lim}")

        print()
        print(LINE)
        print("  IMPORTANT DISCLAIMER")
        print(SUB)
        print("  These evaluation metrics represent technical testing on synthetic benchmark data.")
        print("  They do NOT constitute legal compliance validation, GDPR/DPDP certification,")
        print("  or an assurance of universal real-world accuracy.")
        print(LINE)
        print()
