"""Gap tests for contract_emitter.py + experiment_tracker.py."""
from __future__ import annotations

import pytest

from runtime.contract_emitter import (
    ContractArtifact,
    ContractEmitError,
    emit_contract,
    emit_contracts,
    validate_contract,
)
from runtime.experiment_tracker import (
    _srm_p_value,
    _two_proportion_z,
    analyze_ab_test,
    analyze_ab_test_dict,
)
from runtime.schemas import ValidationError


class TestContractEmit:
    def test_pydantic_schema_error(self):
        class FakeModel:
            @classmethod
            def model_json_schema(cls):
                raise RuntimeError("schema boom")
        with pytest.raises(ContractEmitError):
            emit_contract(FakeModel)

    def test_dataclass_fallback(self):
        class DC:
            __annotations__ = {"name": str, "count": int, "weird": "Custom"}
        a = emit_contract(DC)
        assert "name: string" in a.typescript_stub
        assert "weird: any" in a.typescript_stub

    def test_neither_model_nor_dataclass(self):
        with pytest.raises(ContractEmitError):
            emit_contract(object)

    def test_ref_and_anyof_and_list_type(self):
        class M:
            @classmethod
            def model_json_schema(cls):
                return {
                    "required": ["a"],
                    "properties": {
                        "a": {"$ref": "#/$defs/Thing"},
                        "b": {"anyOf": [{"type": "string"}, {"type": "string"}, {"type": "null"}]},
                        "c": {"type": ["string", "null"]},
                        "d": {"type": "integer"},
                    },
                }
        a = emit_contract(M)
        assert "a: Thing" in a.typescript_stub
        assert "b?: string | null" in a.typescript_stub
        assert "c?: string | null" in a.typescript_stub

    def test_ref_empty_name(self):
        class M:
            @classmethod
            def model_json_schema(cls):
                return {"properties": {"x": {"$ref": ""}}}
        a = emit_contract(M)
        assert "x: any" in a.typescript_stub  # no required[] -> all required

    def test_emit_contracts_writes_files(self, tmp_path):
        class DC:
            __annotations__ = {"f": str}
        out = emit_contracts([DC], output_dir=tmp_path / "out")
        assert "DC" in out
        assert (tmp_path / "out" / "DC.json").exists()
        assert (tmp_path / "out" / "DC.d.ts").exists()

    def test_emit_contracts_bad_dir(self, tmp_path):
        # mkdir on a path under a *file* raises NotADirectoryError (OSError)
        blocker = tmp_path / "afile"
        blocker.write_text("x")
        class DC:
            __annotations__ = {"f": str}
        with pytest.raises(ContractEmitError):
            emit_contracts([DC], output_dir=blocker / "sub")

    def test_emit_contracts_generic_exc(self, tmp_path):
        class M:
            @classmethod
            def model_json_schema(cls):
                return {"properties": None}
        # properties=None -> .items() AttributeError inside emit -> wrapped by emit_contracts
        with pytest.raises(ContractEmitError):
            emit_contracts([M], output_dir=tmp_path)

    def test_write_outside_output_dir(self, tmp_path):
        from unittest.mock import patch
        a = ContractArtifact(name="../evil", json_schema={}, typescript_stub="")
        class M:
            __annotations__ = {"f": str}
        with patch("runtime.contract_emitter.emit_contract", return_value=a):
            with pytest.raises(ContractEmitError):
                emit_contracts([M], output_dir=tmp_path)

    def test_write_oserror(self, tmp_path):
        class M:
            __annotations__ = {"f": str}
        from pathlib import Path
        from unittest.mock import patch
        with patch.object(Path, "write_text", side_effect=OSError("disk")):
            with pytest.raises(ContractEmitError):
                emit_contracts([M], output_dir=tmp_path)


class TestValidateContract:
    def test_missing_required_and_unknown(self):
        a = ContractArtifact(name="C", json_schema={
            "properties": {"req": {"type": "string"}, "num": {"type": "number"}, "flag": {"type": "boolean"}},
            "required": ["req"],
        }, typescript_stub="")
        errs = validate_contract(a, {"num": "x", "flag": 1, "extra": 5})
        assert "missing required field: req" in errs
        assert "num: expected number" in errs[1] or any("expected number" in e for e in errs)
        assert any("expected boolean" in e for e in errs)
        assert "unknown field: extra" in errs

    def test_no_required_means_all_required(self):
        a = ContractArtifact(name="C", json_schema={"properties": {"a": {"type": "any"}}}, typescript_stub="")
        assert validate_contract(a, {}) == ["missing required field: a"]

    def test_required_not_list(self):
        a = ContractArtifact(name="C", json_schema={
            "properties": {"a": {}}, "required": "yes"},
            typescript_stub="")
        assert "missing required field: a" in validate_contract(a, {})


class TestExperimentTracker:
    def test_unpooled_se_fallback(self):
        # a_conv=0 -> pooled_se collapses -> unpooled path
        p_a, p_b, _z, _pv = _two_proportion_z(0, 100, 50, 100)
        assert p_a == 0.0 and p_b == 0.5

    def test_srm_zero_total_and_zero_expected(self):
        assert _srm_p_value(0, 0) == 1.0
        assert _srm_p_value(100, 0, expected_ratio=1.0) == 1.0

    def test_getitem_and_get(self):
        r = analyze_ab_test(50, 1000, 60, 1000)
        assert r["p_a"] == r.p_a
        assert r.get("winner") == r.winner
        assert r.get("nope", "d") == "d"

    def test_method_not_implemented(self):
        with pytest.raises(ValidationError):
            analyze_ab_test(1, 10, 1, 10, method="cuped")

    def test_bad_visitors_and_confidence(self):
        with pytest.raises(ValidationError):
            analyze_ab_test(1, 0, 1, 10)
        with pytest.raises(ValidationError):
            analyze_ab_test(1, 10, 1, 10, confidence=1.5)
        with pytest.raises(ValidationError):
            analyze_ab_test(1, 10, 1, 10, confidence=0.0)

    def test_negative_and_overflow_conv(self):
        with pytest.raises(ValidationError):
            analyze_ab_test(-1, 10, 1, 10)
        with pytest.raises(ValidationError):
            analyze_ab_test(20, 10, 1, 10)

    def test_winner_a_and_b(self):
        ra = analyze_ab_test(90, 100, 10, 100)  # A wins clearly
        assert ra.significant and ra.winner == "A"
        rb = analyze_ab_test(10, 100, 90, 100)
        assert rb.significant and rb.winner == "B"

    def test_not_significant_no_winner(self):
        r = analyze_ab_test(50, 1000, 51, 1000)
        assert r.winner is None

    def test_dict_alias(self):
        d = analyze_ab_test_dict(50, 1000, 60, 1000)
        assert "p_value" in d and d["method"] == "z_test"

    def test_srm_mismatch_flag(self):
        # extreme split (1000 vs 10 visitors) -> srm p tiny -> srm_ok False
        r = analyze_ab_test(500, 1000, 5, 10)
        assert r.srm_ok is False
