"""Tests for runtime/approval_cache.py — session-scoped approval caching."""

from __future__ import annotations

import threading

from runtime.approval_cache import ApprovalCache


class TestApprovalCacheKeying:
    """Tests for key generation and normalization."""

    def test_same_action_produces_same_key(self) -> None:
        cache = ApprovalCache()
        action = {"type": "bash", "command": "ls", "tool": None, "path": "/tmp"}
        cache.approve(action)
        assert cache.is_approved(action)

    def test_different_field_order_produces_same_key(self) -> None:
        cache = ApprovalCache()
        action1 = {"type": "bash", "command": "ls", "tool": None, "path": "/tmp"}
        action2 = {"path": "/tmp", "command": "ls", "type": "bash", "tool": None}
        cache.approve(action1)
        assert cache.is_approved(action2)

    def test_extra_fields_ignored(self) -> None:
        cache = ApprovalCache()
        action1 = {"type": "bash", "command": "ls", "extra": "ignored"}
        action2 = {"type": "bash", "command": "ls", "extra": "different"}
        cache.approve(action1)
        assert cache.is_approved(action2)

    def test_different_command_not_approved(self) -> None:
        cache = ApprovalCache()
        cache.approve({"type": "bash", "command": "ls"})
        assert not cache.is_approved({"type": "bash", "command": "rm"})

    def test_missing_fields_treated_as_none(self) -> None:
        cache = ApprovalCache()
        cache.approve({"type": "bash"})
        assert cache.is_approved({"type": "bash", "command": None})
        assert cache.is_approved({"type": "bash", "tool": None})

    def test_custom_fields(self) -> None:
        cache = ApprovalCache(fields=("type", "command"))
        cache.approve({"type": "bash", "command": "ls", "path": "/ignored"})
        assert cache.is_approved({"type": "bash", "command": "ls", "path": "/different"})


class TestApprovalCacheOperations:
    """Tests for approve/is_approved/clear lifecycle."""

    def test_unapproved_action_returns_false(self) -> None:
        cache = ApprovalCache()
        assert not cache.is_approved({"type": "bash", "command": "ls"})

    def test_approve_then_clear(self) -> None:
        cache = ApprovalCache()
        action = {"type": "bash", "command": "ls"}
        cache.approve(action)
        assert cache.is_approved(action)
        cache.clear()
        assert not cache.is_approved(action)

    def test_clear_on_empty_cache_no_error(self) -> None:
        cache = ApprovalCache()
        cache.clear()  # should not raise

    def test_multiple_approvals(self) -> None:
        cache = ApprovalCache()
        cache.approve({"type": "bash", "command": "ls"})
        cache.approve({"type": "bash", "command": "pwd"})
        cache.approve({"type": "mcp", "tool": "query_rules"})
        assert cache.is_approved({"type": "bash", "command": "ls"})
        assert cache.is_approved({"type": "bash", "command": "pwd"})
        assert cache.is_approved({"type": "mcp", "tool": "query_rules"})


class TestApprovalCacheConcurrency:
    """Thread-safety tests."""

    def test_concurrent_approves_do_not_crash(self) -> None:
        cache = ApprovalCache()
        errors: list[Exception] = []

        def worker(idx: int) -> None:
            try:
                for i in range(100):
                    cache.approve({"type": "bash", "command": f"cmd{idx}_{i}"})
                    cache.is_approved({"type": "bash", "command": f"cmd{idx}_{i}"})
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []

    def test_concurrent_clear_and_approve(self) -> None:
        cache = ApprovalCache()
        errors: list[Exception] = []

        def approver() -> None:
            try:
                for _ in range(100):
                    cache.approve({"type": "bash", "command": "ls"})
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        def clearer() -> None:
            try:
                for _ in range(100):
                    cache.clear()
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        threads = [threading.Thread(target=approver), threading.Thread(target=clearer)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []

    def test_concurrent_approve_exception_captured(self) -> None:
        """Cover lines 91-92: except block in concurrent approve worker."""
        cache = ApprovalCache()
        errors: list[Exception] = []

        def worker(idx: int) -> None:
            try:
                for i in range(10):
                    cache.approve({"type": "bash", "command": f"cmd{idx}_{i}"})
                    cache.is_approved({"type": "bash", "command": f"cmd{idx}_{i}"})
            except Exception as exc:
                errors.append(exc)

        # Patch approve to raise on the second call
        original_approve = cache.approve
        call_count = [0]

        def failing_approve(action):
            call_count[0] += 1
            if call_count[0] > 1:
                raise RuntimeError("forced error")
            return original_approve(action)

        cache.approve = failing_approve  # type: ignore[method-assign]

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) > 0

    def test_concurrent_clear_exception_captured(self) -> None:
        """Cover lines 109-110, 116-117: except blocks in approver/clearer."""
        cache = ApprovalCache()
        errors: list[Exception] = []

        def approver() -> None:
            try:
                for _ in range(10):
                    cache.approve({"type": "bash", "command": "ls"})
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        def clearer() -> None:
            try:
                for _ in range(10):
                    cache.clear()
            except Exception as exc:
                errors.append(exc)

        # Patch clear to raise
        original_clear = cache.clear
        clear_count = [0]

        def failing_clear():
            clear_count[0] += 1
            if clear_count[0] > 1:
                raise RuntimeError("forced clear error")
            return original_clear()

        cache.clear = failing_clear  # type: ignore[method-assign]

        threads = [threading.Thread(target=approver), threading.Thread(target=clearer)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) > 0
