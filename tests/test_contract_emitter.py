"""Tests for runtime/contract_emitter.py — ContractArtifact + emit/validate."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from pydantic import BaseModel

from runtime.contract_emitter import (
    ContractArtifact,
    ContractEmitError,
    emit_contract,
    emit_contracts,
    validate_contract,
)


class _SampleModel(BaseModel):
    name: str
    age: int
    active: bool = True


@dataclass
class _SampleDataclass:
    title: str
    count: int


def test_emit_contract_from_pydantic() -> None:
    artifact = emit_contract(_SampleModel)
    assert artifact.name == "_SampleModel"
    assert "properties" in artifact.json_schema
    assert "name" in artifact.json_schema["properties"]


def test_emit_contract_typescript_stub() -> None:
    artifact = emit_contract(_SampleModel)
    ts = artifact.to_typescript()
    assert "export interface _SampleModel" in ts
    assert "name: string" in ts


def test_emit_contract_json_string() -> None:
    artifact = emit_contract(_SampleModel)
    json_str = artifact.to_json()
    assert '"_SampleModel"' in json_str


def test_emit_contract_from_dataclass() -> None:
    artifact = emit_contract(_SampleDataclass)
    assert artifact.name == "_SampleDataclass"
    assert "title" in artifact.json_schema["properties"]


def test_emit_contract_custom_name() -> None:
    artifact = emit_contract(_SampleModel, name="User")
    assert artifact.name == "User"
    assert "export interface User" in artifact.to_typescript()


def test_emit_contract_invalid_class_raises() -> None:
    class NotASchema:
        pass

    with pytest.raises(ContractEmitError):
        emit_contract(NotASchema)


def test_emit_contracts_multiple() -> None:
    artifacts = emit_contracts([_SampleModel, _SampleDataclass])
    assert len(artifacts) == 2
    assert "_SampleModel" in artifacts
    assert "_SampleDataclass" in artifacts


def test_emit_contracts_writes_to_disk() -> None:
    with TemporaryDirectory() as tmp:
        out = Path(tmp) / "contracts"
        emit_contracts([_SampleModel], output_dir=out)
        assert (out / "_SampleModel.json").exists()
        assert (out / "_SampleModel.d.ts").exists()


def test_validate_contract_valid_data() -> None:
    artifact = emit_contract(_SampleModel)
    errors = validate_contract(artifact, {"name": "Alice", "age": 30, "active": True})
    assert errors == []


def test_validate_contract_missing_field() -> None:
    artifact = emit_contract(_SampleModel)
    errors = validate_contract(artifact, {"name": "Alice"})
    assert any("missing" in e for e in errors)


def test_validate_contract_wrong_type() -> None:
    artifact = emit_contract(_SampleModel)
    errors = validate_contract(artifact, {"name": 123, "age": 30, "active": True})
    assert any("expected string" in e for e in errors)


def test_validate_contract_unknown_field() -> None:
    artifact = emit_contract(_SampleModel)
    errors = validate_contract(artifact, {"name": "A", "age": 1, "active": True, "extra": "x"})
    assert any("unknown field" in e for e in errors)


def test_contract_artifact_dataclass() -> None:
    a = ContractArtifact(name="Test", json_schema={"type": "object"}, typescript_stub="export interface Test {}")
    assert a.name == "Test"
    assert a.to_typescript() == "export interface Test {}"
