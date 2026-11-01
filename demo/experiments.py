from __future__ import annotations

import sys
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Any

from pydantic import (
    AfterValidator,
    BaseModel,
    PlainValidator,
    ValidationError,
    ValidatorFunctionWrapHandler,
    field_validator,
    model_validator,
)

from .schema_view import show_schema


def header(title: str) -> None:
    print("\n" + "-" * 72 + f"\n{title}\n" + "-" * 72)


def add_commission(v: Decimal) -> Decimal:
    return v * Decimal("1.01")


def round_to_thousands(v: Decimal) -> Decimal:
    return (v / 1000).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * 1000


def exp_order() -> None:
    header("order: порядок after-валидаторов = порядок применения бизнес-правил")

    class CommissionThenRound(BaseModel):
        amount: Annotated[Decimal, AfterValidator(add_commission), AfterValidator(round_to_thousands)]

    class RoundThenCommission(BaseModel):
        amount: Annotated[Decimal, AfterValidator(round_to_thousands), AfterValidator(add_commission)]

    print("комиссия → округление:", CommissionThenRound(amount="149500").amount)
    print("округление → комиссия:", RoundThenCommission(amount="149500").amount)
    print("Причина: каждый AfterValidator оборачивает предыдущую схему, after-функции")
    print("выполняются «на выходе» из матрёшки — от внутренней к внешней, т.е. слева направо.")


def exp_mode() -> None:
    header("mode: before получает сырой ввод, after — уже приведённый тип")

    class Before(BaseModel):
        amount: Decimal

        @field_validator("amount", mode="before")
        @classmethod
        def show(cls, v: Any) -> Any:
            print(f"  before видит {v!r} ({type(v).__name__})")
            return v

    class After(BaseModel):
        amount: Decimal

        @field_validator("amount", mode="after")
        @classmethod
        def show(cls, v: Any) -> Any:
            print(f"  after  видит {v!r} ({type(v).__name__})")
            return v

    Before(amount="100.5")
    After(amount="100.5")
    try:
        Before(amount="сто")
    except ValidationError:
        print("  before вызвался даже для «сто» — он стоит ДО разбора Decimal")
    try:
        After(amount="сто")
    except ValidationError:
        print("  after для «сто» не вызвался: ядро упало на разборе Decimal раньше")


def exp_wrap_fallback() -> None:
    header("wrap_fallback: wrap может перехватить ошибку и вернуть значение по умолчанию")

    class Application(BaseModel):
        amount: Decimal

        @field_validator("amount", mode="wrap")
        @classmethod
        def fallback(cls, v: Any, handler: ValidatorFunctionWrapHandler) -> Decimal:
            try:
                return handler(v)
            except ValidationError:
                print(f"  handler упал на {v!r} → подставляю 0")
                return Decimal("0")

    print("  результат:", Application(amount="не число").amount)
    show_schema(Application, only_field="amount")


def exp_plain() -> None:
    header("plain: внутренняя схема (decimal) выбрасывается — ядро тип больше не проверяет")

    class Application(BaseModel):
        amount: Annotated[Decimal, PlainValidator(lambda v: f"как есть: {v}")]

    print("  результат:", repr(Application(amount=[1, 2, 3]).amount), "— даже список прошёл")
    show_schema(Application, only_field="amount")


def exp_inherit() -> None:
    header("inherit: DecoratorInfos.build() обходит MRO, валидатор с тем же именем заменяется")

    class Base(BaseModel):
        amount: Decimal

        @field_validator("amount")
        @classmethod
        def limit(cls, v: Decimal) -> Decimal:
            if v > 1000:
                raise ValueError("базовый лимит 1000")
            return v

    class Vip(Base):
        @field_validator("amount")
        @classmethod
        def limit(cls, v: Decimal) -> Decimal:
            if v > 1_000_000:
                raise ValueError("VIP-лимит 1 000 000")
            return v

    class VipExtra(Base):
        @field_validator("amount")
        @classmethod
        def vip_limit(cls, v: Decimal) -> Decimal:
            return v

    for model in (Base, Vip, VipExtra):
        try:
            model(amount=5000)
            print(f"  {model.__name__:<9} 5000 → ок;  валидаторы: {list(model.__pydantic_decorators__.field_validators)}")
        except ValidationError as e:
            print(f"  {model.__name__:<9} 5000 → {e.errors()[0]['msg']};  валидаторы: {list(model.__pydantic_decorators__.field_validators)}")


def exp_model_wrap() -> None:
    header("model_wrap: обёртка вокруг всей модели — видно сырой ввод и готовый объект")

    class Application(BaseModel):
        amount: Decimal

        @model_validator(mode="wrap")
        @classmethod
        def audit(cls, data: Any, handler: ValidatorFunctionWrapHandler) -> "Application":
            print(f"  до:    {data!r}")
            obj = handler(data)
            print(f"  после: {obj!r}")
            return obj

    Application(amount="42")
    show_schema(Application)


EXPERIMENTS = {
    "order": exp_order,
    "mode": exp_mode,
    "wrap_fallback": exp_wrap_fallback,
    "plain": exp_plain,
    "inherit": exp_inherit,
    "model_wrap": exp_model_wrap,
}


if __name__ == "__main__":
    for name in sys.argv[1:] or EXPERIMENTS:
        EXPERIMENTS[name]()
