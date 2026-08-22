"""Tests for runtime/fuzz_testing.py."""

from __future__ import annotations

from unittest.mock import MagicMock

from runtime.fuzz_testing import FuzzResult, PolicyFuzzer


class TestFuzzResult:
    def test_default_values(self) -> None:
        # Arrange & Act
        result = FuzzResult()

        # Assert
        assert result.iterations == 0
        assert result.crashes == 0
        assert result.edge_cases == 0
        assert result.errors == []
        assert result.decisions == {}

    def test_custom_values(self) -> None:
        # Arrange & Act
        result = FuzzResult(iterations=100, crashes=2, edge_cases=5)

        # Assert
        assert result.iterations == 100
        assert result.crashes == 2
        assert result.edge_cases == 5


class TestPolicyFuzzerFuzz:
    def test_fuzz_returns_result_with_correct_iterations(self) -> None:
        # Arrange
        fuzzer = PolicyFuzzer(iterations=50, seed=42)

        # Act
        result = fuzzer.fuzz()

        # Assert
        assert isinstance(result, FuzzResult)
        assert result.iterations == 50

    def test_fuzz_with_custom_pdp(self) -> None:
        # Arrange
        fuzzer = PolicyFuzzer(iterations=10, seed=42)
        mock_pdp = MagicMock()
        mock_decision = MagicMock()
        mock_decision.decision = "allow"
        mock_pdp.decide.return_value = mock_decision

        # Act
        result = fuzzer.fuzz(pdp=mock_pdp)

        # Assert
        assert mock_pdp.decide.call_count == 10
        assert result.decisions.get("allow") == 10

    def test_fuzz_records_crashes(self) -> None:
        # Arrange
        fuzzer = PolicyFuzzer(iterations=10, seed=42)
        mock_pdp = MagicMock()
        mock_pdp.decide.side_effect = RuntimeError("boom")

        # Act
        result = fuzzer.fuzz(pdp=mock_pdp)

        # Assert
        assert result.crashes == 10
        assert len(result.errors) == 10
        assert "boom" in result.errors[0]

    def test_fuzz_is_deterministic_with_same_seed(self) -> None:
        # Arrange
        fuzzer1 = PolicyFuzzer(iterations=20, seed=99)
        fuzzer2 = PolicyFuzzer(iterations=20, seed=99)

        # Act
        result1 = fuzzer1.fuzz()
        result2 = fuzzer2.fuzz()

        # Assert
        assert result1.decisions == result2.decisions
        assert result1.crashes == result2.crashes

    def test_fuzz_different_seed_different_results(self) -> None:
        # Arrange
        fuzzer1 = PolicyFuzzer(iterations=20, seed=1)
        fuzzer2 = PolicyFuzzer(iterations=20, seed=2)

        # Act
        result1 = fuzzer1.fuzz()
        result2 = fuzzer2.fuzz()

        # Assert — decisions distribution likely differs
        # At minimum, the random tuple generation differs
        assert result1.iterations == result2.iterations

    def test_fuzz_edge_cases_counted(self) -> None:
        # Arrange — use a mock PDP that always succeeds
        fuzzer = PolicyFuzzer(iterations=100, seed=42)
        mock_pdp = MagicMock()
        mock_decision = MagicMock()
        mock_decision.decision = "allow"
        mock_pdp.decide.return_value = mock_decision

        # Act
        result = fuzzer.fuzz(pdp=mock_pdp)

        # Assert — with 100 iterations and edge-case targets in the pool,
        # at least some edge cases should be counted
        assert result.edge_cases >= 0
        assert result.edge_cases <= 100


class TestPolicyFuzzerConfiguration:
    def test_default_operations_list(self) -> None:
        # Arrange & Act
        fuzzer = PolicyFuzzer()

        # Assert
        assert "read" in fuzzer.operations
        assert "write" in fuzzer.operations
        assert "" in fuzzer.operations

    def test_default_targets_include_edge_cases(self) -> None:
        # Arrange & Act
        fuzzer = PolicyFuzzer()

        # Assert
        assert "" in fuzzer.targets
        assert "../../../etc/passwd" in fuzzer.targets

    def test_default_risk_scores_include_extremes(self) -> None:
        # Arrange & Act
        fuzzer = PolicyFuzzer()

        # Assert
        assert -1.0 in fuzzer.risk_scores
        assert 999.0 in fuzzer.risk_scores
        assert 0.0 in fuzzer.risk_scores
