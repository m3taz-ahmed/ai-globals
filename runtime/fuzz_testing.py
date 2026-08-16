#!/usr/bin/env python3
"""Fuzz testing harness for policy and authorization (from agent-policy-engine).

Generates random inputs to test policy evaluation robustness.
Catches edge cases that structured tests might miss.

Usage::

    from runtime.fuzz_testing import PolicyFuzzer

    fuzzer = PolicyFuzzer(iterations=1000)
    results = fuzzer.fuzz()
    print(f"Crashes: {results.crashes}, Edge cases: {results.edge_cases}")
"""

from __future__ import annotations

import random
import string
from dataclasses import dataclass, field

from runtime.authorization import AuthorizationTuple, PolicyDecisionPoint


@dataclass
class FuzzResult:
    """Result of a fuzz testing run."""

    iterations: int = 0
    crashes: int = 0
    edge_cases: int = 0
    errors: list[str] = field(default_factory=list)
    decisions: dict[str, int] = field(default_factory=dict)


@dataclass
class PolicyFuzzer:
    """Fuzz test the policy decision point (from agent-policy-engine).

    Generates random AuthorizationTuples and evaluates them,
    catching crashes and recording edge cases.
    """

    iterations: int = 1000
    seed: int = 42
    operations: list[str] = field(default_factory=lambda: [
        "read", "write", "deploy", "delete", "spend", "grant_access",
        "git.push", "unknown_op", "", "EXECUTE",
    ])
    targets: list[str] = field(default_factory=lambda: [
        "doc1", "prod", "db", "secret.key", "../../../etc/passwd",
        "", "target with spaces", "a" * 1000,
    ])
    risk_scores: list[float] = field(default_factory=lambda: [
        0.0, 0.1, 0.5, 0.8, 0.85, 0.99, 1.0, -1.0, 999.0,
    ])

    def fuzz(self, pdp: PolicyDecisionPoint | None = None) -> FuzzResult:
        """Run fuzz testing on the PDP."""
        random.seed(self.seed)
        pdp = pdp or PolicyDecisionPoint()
        result = FuzzResult(iterations=self.iterations)
        for _ in range(self.iterations):
            tup = self._generate_random_tuple()
            try:
                decision = pdp.decide(tup)
                result.decisions[decision.decision] = (
                    result.decisions.get(decision.decision, 0) + 1
                )
                # Edge case: empty target or very high risk
                if not tup.target_id or tup.risk_score > 1.0:
                    result.edge_cases += 1
            except Exception as e:
                result.crashes += 1
                result.errors.append(str(e)[:200])
        return result

    def _generate_random_tuple(self) -> AuthorizationTuple:
        """Generate a random AuthorizationTuple."""
        return AuthorizationTuple(
            subject_id=self._random_string(8),
            tenant_id=self._random_string(6),
            workload_id=self._random_string(6),
            operation_id=random.choice(self.operations),
            target_id=random.choice(self.targets),
            risk_score=random.choice(self.risk_scores),
            delegated_scope=tuple(random.sample(
                ["read", "write", "deploy", "admin"],
                random.randint(0, 4),
            )),
            requested_scope=tuple(random.sample(
                ["read", "write", "deploy", "admin"],
                random.randint(0, 2),
            )),
        )

    @staticmethod
    def _random_string(length: int) -> str:
        return "".join(random.choices(string.ascii_lowercase, k=length))


if __name__ == "__main__":
    fuzzer = PolicyFuzzer(iterations=100)
    result = fuzzer.fuzz()
    print(f"Iterations: {result.iterations}, Crashes: {result.crashes}")
    print(f"Decisions: {result.decisions}")
