"""
backend/scanner/scanner_service.py
====================================
Orchestration layer for PS-019 TC-303.

Provides a single, easy-to-use ScannerService that wires together:
  - PersonalDataDetector  (rules loaded from backend/config/rules.json)
  - CSVScanner            (CSV file scanning)
  - SQLScanner            (SQLite database scanning)

This is the class that will later be connected to FastAPI endpoints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from backend.scanner.csv_scanner import CSVScanner
from backend.scanner.detector import FieldDetectionResult, PersonalDataDetector
from backend.scanner.sql_scanner import SQLScanner

# ---------------------------------------------------------------------------
# Default paths (resolved relative to this file's location in the project)
# ---------------------------------------------------------------------------
_PROJECT_ROOT    = Path(__file__).parent.parent.parent
_DEFAULT_CSV_DIR = _PROJECT_ROOT / "data" / "csv"
_DEFAULT_DB_PATH = _PROJECT_ROOT / "data" / "sql" / "privacy_demo.db"
_DEFAULT_RULES   = _PROJECT_ROOT / "backend" / "config" / "rules.json"


# ===========================================================================
# Scan result containers
# ===========================================================================

@dataclass
class CSVScanResult:
    """Detection results for a single CSV file."""
    source_path: str
    source_name: str
    field_results: list[FieldDetectionResult] = field(default_factory=list)

    @property
    def detected_fields(self) -> list[FieldDetectionResult]:
        """Fields with a non-None detected_class."""
        return [r for r in self.field_results if r.detected_class is not None]

    @property
    def review_required_fields(self) -> list[FieldDetectionResult]:
        return [r for r in self.field_results if r.review_required]


@dataclass
class SQLScanResult:
    """Detection results for a single SQLite database (all tables)."""
    source_path: str
    db_name: str
    tables: dict[str, list[FieldDetectionResult]] = field(default_factory=dict)

    @property
    def all_results(self) -> list[FieldDetectionResult]:
        return [r for table_results in self.tables.values() for r in table_results]

    @property
    def detected_fields(self) -> list[FieldDetectionResult]:
        return [r for r in self.all_results if r.detected_class is not None]

    @property
    def review_required_fields(self) -> list[FieldDetectionResult]:
        return [r for r in self.all_results if r.review_required]


@dataclass
class FullScanReport:
    """Aggregated results from one complete scan run."""
    csv_results: list[CSVScanResult] = field(default_factory=list)
    sql_results: list[SQLScanResult] = field(default_factory=list)

    @property
    def all_field_results(self) -> list[FieldDetectionResult]:
        csv_all = [r for cr in self.csv_results for r in cr.field_results]
        sql_all = [r for sr in self.sql_results for r in sr.all_results]
        return csv_all + sql_all

    @property
    def all_detected(self) -> list[FieldDetectionResult]:
        return [r for r in self.all_field_results if r.detected_class is not None]

    @property
    def all_review_required(self) -> list[FieldDetectionResult]:
        return [r for r in self.all_field_results if r.review_required]

    def detected_by_class(self) -> dict[str, list[FieldDetectionResult]]:
        """Group all detected fields by their data class."""
        grouped: dict[str, list[FieldDetectionResult]] = {}
        for r in self.all_detected:
            grouped.setdefault(r.detected_class, []).append(r)  # type: ignore[arg-type]
        return grouped


# ===========================================================================
# ScannerService
# ===========================================================================

class ScannerService:
    """
    High-level orchestrator that exposes simple scan methods.

    Internally it instantiates the detector and both scanner wrappers,
    ensuring they all share the same detector instance.

    Parameters
    ----------
    rules_path : Path to rules.json. Defaults to backend/config/rules.json.
    csv_dir    : Directory containing CSV files to scan. Defaults to data/csv/.
    db_path    : Path to the SQLite demo database. Defaults to data/sql/privacy_demo.db.
    """

    def __init__(
        self,
        rules_path: Optional[str | Path] = None,
        csv_dir:    Optional[str | Path] = None,
        db_path:    Optional[str | Path] = None,
    ) -> None:
        self._rules_path = Path(rules_path) if rules_path else _DEFAULT_RULES
        self._csv_dir    = Path(csv_dir)    if csv_dir    else _DEFAULT_CSV_DIR
        self._db_path    = Path(db_path)    if db_path    else _DEFAULT_DB_PATH

        # Single shared detector instance
        self._detector = PersonalDataDetector(self._rules_path)

        # Scanner wrappers
        self._csv_scanner = CSVScanner(self._detector)
        self._sql_scanner = SQLScanner(self._detector)

    # ------------------------------------------------------------------

    def scan_csv(self, path: str | Path) -> CSVScanResult:
        """Scan a single CSV file."""
        path = Path(path)
        results = self._csv_scanner.scan(path)
        return CSVScanResult(
            source_path  = str(path),
            source_name  = path.name,
            field_results= results,
        )

    def scan_sqlite(self, db_path: Optional[str | Path] = None) -> SQLScanResult:
        """Scan the SQLite database (defaults to data/sql/privacy_demo.db)."""
        db_path = Path(db_path) if db_path else self._db_path
        tables  = self._sql_scanner.scan(db_path)
        return SQLScanResult(
            source_path = str(db_path),
            db_name     = db_path.name,
            tables      = tables,
        )

    def scan_all_csv(self) -> list[CSVScanResult]:
        """Scan every *.csv file found in the configured csv_dir."""
        csv_files = sorted(self._csv_dir.glob("*.csv"))
        return [self.scan_csv(f) for f in csv_files]

    def run_full_scan(self) -> FullScanReport:
        """
        Run a complete scan: all CSV files + the SQLite database.

        Returns a FullScanReport that aggregates every result.
        """
        report = FullScanReport()
        report.csv_results = self.scan_all_csv()
        report.sql_results = [self.scan_sqlite()]
        return report
