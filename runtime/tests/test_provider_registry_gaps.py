"""Gap coverage: runtime/provider_registry.py."""

from __future__ import annotations

import pytest

import runtime.provider_registry as pr
from runtime.provider_registry import (
    ProviderSpec,
    estimate_cost,
    get_all_providers,
    get_cheapest_provider,
    get_configured_providers,
    get_provider,
    get_providers_by_modality,
    list_provider_names,
)


class TestProviderSpec:
    def test_env_config(self) -> None:
        s = ProviderSpec(
            name="x", display_name="X", modalities=("language",),
            required_env=("REQ_A",), required_any_env=("ANY_B", "ANY_C"),
            optional_env=("OPT_D",),
        )
        cfg = s.env_config()
        assert cfg == {
            "required": ["REQ_A"],
            "required_any": ["ANY_B", "ANY_C"],
            "optional": ["OPT_D"],
        }
        empty = ProviderSpec(name="y", display_name="Y", modalities=())
        assert empty.env_config() == {}

    def test_is_configured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s = ProviderSpec(name="x", display_name="X", modalities=(),
                         required_env=("MISSING_VAR_XYZ",))
        monkeypatch.delenv("MISSING_VAR_XYZ", raising=False)
        assert not s.is_configured()
        monkeypatch.setenv("MISSING_VAR_XYZ", "v")
        assert s.is_configured()

    def test_is_configured_any(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s = ProviderSpec(name="x", display_name="X", modalities=(),
                         required_any_env=("ANY_X1", "ANY_X2"))
        monkeypatch.delenv("ANY_X1", raising=False)
        monkeypatch.delenv("ANY_X2", raising=False)
        assert not s.is_configured()
        monkeypatch.setenv("ANY_X2", "v")
        assert s.is_configured()

    def test_estimate_cost(self) -> None:
        s = ProviderSpec(name="x", display_name="X", modalities=(),
                         input_cost_per_1m=2.0, output_cost_per_1m=6.0)
        assert s.estimate_cost(1_000_000, 500_000) == pytest.approx(5.0)


class TestRegistry:
    def test_get_provider(self) -> None:
        all_p = get_all_providers()
        assert all_p, "registry should not be empty"
        first = next(iter(all_p))
        assert get_provider(first) is all_p[first]
        assert get_provider("nonexistent-provider") is None

    def test_configured_and_modality(self) -> None:
        configured = get_configured_providers()
        assert all(s.is_configured() for s in configured)
        lang = get_providers_by_modality("language")
        assert lang and all("language" in s.modalities for s in lang)
        assert get_providers_by_modality("nonexistent-mod") == []

    def test_cheapest(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cheap = ProviderSpec(name="c", display_name="C", modalities=("language",),
                             input_cost_per_1m=0.1, output_cost_per_1m=0.1)
        pricey = ProviderSpec(name="p", display_name="P", modalities=("language",),
                              input_cost_per_1m=9.0, output_cost_per_1m=9.0)
        monkeypatch.setattr(pr, "get_configured_providers", lambda: [cheap, pricey])
        assert get_cheapest_provider("language").name == "c"  # type: ignore[union-attr]
        assert get_cheapest_provider("no-modality") is None

    def test_cheapest_none_configured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(pr, "get_configured_providers", lambda: [])
        assert get_cheapest_provider() is None

    def test_estimate_cost_and_names(self) -> None:
        assert estimate_cost("nonexistent-provider", 10, 10) == 0.0
        names = list_provider_names()
        assert names == list(get_all_providers().keys())
