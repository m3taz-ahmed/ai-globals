"""Tests for runtime/memory_compression.py — three-zone compression."""

from __future__ import annotations

from runtime.memory_compression import MemoryCompressor


class TestMemoryCompressor:
    def test_partition_small_list(self) -> None:
        compressor = MemoryCompressor()
        msgs = [{"role": "user", "content": "hi"}]
        result = compressor.partition(msgs)
        assert len(result.frozen) == 1
        assert len(result.compress) == 0

    def test_partition_large_list(self) -> None:
        compressor = MemoryCompressor(frozen_zone_size=2, active_zone_rounds=3)
        msgs = [{"role": "user", "content": f"msg {i}"} for i in range(20)]
        result = compressor.partition(msgs)
        assert len(result.frozen) == 2
        assert len(result.active) == 6  # 3 rounds * 2 messages
        assert len(result.compress) > 0

    def test_should_compress_async(self) -> None:
        compressor = MemoryCompressor(max_tokens=1000)
        assert compressor.should_compress_async(600) is True
        assert compressor.should_compress_async(500) is False

    def test_should_compress_sync(self) -> None:
        compressor = MemoryCompressor(max_tokens=1000)
        assert compressor.should_compress_sync(800) is True
        assert compressor.should_compress_sync(700) is False

    def test_estimate_tokens(self) -> None:
        compressor = MemoryCompressor()
        msgs = [{"role": "user", "content": "x" * 400}]
        assert compressor.estimate_tokens(msgs) == 100

    def test_compress_messages_with_summary(self) -> None:
        compressor = MemoryCompressor(frozen_zone_size=2, active_zone_rounds=2)
        msgs = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
        result = compressor.compress_messages(msgs, summary="Previous conversation summarized")
        # Should have frozen + summary + active
        assert len(result) < len(msgs)
        assert any("[Summary]" in str(m.get("content", "")) for m in result)
