from decimal import Decimal
from typing import Annotated, Any

import pytest
from pydantic import AfterValidator, BaseModel, BeforeValidator, ValidationError, field_validator

from demo import tracing
from demo.models import BUSINESS_RULE_FORM, INVALID_FORM, VALID_FORM, LoanApplication


def test_valid_form_parsed():
    app = LoanApplication.model_validate(VALID_FORM)
    assert app.amount == Decimal("1500000.50")
    assert app.email == "maria.ivanova@example.ru"
    assert app.term_months == 24


def test_negative_amount_rejected_by_must_be_positive():
    with pytest.raises(ValidationError) as exc:
        LoanApplication.model_validate(INVALID_FORM)
    assert exc.value.errors()[0]["loc"] == ("amount",)
    assert "больше нуля" in exc.value.errors()[0]["msg"]


def test_business_rule_is_model_level():
    with pytest.raises(ValidationError) as exc:
        LoanApplication.model_validate(BUSINESS_RULE_FORM)
    assert exc.value.errors()[0]["loc"] == ()


def test_context_changes_limit():
    with pytest.raises(ValidationError):
        LoanApplication.model_validate(VALID_FORM, context={"max_amount": 1_000_000})


def test_call_order_of_amount_chain(capsys):
    tracing.reset()
    LoanApplication.model_validate(VALID_FORM)
    out = capsys.readouterr().out
    order = ["log_amount →", "remove_currency", "strip_spaces", "must_be_positive", "check_limit", "log_amount ←"]
    positions = [out.index(name) for name in order]
    assert positions == sorted(positions)


def test_before_runs_in_reverse_after_runs_in_order():
    calls: list[str] = []

    def mark(tag: str):
        def f(v: Any) -> Any:
            calls.append(tag)
            return v
        return f

    class M(BaseModel):
        x: Annotated[int, BeforeValidator(mark("b1")), BeforeValidator(mark("b2")),
                     AfterValidator(mark("a1")), AfterValidator(mark("a2"))]

        @field_validator("x", mode="before")
        @classmethod
        def b3(cls, v: Any) -> Any:
            calls.append("b3")
            return v

    M(x="1")
    assert calls == ["b3", "b2", "b1", "a1", "a2"]
