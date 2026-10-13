"""
backend/scanner/csv_scanner.py
===============================
CSV-specific scanner wrapper for PS-019 TC-303.

This module is intentionally thin. All classification logic lives in
detector.py — this file only handles CSV I/O and pandas loading.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from backend.scanner.detector import FieldDetectionResult, PersonalDataDetector


class CSVScanner:
    """
    Scans a single CSV file and returns one FieldDetectionResult per column.

    The scanner delegates ALL detection logic to the shared
    PersonalDataDetector engine — no classification rules live here.

    Parameters
    ----------
    detector    : A configured PersonalDataDetector instance.
    sample_rows : Maximum number of rows to read for value-pattern analysis.
                  Reading is done with ``nrows`` to keep memory usage low on
                  large files.  Pass None to read the full file.
    """

    def __init__(
        self,
        detector: PersonalDataDetector,
        sample_rows: Optional[int] = 500,
    ) -> None:
        self._detector   = detector
        self._sample_rows = sample_rows

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def scan(self, path: str | Path) -> list[FieldDetectionResult]:
        """
        Load *path* as a CSV, inspect every column, return detection results.

        Parameters
        ----------
        path : Absolute or relative path to the CSV file.

        Returns
        -------
        List of FieldDetectionResult, one entry per column in the CSV.

        Raises
        ------
        FileNotFoundError : If the CSV file does not exist.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {path}")

        source_name = path.name          # e.g. "customers.csv"

        # Read a limited number of rows to keep scanning fast on large files.
        df = pd.read_csv(path, nrows=self._sample_rows)

        results: list[FieldDetectionResult] = []
        for col in df.columns:
            result = self._detector.detect(
                field_name  = col,
                series      = df[col],
                source_type = "CSV",
                source_name = source_name,
            )
            results.append(result)

        return results
