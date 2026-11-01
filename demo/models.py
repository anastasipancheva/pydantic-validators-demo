from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Any

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    Field,
    ValidationError,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    field_validator,
    model_validator,
)

from .tracing import nested, trace

DEFAULT_MAX_AMOUNT = Decimal("5000000")


def strip_spaces(value: Any) -> Any:
    trace("Annotated · before", "strip_spaces", value)
    if isinstance(value, str):
        value = value.replace(" ", "").replace(" ", "").replace(",", ".")
    return value


def must_be_positive(value: Decimal) -> Decimal:
    trace("Annotated · after", "must_be_positive", value)
    if value <= 0:
        raise ValueError("Сумма должна быть больше нуля")
    return value


Amount = Annotated[Decimal, BeforeValidator(strip_spaces), AfterValidator(must_be_positive)]


class LoanApplication(BaseModel):

    client_name: str = Field(min_length=2)
    email: str
    amount: Amount
    term_months: int = Field(ge=3, le=360)

    @model_validator(mode="before")
    @classmethod
    def map_form_keys(cls, data: Any) -> Any:
        trace("model · before", "map_form_keys", data)
        mapping = {"фио": "client_name", "почта": "email", "сумма": "amount", "срок": "term_months"}
        if isinstance(data, dict):
            data = {mapping.get(k, k): v for k, v in data.items()}
        return data

    @field_validator("amount", mode="before")
    @classmethod
    def remove_currency(cls, value: Any) -> Any:
        trace("field · before", "remove_currency", value)
        if isinstance(value, str):
            value = value.replace("₽", "").replace("руб.", "").strip()
        return value

    @field_validator("amount", mode="after")
    @classmethod
    def check_limit(cls, value: Decimal, info: ValidationInfo) -> Decimal:
        limit = Decimal(str((info.context or {}).get("max_amount", DEFAULT_MAX_AMOUNT)))
        trace("field · after", f"check_limit (лимит {limit})", value)
        if value > limit:
            raise ValueError(f"Сумма превышает лимит {limit}")
        return value

    @field_validator("amount", mode="wrap")
    @classmethod
    def log_amount(cls, value: Any, handler: ValidatorFunctionWrapHandler) -> Decimal:
        trace("field · wrap", "log_amount → вызываю handler()", value)
        with nested():
            try:
                result = handler(value)
            except ValidationError as exc:
                trace("field · wrap", f"log_amount поймал ошибку: {exc.errors()[0]['msg']}")
                raise
        trace("field · wrap", "log_amount ← handler вернул", result)
        return result

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        trace("field · after", "normalize_email", value)
        if "@" not in value:
            raise ValueError("Некорректный e-mail")
        return value.lower()

    @model_validator(mode="after")
    def check_term_for_big_loans(self) -> "LoanApplication":
        trace("model · after", "check_term_for_big_loans", f"amount={self.amount}, term={self.term_months}")
        if self.amount > Decimal("1000000") and self.term_months < 12:
            raise ValueError("Кредит больше 1 млн оформляется на срок от 12 месяцев")
        return self


VALID_FORM = {
    "фио": "Иванова Мария",
    "почта": "Maria.Ivanova@Example.RU",
    "сумма": "1 500 000,50 ₽",
    "срок": "24",
}

INVALID_FORM = {
    "фио": "Иванова Мария",
    "почта": "maria@example.ru",
    "сумма": "-100 ₽",
    "срок": 24,
}

BUSINESS_RULE_FORM = {
    "фио": "Петров Пётр",
    "почта": "petr@example.ru",
    "сумма": "2 000 000",
    "срок": 6,
}
