#!/usr/bin/env python3
"""Fairness detection for EU AI Act compliance.

Inspired by sage: detects protected attributes and proxy attributes in a
data schema, recommends a fairness strategy, and emits EU AI Act Annex III
compliance notes.

A *protected attribute* is a field that directly encodes a protected
characteristic (age, sex, race, ...).  A *proxy attribute* is a field that
does not directly encode a protected characteristic but is statistically
correlated with one (e.g. ``zip_code`` is a proxy for race in many regions).

The :class:`FairnessDetector` also documents the *Fairness Impossibility
Theorem*: Equalized Odds, Differential Privacy, and Predictive Parity cannot
all be simultaneously satisfied for non-trivial classifiers.

Usage::

    from runtime.fairness_detector import FairnessDetector
    fd = FairnessDetector()
    report = fd.detect({"age": "int", "zip_code": "str", "name": "str"})
    notes = fd.compliance_notes(report.findings)
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

from runtime.schemas import AizeeError, ErrorSeverity, ValidationError

_logger = logging.getLogger(__name__)


class ProtectedAttribute(str, Enum):
    """Protected attributes under EU AI Act / GDPR Article 9."""

    AGE = "age"
    SEX = "sex"
    GENDER = "gender"
    RACE = "race"
    ETHNICITY = "ethnicity"
    RELIGION = "religion"
    DISABILITY = "disability"
    NATIONALITY = "nationality"
    MARITAL_STATUS = "marital_status"
    POLITICAL_OPINION = "political_opinion"


class FairnessStrategy(str, Enum):
    """Fairness mitigation strategies."""

    EQUALIZED_ODDS = "equalized_odds"
    DIFFERENTIAL_PRIVACY = "differential_privacy"
    PREDICTIVE_PARITY = "predictive_parity"
    DEMOGRAPHIC_PARITY = "demographic_parity"


@dataclass
class FairnessFinding:
    """A single fairness finding for one schema field.

    Attributes:
        attribute: The field name in the data schema.
        is_protected: Whether the field directly encodes a protected attribute.
        is_proxy: Whether the field is a proxy for a protected attribute.
        proxy_for: The protected attribute this field proxies, if any.
        severity: Severity of the finding (``"high"`` / ``"medium"`` / ``"low"``).
        evidence: Human-readable explanation of the finding.
        recommendation: Mitigation recommendation.
    """

    attribute: str
    is_protected: bool
    is_proxy: bool
    proxy_for: ProtectedAttribute | None
    severity: str
    evidence: str
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "attribute": self.attribute,
            "is_protected": self.is_protected,
            "is_proxy": self.is_proxy,
            "proxy_for": self.proxy_for.value if self.proxy_for else None,
            "severity": self.severity,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
        }


@dataclass
class FairnessReport:
    """Aggregate fairness report for a schema.

    Attributes:
        total_attributes_checked: Number of fields examined.
        protected_found: Count of protected attributes detected.
        proxies_found: Count of proxy attributes detected.
        strategy_recommended: The recommended :class:`FairnessStrategy`.
        findings: List of individual findings.
        compliance_notes: EU AI Act Annex III compliance notes.
    """

    total_attributes_checked: int
    protected_found: int
    proxies_found: int
    strategy_recommended: FairnessStrategy
    findings: list[FairnessFinding] = field(default_factory=list)
    compliance_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "total_attributes_checked": self.total_attributes_checked,
            "protected_found": self.protected_found,
            "proxies_found": self.proxies_found,
            "strategy_recommended": self.strategy_recommended.value,
            "findings": [f.to_dict() for f in self.findings],
            "compliance_notes": list(self.compliance_notes),
        }


class FairnessDetectorError(AizeeError):
    """Raised when the fairness detector encounters an internal error."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("FAIRNESS_ERROR", message, ErrorSeverity.HIGH, context)


class FairnessDetector:
    """Detect protected and proxy attributes in a data schema.

    Thread-safe.  Use :meth:`detect` to analyze a schema mapping field names
    to type strings.  An optional data sample can refine proxy detection.
    """

    # Regex patterns for direct protected-attribute detection.
    _PROTECTED_PATTERNS: ClassVar[dict[ProtectedAttribute, list[str]]] = {
        ProtectedAttribute.AGE: [
            r"\bage\b",
            r"\bdate_of_birth\b",
            r"\byear_born\b",
            r"\bdob\b",
            r"\bbirth_date\b",
        ],
        ProtectedAttribute.SEX: [
            r"\bsex\b",
            r"\bbiological_sex\b",
        ],
        ProtectedAttribute.GENDER: [
            r"\bgender\b",
            r"\bgender_identity\b",
        ],
        ProtectedAttribute.RACE: [
            r"\brace\b",
            r"\bethnic_origin\b",
        ],
        ProtectedAttribute.ETHNICITY: [
            r"\bethnicity\b",
            r"\bethnic_group\b",
        ],
        ProtectedAttribute.RELIGION: [
            r"\breligion\b",
            r"\breligious_belief\b",
            r"\bfaith\b",
        ],
        ProtectedAttribute.DISABILITY: [
            r"\bdisability\b",
            r"\bdisabled\b",
            r"\bimpairment\b",
        ],
        ProtectedAttribute.NATIONALITY: [
            r"\bnationality\b",
            r"\bcitizenship\b",
            r"\bcountry_of_origin\b",
        ],
        ProtectedAttribute.MARITAL_STATUS: [
            r"\bmarital_status\b",
            r"\bmarriage_status\b",
            r"\bcivil_status\b",
        ],
        ProtectedAttribute.POLITICAL_OPINION: [
            r"\bpolitical_opinion\b",
            r"\bpolitical_affiliation\b",
            r"\bpolitical_view\b",
        ],
    }

    # Proxy field names -> the protected attribute they proxy for.
    _PROXY_PATTERNS: ClassVar[dict[str, ProtectedAttribute]] = {
        "zip_code": ProtectedAttribute.RACE,
        "postcode": ProtectedAttribute.RACE,
        "postal_code": ProtectedAttribute.RACE,
        "name": ProtectedAttribute.RACE,
        "first_name": ProtectedAttribute.RACE,
        "last_name": ProtectedAttribute.ETHNICITY,
        "surname": ProtectedAttribute.ETHNICITY,
        "school": ProtectedAttribute.RACE,
        "school_name": ProtectedAttribute.RACE,
        "payment_history": ProtectedAttribute.RACE,
        "credit_score": ProtectedAttribute.RACE,
        "neighborhood": ProtectedAttribute.RACE,
        "address": ProtectedAttribute.NATIONALITY,
        "language": ProtectedAttribute.NATIONALITY,
        "accent": ProtectedAttribute.NATIONALITY,
    }

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._compiled_protected = self._compile_protected_patterns()

    def _compile_protected_patterns(
        self,
    ) -> dict[ProtectedAttribute, list[re.Pattern[str]]]:
        """Pre-compile protected-attribute regexes for performance."""
        compiled: dict[ProtectedAttribute, list[re.Pattern[str]]] = {}
        for attr, patterns in self._PROTECTED_PATTERNS.items():
            compiled[attr] = [re.compile(p, re.IGNORECASE) for p in patterns]
        return compiled

    # -- public API ---------------------------------------------------------

    def detect(
        self,
        schema: dict[str, str],
        data_sample: dict[str, list[Any]] | None = None,
    ) -> FairnessReport:
        """Detect protected and proxy attributes in *schema*.

        Args:
            schema: Mapping of field name -> type string (e.g. ``"int"``).
            data_sample: Optional mapping of field name -> sample values,
                used to refine proxy detection (currently informational).

        Returns:
            A :class:`FairnessReport` with all findings and recommendations.

        Raises:
            ValidationError: if *schema* is empty.
        """
        if not schema:
            raise ValidationError("Schema must not be empty")
        with self._lock:
            findings: list[FairnessFinding] = []
            for field_name in schema:
                finding = self._check_field(field_name, data_sample)
                if finding is not None:
                    findings.append(finding)
            protected_count = sum(1 for f in findings if f.is_protected)
            proxy_count = sum(1 for f in findings if f.is_proxy)
            strategy = self.recommend_strategy(findings)
            notes = self.compliance_notes(findings)
            return FairnessReport(
                total_attributes_checked=len(schema),
                protected_found=protected_count,
                proxies_found=proxy_count,
                strategy_recommended=strategy,
                findings=findings,
                compliance_notes=notes,
            )

    def _check_field(
        self,
        field_name: str,
        data_sample: dict[str, list[Any]] | None,
    ) -> FairnessFinding | None:
        """Check a single field for protected/proxy status."""
        protected = self._match_protected(field_name)
        if protected is not None:
            return FairnessFinding(
                attribute=field_name,
                is_protected=True,
                is_proxy=False,
                proxy_for=None,
                severity="high",
                evidence=f"Field '{field_name}' directly encodes protected attribute '{protected.value}'",
                recommendation="Remove this field or apply differential privacy",
            )
        proxy = self._match_proxy(field_name)
        if proxy is not None:
            return FairnessFinding(
                attribute=field_name,
                is_protected=False,
                is_proxy=True,
                proxy_for=proxy,
                severity="medium",
                evidence=f"Field '{field_name}' is a proxy for protected attribute '{proxy.value}'",
                recommendation="Audit correlation or remove from model features",
            )
        return None

    def _match_protected(self, field_name: str) -> ProtectedAttribute | None:
        """Return the protected attribute if *field_name* matches a pattern."""
        normalized = field_name.strip().lower().replace(" ", "_")
        for attr, patterns in self._compiled_protected.items():
            for pat in patterns:
                if pat.search(normalized):
                    return attr
        return None

    def _match_proxy(self, field_name: str) -> ProtectedAttribute | None:
        """Return the protected attribute if *field_name* is a known proxy."""
        normalized = field_name.strip().lower().replace(" ", "_")
        return self._PROXY_PATTERNS.get(normalized)

    # -- strategy & compliance ---------------------------------------------

    def check_fairness_impossibility(
        self,
        strategies: list[FairnessStrategy],
    ) -> list[str]:
        """Note which strategy combinations are mathematically impossible.

        The Fairness Impossibility Theorem states that Equalized Odds,
        Differential Privacy, and Predictive Parity cannot all be
        simultaneously satisfied for non-trivial classifiers.

        Returns a list of human-readable notes about impossible combinations.
        """
        notes: list[str] = []
        strategy_set = set(strategies)
        impossible_triple = {
            FairnessStrategy.EQUALIZED_ODDS,
            FairnessStrategy.DIFFERENTIAL_PRIVACY,
            FairnessStrategy.PREDICTIVE_PARITY,
        }
        if impossible_triple.issubset(strategy_set):
            notes.append(
                "Equalized Odds, Differential Privacy, and Predictive Parity "
                "cannot all be simultaneously satisfied for non-trivial "
                "classifiers (Fairness Impossibility Theorem)."
            )
        pairs: list[tuple[FairnessStrategy, FairnessStrategy]] = [
            (
                FairnessStrategy.EQUALIZED_ODDS,
                FairnessStrategy.PREDICTIVE_PARITY,
            ),
            (
                FairnessStrategy.DEMOGRAPHIC_PARITY,
                FairnessStrategy.PREDICTIVE_PARITY,
            ),
        ]
        for a, b in pairs:
            if a in strategy_set and b in strategy_set:
                notes.append(
                    f"{a.value} and {b.value} are generally incompatible "
                    "for non-trivial classifiers."
                )
        return notes

    def recommend_strategy(
        self,
        findings: list[FairnessFinding],
    ) -> FairnessStrategy:
        """Recommend the best fairness strategy for the given findings.

        Heuristic: if any protected attribute is directly present, prefer
        differential privacy.  If only proxies exist, prefer equalized odds.
        If no findings, default to demographic parity.
        """
        has_protected = any(f.is_protected for f in findings)
        has_proxy = any(f.is_proxy for f in findings)
        if has_protected:
            return FairnessStrategy.DIFFERENTIAL_PRIVACY
        if has_proxy:
            return FairnessStrategy.EQUALIZED_ODDS
        return FairnessStrategy.DEMOGRAPHIC_PARITY

    def compliance_notes(self, findings: list[FairnessFinding]) -> list[str]:
        """Generate EU AI Act Annex III compliance notes for *findings*."""
        notes: list[str] = []
        protected_findings = [f for f in findings if f.is_protected]
        proxy_findings = [f for f in findings if f.is_proxy]
        if protected_findings:
            attrs = ", ".join(f.attribute for f in protected_findings)
            notes.append(
                f"EU AI Act Annex III: protected attributes detected ({attrs}). "
                "Data must be anonymized or pseudonymized before processing."
            )
        if proxy_findings:
            proxies = ", ".join(f.attribute for f in proxy_findings)
            notes.append(
                f"EU AI Act Annex III: proxy attributes detected ({proxies}). "
                "Conduct a bias audit to assess disparate impact."
            )
        notes.append(
            "Fairness Impossibility Theorem: Equalized Odds, Differential "
            "Privacy, and Predictive Parity cannot all be simultaneously "
            "satisfied for non-trivial classifiers."
        )
        if not protected_findings and not proxy_findings:
            notes.append(
                "EU AI Act Annex III: no protected or proxy attributes "
                "detected in the schema. Routine fairness monitoring still "
                "recommended."
            )
        return notes
