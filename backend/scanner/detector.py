"""
backend/scanner/detector.py
===========================
Core personal-data detection engine for PS-019 TC-303.

This module is the SINGLE source of classification logic.
Both the CSV scanner and the SQL scanner call into this engine.
No classification logic lives in the scanner wrappers.

IMPORTANT SCOPE NOTE
--------------------
This engine identifies *candidate* personal-data fields based on
configurable technical evidence. It does NOT determine whether
processing is lawful or compliant with any specific regulation.
All outputs are technical evidence for human review.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Default rules path  (backend/config/rules.json relative to this file)
# ---------------------------------------------------------------------------
_DEFAULT_RULES_PATH = Path(__file__).parent.parent / "config" / "rules.json"


# ===========================================================================
# Result models
# ===========================================================================

class EvidenceDetail(BaseModel):
    """Structured evidence that explains how the confidence was derived."""

    keyword_match: bool = Field(description="True if the column name matched any class keyword.")
    keyword_match_type: Optional[str] = Field(
        default=None,
        description="'exact' | 'token' | 'substring' — or None when no keyword matched.",
    )
    keyword_score: float = Field(description="Score contribution from keyword matching.")
    pattern_matched: bool = Field(description="True if >= 50% of sampled values matched a pattern.")
    pattern_name: Optional[str] = Field(default=None, description="Name of the best-matching pattern.")
    pattern_match_rate: Optional[float] = Field(
        default=None,
        description="Fraction of non-null sampled values that matched the best pattern (0–1).",
    )
    pattern_score: float = Field(description="Score contribution from pattern matching.")
    dtype: str = Field(description="Pandas dtype of the column.")
    dtype_score: float = Field(description="Score contribution from dtype matching class hints.")


class FieldDetectionResult(BaseModel):
    """Complete detection result for a single field/column."""

    source_type: str = Field(description="'CSV' or 'SQL'.")
    source_name: str = Field(description="File name or 'db_file:table_name'.")
    field_name: str = Field(description="Original column/field name.")
    detected_class: Optional[str] = Field(
        default=None,
        description="Detected personal-data class, or None if below confidence threshold.",
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Composite confidence score (0–1).")
    confidence_level: str = Field(description="'High' | 'Medium' | 'Low' | 'None'.")
    review_required: bool = Field(
        description="True when evidence is weak, ambiguous, or keyword/pattern conflict exists."
    )
    evidence: EvidenceDetail
    sample_count: int = Field(description="Total values in the column (including nulls).")
    non_null_count: int = Field(description="Non-null values in the column.")
    pattern_match_rate: Optional[float] = Field(
        default=None,
        description="Convenience alias for evidence.pattern_match_rate.",
    )
    reason: str = Field(description="Human-readable explanation of the detection decision.")


# ===========================================================================
# Internal intermediate type
# ===========================================================================

class _ClassScore:
    """Holds raw scoring components for one data class."""

    __slots__ = (
        "class_name",
        "keyword_type",
        "keyword_score",
        "pattern_score",
        "pattern_rate",
        "pattern_name",
        "dtype_score",
        "dtype",
        "total",
    )

    def __init__(
        self,
        class_name: str,
        keyword_type: Optional[str],
        keyword_score: float,
        pattern_score: float,
        pattern_rate: Optional[float],
        pattern_name: Optional[str],
        dtype_score: float,
        dtype: str = "",
    ) -> None:
        self.class_name = class_name
        self.keyword_type = keyword_type
        self.keyword_score = keyword_score
        self.pattern_score = pattern_score
        self.pattern_rate = pattern_rate
        self.pattern_name = pattern_name
        self.dtype_score = dtype_score
        self.dtype = dtype
        self.total = min(1.0, keyword_score + pattern_score + dtype_score)


# ===========================================================================
# Detection Engine
# ===========================================================================

class PersonalDataDetector:
    """
    Rule-based engine that identifies candidate personal-data fields.

    Detection combines three independent evidence sources:
      A) Column-name keyword matching  (normalisation handles case/separators)
      B) Pandas dtype alignment with class hints
      C) Value-pattern matching on a random sample of non-null values

    The final confidence score is the *additive sum* of the three evidence
    contributions, capped at 1.0. Scoring weights and thresholds are
    loaded from rules.json so they can be tuned without code changes.

    Usage
    -----
    >>> detector = PersonalDataDetector()          # uses default rules
    >>> result = detector.detect("email", series, "CSV", "customers.csv")
    >>> print(result.detected_class, result.confidence)
    """

    # Regex used to split camelCase/PascalCase names
    _CAMEL_SPLIT_1 = re.compile(r"([a-z0-9])([A-Z])")
    _CAMEL_SPLIT_2 = re.compile(r"([A-Z]+)([A-Z][a-z])")
    _SEPARATOR_RE  = re.compile(r"[\-\s\.]")

    def __init__(self, rules_path: str | Path = _DEFAULT_RULES_PATH) -> None:
        rules_path = Path(rules_path)
        if not rules_path.exists():
            raise FileNotFoundError(f"Rules file not found: {rules_path}")
        with open(rules_path, encoding="utf-8") as f:
            self._rules: dict[str, Any] = json.load(f)

        self._scoring    = self._rules["scoring"]
        self._thresholds = self._rules["thresholds"]
        self._sample_size: int = self._rules.get("sample_size", 100)
        self._classes: dict[str, Any] = self._rules["classes"]

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def detect(
        self,
        field_name: str,
        series: pd.Series,
        source_type: str,
        source_name: str,
    ) -> FieldDetectionResult:
        """
        Analyse a single column and return a FieldDetectionResult.

        Parameters
        ----------
        field_name:  Original column/field name (any casing / separator style).
        series:      Pandas Series containing the column values.
        source_type: 'CSV' or 'SQL'.
        source_name: Human-readable source identifier (e.g. 'customers.csv').
        """
        # --- 1. Normalise column name → token list -----------------------
        col_tokens     = self._normalize_name(field_name)
        col_normalized = "_".join(col_tokens)   # e.g. "customer_email"

        # --- 2. Prepare a sample of non-null values ----------------------
        non_null = series.dropna()
        if len(non_null) > self._sample_size:
            sample = non_null.sample(self._sample_size, random_state=42)
        else:
            sample = non_null

        dtype_str = str(series.dtype)

        # --- 3. Score every class ----------------------------------------
        class_scores: list[_ClassScore] = []
        for class_name, class_cfg in self._classes.items():
            kw_type, kw_score = self._score_keywords(
                col_tokens, col_normalized, class_cfg.get("keywords", [])
            )
            pat_score, pat_rate, pat_name = self._score_patterns(
                sample, class_cfg.get("patterns", [])
            )
            dt_score = self._score_dtype(
                dtype_str, class_cfg.get("dtype_hints", [])
            )
            class_scores.append(
                _ClassScore(class_name, kw_type, kw_score, pat_score, pat_rate, pat_name, dt_score, dtype_str)
            )

        # --- 4. Pick the best class --------------------------------------
        best: _ClassScore = max(class_scores, key=lambda s: s.total)

        if best.total < self._thresholds["low"]:
            detected_class: Optional[str] = None
        else:
            detected_class = best.class_name

        confidence = round(best.total, 4)

        # --- 5. Confidence level label -----------------------------------
        confidence_level = self._confidence_label(confidence)

        # --- 6. review_required flag -------------------------------------
        #   True when:
        #   (a) confidence is below the "high" threshold   AND we have a class, OR
        #   (b) keyword matched but value-pattern evidence contradicts it
        #       (patterns exist, were checked, and nearly nothing matched).
        has_patterns = bool(self._classes.get(best.class_name or "", {}).get("patterns", []))
        pattern_conflict = (
            has_patterns
            and best.keyword_score >= self._scoring["keyword_token"]
            and best.pattern_rate is not None
            and best.pattern_rate < 0.20
        )
        review_required = bool(
            (detected_class is not None and confidence < self._thresholds["review_required_max"])
            or pattern_conflict
        )

        # --- 7. Evidence object ------------------------------------------
        evidence = EvidenceDetail(
            keyword_match      = best.keyword_type is not None,
            keyword_match_type = best.keyword_type,
            keyword_score      = round(best.keyword_score, 4),
            pattern_matched    = (best.pattern_rate or 0.0) >= 0.50,
            pattern_name       = best.pattern_name,
            pattern_match_rate = round(best.pattern_rate, 4) if best.pattern_rate is not None else None,
            pattern_score      = round(best.pattern_score, 4),
            dtype              = dtype_str,
            dtype_score        = round(best.dtype_score, 4),
        )

        # --- 8. Human-readable reason ------------------------------------
        reason = self._build_reason(
            field_name, detected_class, best, has_patterns, pattern_conflict
        )

        return FieldDetectionResult(
            source_type       = source_type,
            source_name       = source_name,
            field_name        = field_name,
            detected_class    = detected_class,
            confidence        = confidence,
            confidence_level  = confidence_level,
            review_required   = review_required,
            evidence          = evidence,
            sample_count      = int(len(series)),
            non_null_count    = int(len(non_null)),
            pattern_match_rate= round(best.pattern_rate, 4) if best.pattern_rate is not None else None,
            reason            = reason,
        )

    # ------------------------------------------------------------------
    # Private helpers — Column-name normalisation
    # ------------------------------------------------------------------

    def _normalize_name(self, name: str) -> list[str]:
        """
        Return a list of lower-case tokens from a column name.

        Handles: camelCase, PascalCase, snake_case, kebab-case, spaces, dots.

        Examples
        --------
        "customerEmail"  → ["customer", "email"]
        "full_name"      → ["full", "name"]
        "EMAIL"          → ["email"]
        "customer-email" → ["customer", "email"]
        "customer.email" → ["customer", "email"]
        """
        # Split camelCase / PascalCase
        s = self._CAMEL_SPLIT_1.sub(r"\1_\2", name)
        s = self._CAMEL_SPLIT_2.sub(r"\1_\2", s)
        # Normalise non-underscore separators
        s = self._SEPARATOR_RE.sub("_", s)
        # Lower-case and split
        return [tok for tok in s.lower().split("_") if tok]

    # ------------------------------------------------------------------
    # Private helpers — Keyword scoring  (evidence source A)
    # ------------------------------------------------------------------

    def _score_keywords(
        self,
        col_tokens: list[str],
        col_normalized: str,
        keywords: list[str],
    ) -> tuple[Optional[str], float]:
        """
        Match column tokens against a list of class keywords.

        Match hierarchy (highest → lowest precedence):
          exact     : full normalised column name == normalised keyword
          token     : at least one column token matches a single-word keyword,
                      OR all tokens of a multi-word keyword appear in the column
          substring : normalised keyword appears as a substring of col_normalized

        Returns (match_type, score).
        """
        best_type:  Optional[str] = None
        best_score: float         = 0.0

        for keyword in keywords:
            kw_tokens     = self._normalize_name(keyword)
            kw_normalized = "_".join(kw_tokens)

            # ── Exact match: entire column name = keyword ──────────────
            if col_normalized == kw_normalized:
                score, mtype = self._scoring["keyword_exact"], "exact"

            # ── All multi-word keyword tokens present in column ────────
            elif len(kw_tokens) > 1 and all(t in col_tokens for t in kw_tokens):
                score, mtype = self._scoring["keyword_exact"], "exact"

            # ── Single keyword token appears as a column token ─────────
            elif len(kw_tokens) == 1 and kw_tokens[0] in col_tokens:
                score, mtype = self._scoring["keyword_token"], "token"

            # ── Keyword is a substring of the normalised column name ───
            elif kw_normalized in col_normalized:
                score, mtype = self._scoring["keyword_substring"], "substring"

            else:
                continue

            if score > best_score:
                best_score = score
                best_type  = mtype

        return best_type, best_score

    # ------------------------------------------------------------------
    # Private helpers — Dtype scoring  (evidence source B)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_dtype(dtype_str: str, hints: list[str]) -> float:
        """Return dtype_hint score if the column dtype aligns with class hints."""
        for hint in hints:
            if hint in dtype_str or dtype_str.startswith(hint):
                return 0.05
        return 0.0

    # ------------------------------------------------------------------
    # Private helpers — Pattern scoring  (evidence source C)
    # ------------------------------------------------------------------

    def _score_patterns(
        self,
        sample: pd.Series,
        patterns: list[dict],
    ) -> tuple[float, Optional[float], Optional[str]]:
        """
        Test sampled non-null values against configured regex patterns.

        Only the *best* matching pattern (highest match rate) is reported.
        If no patterns are defined for the class, returns (0.0, None, None)
        — the class is not penalised for the absence of patterns.

        Returns (score, match_rate, pattern_name).
        """
        if not patterns or len(sample) == 0:
            return 0.0, None, None

        sample_str = sample.astype(str)
        best_rate:  float           = 0.0
        best_name:  Optional[str]   = None

        for pat_def in patterns:
            try:
                pat_regex = re.compile(pat_def["regex"], re.IGNORECASE)
            except re.error:
                continue

            match_count = sample_str.apply(lambda v: bool(pat_regex.match(v))).sum()
            rate = float(match_count) / len(sample_str)

            if rate > best_rate:
                best_rate = rate
                best_name = pat_def.get("name")

        score = self._rate_to_pattern_score(best_rate)
        # If no pattern matched at all, still return a rate of 0.0 so the
        # caller knows patterns were checked and nothing matched.
        return score, best_rate, best_name

    def _rate_to_pattern_score(self, rate: float) -> float:
        s = self._scoring
        if rate >= 0.80:
            return s["pattern_high"]
        if rate >= 0.50:
            return s["pattern_medium"]
        if rate >= 0.20:
            return s["pattern_low"]
        if rate > 0.0:
            return s["pattern_minimal"]
        return 0.0

    # ------------------------------------------------------------------
    # Private helpers — Labels and reason
    # ------------------------------------------------------------------

    def _confidence_label(self, confidence: float) -> str:
        t = self._thresholds
        if confidence >= t["high"]:
            return "High"
        if confidence >= t["medium"]:
            return "Medium"
        if confidence >= t["low"]:
            return "Low"
        return "None"

    @staticmethod
    def _build_reason(
        field_name: str,
        detected_class: Optional[str],
        best: _ClassScore,
        has_patterns: bool,
        pattern_conflict: bool,
    ) -> str:
        parts: list[str] = []

        if detected_class is None:
            return (
                f"No personal-data class met the minimum confidence threshold "
                f"for field '{field_name}' (best score: {best.total:.2f}). "
                "No personal data detected."
            )

        if best.keyword_type == "exact":
            parts.append(
                f"Column name '{field_name}' exactly matches a '{detected_class}' keyword."
            )
        elif best.keyword_type == "token":
            parts.append(
                f"A token of '{field_name}' matches a '{detected_class}' keyword."
            )
        elif best.keyword_type == "substring":
            parts.append(
                f"Column name '{field_name}' contains a '{detected_class}' keyword as a substring."
            )

        if best.pattern_rate is not None:
            rate_pct = f"{best.pattern_rate * 100:.0f}%"
            if best.pattern_rate >= 0.50:
                parts.append(
                    f"Value pattern '{best.pattern_name}' matched {rate_pct} of sampled values."
                )
            else:
                parts.append(
                    f"Value pattern '{best.pattern_name}' matched only {rate_pct} of sampled values."
                )
        elif not has_patterns:
            parts.append("No value patterns are configured for this class; detection relies on column name.")

        if pattern_conflict:
            parts.append(
                "CONFLICT: keyword suggests personal data but value patterns do not confirm — review required."
            )

        if best.dtype_score > 0:
            parts.append(f"Column dtype '{best.dtype}' is consistent with the '{detected_class}' class.")

        return " ".join(parts) if parts else f"Classified as '{detected_class}' based on combined evidence."
