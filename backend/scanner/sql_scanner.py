"""
backend/scanner/sql_scanner.py
================================
SQLite/SQLAlchemy scanner wrapper for PS-019 TC-303.

This module is intentionally thin. All classification logic lives in
detector.py — this file only handles database introspection and sampling.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, inspect, text

from backend.scanner.detector import FieldDetectionResult, PersonalDataDetector


class SQLScanner:
    """
    Scans all tables in a SQLite database and returns one FieldDetectionResult
    per column, across all discovered tables.

    The scanner delegates ALL detection logic to the shared
    PersonalDataDetector engine — no classification rules live here.

    Strategy
    --------
    - Uses SQLAlchemy ``inspect()`` to discover tables without needing the ORM
      models.  This makes the scanner generic: it works with any SQLite file.
    - Reads only a limited sample of rows (``sample_rows``) to keep scanning
      safe on large databases.
    - Column metadata (dtype, nullability) is inferred from the pandas
      DataFrame after loading the sample.

    Parameters
    ----------
    detector    : A configured PersonalDataDetector instance.
    sample_rows : Maximum rows to SELECT per table for value analysis.
    """

    def __init__(
        self,
        detector: PersonalDataDetector,
        sample_rows: int = 200,
    ) -> None:
        self._detector    = detector
        self._sample_rows = sample_rows

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def scan(self, db_path: str | Path) -> dict[str, list[FieldDetectionResult]]:
        """
        Connect to *db_path*, discover tables, scan every column.

        Parameters
        ----------
        db_path : Path to the SQLite ``.db`` file.

        Returns
        -------
        Dict mapping table name → list of FieldDetectionResult.

        Raises
        ------
        FileNotFoundError : If the database file does not exist.
        """
        db_path = Path(db_path)
        if not db_path.exists():
            raise FileNotFoundError(f"SQLite database not found: {db_path}")

        db_file  = db_path.name          # e.g. "privacy_demo.db"
        db_url   = f"sqlite:///{db_path}"
        engine   = create_engine(db_url, echo=False)
        inspector = inspect(engine)

        table_names: list[str] = inspector.get_table_names()
        results_by_table: dict[str, list[FieldDetectionResult]] = {}

        with engine.connect() as conn:
            for table in table_names:
                # ── Sample rows from the table ─────────────────────────
                sample_df: pd.DataFrame = pd.read_sql(
                    text(f"SELECT * FROM {table} LIMIT :n"),   # noqa: S608
                    conn,
                    params={"n": self._sample_rows},
                )

                table_results: list[FieldDetectionResult] = []
                source_name = f"{db_file}:{table}"

                for col in sample_df.columns:
                    result = self._detector.detect(
                        field_name  = col,
                        series      = sample_df[col],
                        source_type = "SQL",
                        source_name = source_name,
                    )
                    table_results.append(result)

                results_by_table[table] = table_results

        engine.dispose()
        return results_by_table

    def scan_flat(self, db_path: str | Path) -> list[FieldDetectionResult]:
        """
        Convenience method: scan all tables and return a flat list.
        Useful when callers do not need per-table grouping.
        """
        nested = self.scan(db_path)
        return [result for table_results in nested.values() for result in table_results]
