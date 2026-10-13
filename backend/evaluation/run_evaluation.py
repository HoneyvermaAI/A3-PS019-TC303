"""
backend/evaluation/run_evaluation.py
===================================
CLI entry point for Phase 5 — Ground-Truth Evaluation and Per-Class Precision/Recall.

Workflow:
  1. Executes full personal-data scanner across synthetic CSV files and SQLite database.
  2. Loads and validates hand-labelled ground truth from data/ground_truth.csv.
  3. Executes one-vs-rest per-class metrics and candidate detection evaluation.
  4. Generates and exports:
       reports/evaluation_summary.json
       reports/evaluation_per_class.csv
       reports/evaluation_confusion_matrix.csv
       reports/evaluation_errors.csv
  5. Outputs formatted ASCII summary to terminal.

Usage:
  .venv\\Scripts\\python backend\\evaluation\\run_evaluation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.evaluation.evaluator import DEFAULT_GROUND_TRUTH_PATH, Evaluator
from backend.evaluation.reporting import EvaluationReporter
from backend.scanner.scanner_service import ScannerService


def main() -> None:
    print("\n[1/4] Running scanner on synthetic datasets (CSV + SQLite) ...")
    scanner_service = ScannerService()
    scan_report = scanner_service.run_full_scan()
    print(f"      Scanned {len(scan_report.all_field_results)} fields total.")
    print(f"      Identified {len(scan_report.all_detected)} candidate personal-data fields.")

    print("\n[2/4] Loading and validating ground truth from data/ground_truth.csv ...")
    evaluator = Evaluator()
    gt_records = evaluator.load_ground_truth(DEFAULT_GROUND_TRUTH_PATH)
    print(f"      Loaded {len(gt_records)} valid ground-truth records.")

    print("\n[3/4] Evaluating candidate detection and per-class classification metrics ...")
    summary = evaluator.evaluate(scan_report.all_field_results, gt_records)
    errors = evaluator.extract_error_records(scan_report.all_field_results, gt_records)
    print(f"      Evaluation completed. Matched {summary.matched_records_count} records.")

    print("\n[4/4] Exporting evaluation reports to reports/ ...")
    reporter = EvaluationReporter()
    p_json = reporter.export_summary_json(summary)
    p_csv = reporter.export_per_class_csv(summary.per_class_metrics)
    p_cm = reporter.export_confusion_matrix_csv(summary.confusion_matrix)
    p_err = reporter.export_errors_csv(errors)

    print(f"      -> {p_json}")
    print(f"      -> {p_csv}")
    print(f"      -> {p_cm}")
    print(f"      -> {p_err}")

    # Render summary to console
    reporter.print_console_summary(summary, errors)


if __name__ == "__main__":
    main()
