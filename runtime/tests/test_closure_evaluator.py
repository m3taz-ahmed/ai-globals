#!/usr/bin/env python3
"""Tests for runtime.closure_evaluator."""

from __future__ import annotations

import pytest

from runtime.closure_evaluator import (
    ClosureEvaluator,
    ClosureResolutionError,
    GuardianClosureEvaluator,
)

# -- ClosureEvaluator: non-callable values ---------------------------------


def test_evaluate_non_callable_int_returns_as_is():
    evaluator = ClosureEvaluator()
    assert evaluator.evaluate(42) == 42


def test_evaluate_non_callable_string_returns_as_is():
    evaluator = ClosureEvaluator()
    assert evaluator.evaluate("hello") == "hello"


def test_evaluate_non_callable_list_returns_as_is():
    evaluator = ClosureEvaluator()
    assert evaluator.evaluate([1, 2, 3]) == [1, 2, 3]


def test_evaluate_class_type_returns_as_is():
    """Classes (types) should not be invoked."""
    evaluator = ClosureEvaluator()

    class Foo:
        pass

    assert evaluator.evaluate(Foo) is Foo


# -- ClosureEvaluator: callable with no params -----------------------------


def test_evaluate_callable_no_params():
    evaluator = ClosureEvaluator()
    assert evaluator.evaluate(lambda: 42) == 42


# -- ClosureEvaluator: named injections ------------------------------------


def test_evaluate_callable_with_named_injection():
    evaluator = ClosureEvaluator()
    result = evaluator.evaluate(lambda x: x * 2, named_injections={"x": 5})
    assert result == 10


def test_evaluate_callable_with_multiple_named_injections():
    evaluator = ClosureEvaluator()
    result = evaluator.evaluate(lambda a, b: a + b, named_injections={"a": 3, "b": 7})
    assert result == 10


# -- ClosureEvaluator: typed injections ------------------------------------


def test_evaluate_callable_with_typed_injection():
    evaluator = ClosureEvaluator()

    def closure(x: int) -> int:
        return x * 3

    # With from __future__ import annotations, annotations are strings.
    # Test with actual type object (no future annotations in runtime).
    result = evaluator.evaluate(closure, typed_injections={"int": 4})
    assert result == 12


def test_evaluate_callable_named_overrides_typed():
    """Named injection should take priority over typed injection."""
    evaluator = ClosureEvaluator()

    def closure(x: int) -> int:
        return x

    result = evaluator.evaluate(
        closure, named_injections={"x": 100}, typed_injections={"int": 200}
    )
    assert result == 100


# -- ClosureEvaluator: evaluation identifier -------------------------------


def test_evaluate_callable_with_evaluation_identifier():
    evaluator = ClosureEvaluator(evaluation_identifier="eval")

    def closure(eval: ClosureEvaluator) -> ClosureEvaluator:
        return eval

    result = evaluator.evaluate(closure)
    assert result is evaluator


# -- ClosureEvaluator: parameter defaults ----------------------------------


def test_evaluate_callable_with_param_default():
    evaluator = ClosureEvaluator()
    result = evaluator.evaluate(lambda x=99: x)
    assert result == 99


def test_evaluate_callable_named_overrides_default():
    evaluator = ClosureEvaluator()
    result = evaluator.evaluate(lambda x=99: x, named_injections={"x": 1})
    assert result == 1


# -- ClosureEvaluator: VAR_POSITIONAL / VAR_KEYWORD ------------------------


def test_evaluate_callable_var_positional_no_args():
    """VAR_POSITIONAL params receive no positional args."""
    evaluator = ClosureEvaluator()
    result = evaluator.evaluate(lambda *args: args)
    assert result == ()


def test_evaluate_callable_var_keyword_no_kwargs():
    """VAR_KEYWORD params receive no kwargs."""
    evaluator = ClosureEvaluator()
    result = evaluator.evaluate(lambda **kwargs: kwargs)
    assert result == {}


# -- ClosureEvaluator: resolution error ------------------------------------


def test_closure_resolution_error_raised():
    evaluator = ClosureEvaluator()
    with pytest.raises(ClosureResolutionError) as exc_info:
        evaluator.evaluate(lambda unknown_param: None)
    assert "unknown_param" in str(exc_info.value)


def test_closure_resolution_error_is_aizee_error():
    """ClosureResolutionError should inherit from AizeeError."""
    from runtime.schemas import AizeeError

    assert issubclass(ClosureResolutionError, AizeeError)


# -- GuardianClosureEvaluator ----------------------------------------------


def test_guardian_evaluator_action_default():
    evaluator = GuardianClosureEvaluator(action="Write")
    result = evaluator.evaluate(lambda action: action)
    assert result == "Write"


def test_guardian_evaluator_attributes_default():
    evaluator = GuardianClosureEvaluator(attributes={"path": "/tmp"})
    result = evaluator.evaluate(lambda attributes: attributes)
    assert result == {"path": "/tmp"}


def test_guardian_evaluator_context_default():
    evaluator = GuardianClosureEvaluator(context={"tenant": "acme"})
    result = evaluator.evaluate(lambda context: context)
    assert result == {"tenant": "acme"}


def test_guardian_evaluator_named_overrides_default():
    evaluator = GuardianClosureEvaluator(action="Default")
    result = evaluator.evaluate(lambda action: action, named_injections={"action": "Override"})
    assert result == "Override"


def test_guardian_evaluator_evaluation_identifier():
    """GuardianClosureEvaluator uses 'guardian' as evaluation identifier."""
    evaluator = GuardianClosureEvaluator()

    def closure(guardian: GuardianClosureEvaluator) -> GuardianClosureEvaluator:
        return guardian

    result = evaluator.evaluate(closure)
    assert result is evaluator


def test_guardian_evaluator_resolve_default_by_name_unknown_returns_none():
    evaluator = GuardianClosureEvaluator()
    assert evaluator.resolve_default_by_name("nonexistent") is None


def test_guardian_evaluator_resolve_default_by_type_returns_none():
    evaluator = GuardianClosureEvaluator()
    assert evaluator.resolve_default_by_type(str) is None
