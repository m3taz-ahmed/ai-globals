"""Tests for runtime/budget_anomaly.py."""

from __future__ import annotations

import pytest

from runtime.budget_anomaly import BudgetAnomalyDetector


class TestBudgetAnomalyDetectorRecord:
    def test_record_stores_value_in_history(self) -> None:
        # Arrange
        detector = BudgetAnomalyDetector(baseline_window=10, threshold=2.0)

        # Act
        detector.record(50)

        # Assert
        assert len(detector._history) == 1

    def test_record_respects_baseline_window(self) -> None:
        # Arrange
        detector = BudgetAnomalyDetector(baseline_window=3, threshold=2.0)

        # Act
        for v in [10, 20, 30, 40, 50]:
            detector.record(v)

        # Assert — deque maxlen keeps only the last 3
        assert len(detector._history) == 3
        assert list(detector._history) == [30, 40, 50]


class TestBudgetAnomalyDetectorCheck:
    def test_check_with_empty_history_returns_no_anomaly(self) -> None:
        # Arrange
        detector = BudgetAnomalyDetector(baseline_window=10, threshold=3.0)

        # Act
        result = detector.check(100)

        # Assert
        assert result["is_anomaly"] is False
        assert result["z_score"] == 0.0

    def test_check_with_single_value_returns_no_anomaly(self) -> None:
        # Arrange
        detector = BudgetAnomalyDetector(baseline_window=10, threshold=3.0)
        detector.record(50)

        # Act
        result = detector.check(500)

        # Assert — need at least 2 values for stats
        assert result["is_anomaly"] is False

    def test_check_normal_value_within_threshold(self) -> None:
        # Arrange
        detector = BudgetAnomalyDetector(baseline_window=10, threshold=3.0)
        for v in [50, 55, 48, 52, 51, 49, 53, 50, 54, 51]:
            detector.record(v)

        # Act
        result = detector.check(52)

        # Assert
        assert result["is_anomaly"] is False
        assert result["z_score"] < 3.0

    def test_check_spike_detected_as_anomaly(self) -> None:
        # Arrange
        detector = BudgetAnomalyDetector(baseline_window=10, threshold=2.0)
        for v in [50, 55, 48, 52, 51, 49, 53, 50, 54, 51]:
            detector.record(v)

        # Act
        result = detector.check(500)

        # Assert
        assert result["is_anomaly"] is True
        assert result["z_score"] > 2.0

    def test_check_returns_mean_and_std_dev(self) -> None:
        # Arrange
        detector = BudgetAnomalyDetector(baseline_window=10, threshold=3.0)
        for v in [50, 60]:
            detector.record(v)

        # Act
        result = detector.check(55)

        # Assert
        assert result["mean"] == pytest.approx(55.0)
        assert result["std_dev"] == pytest.approx(5.0)

    def test_check_zero_std_dev_with_different_value_is_anomaly(self) -> None:
        # Arrange — all same values → std_dev = 0
        detector = BudgetAnomalyDetector(baseline_window=10, threshold=3.0)
        for _ in range(5):
            detector.record(50)

        # Act
        result = detector.check(100)

        # Assert — when std is 0, any different value is anomalous
        assert result["is_anomaly"] is True
        assert result["std_dev"] == 0.0

    def test_check_zero_std_dev_with_same_value_is_not_anomaly(self) -> None:
        # Arrange
        detector = BudgetAnomalyDetector(baseline_window=10, threshold=3.0)
        for _ in range(5):
            detector.record(50)

        # Act
        result = detector.check(50)

        # Assert
        assert result["is_anomaly"] is False


class TestBudgetAnomalyDetectorIsAnomaly:
    def test_is_anomaly_returns_bool(self) -> None:
        # Arrange
        detector = BudgetAnomalyDetector(baseline_window=10, threshold=2.0)
        for v in [50, 55, 48, 52, 51]:
            detector.record(v)

        # Act
        result = detector.is_anomaly(500)

        # Assert
        assert isinstance(result, bool)
        assert result is True

    def test_is_anomaly_normal_value_returns_false(self) -> None:
        # Arrange
        detector = BudgetAnomalyDetector(baseline_window=10, threshold=2.0)
        for v in [50, 55, 48, 52, 51]:
            detector.record(v)

        # Act
        result = detector.is_anomaly(51)

        # Assert
        assert result is False


class TestBudgetAnomalyDetectorThreshold:
    def test_higher_threshold_requires_larger_deviation(self) -> None:
        # Arrange
        detector_low = BudgetAnomalyDetector(baseline_window=10, threshold=1.0)
        detector_high = BudgetAnomalyDetector(baseline_window=10, threshold=5.0)
        for v in [50, 55, 48, 52, 51, 49, 53, 50, 54, 51]:
            detector_low.record(v)
            detector_high.record(v)

        # Act — 55 is slightly above mean (~51.3) with std ~2.16 → z ≈ 1.7
        moderate_spike = 55
        result_low = detector_low.check(moderate_spike)
        result_high = detector_high.check(moderate_spike)

        # Assert
        assert result_low["is_anomaly"] is True
        assert result_high["is_anomaly"] is False
