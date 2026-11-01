from __future__ import annotations

import sys

from pydantic import ValidationError

from . import tracing
from .models import BUSINESS_RULE_FORM, INVALID_FORM, VALID_FORM, LoanApplication
from .schema_view import show_decorators, show_schema


def header(title: str) -> None:
    print("\n" + "=" * 72 + f"\n{title}\n" + "=" * 72)


def validate(data: dict, context: dict | None = None) -> None:
    tracing.reset()
    print(f"Вход: {data}\n")
    try:
        app = LoanApplication.model_validate(data, context=context)
    except ValidationError as exc:
        print("\nValidationError:")
        for err in exc.errors():
            print(f"  loc={err['loc']}  type={err['type']}  msg={err['msg']}")
        return
    print(f"\nРезультат: {app!r}")


def step_ok() -> None:
    header("1. Корректная заявка: в каком порядке ядро вызывает валидаторы")
    validate(VALID_FORM)


def step_error() -> None:
    header("2. Отрицательная сумма: ошибка поднимается из must_be_positive через wrap")
    validate(INVALID_FORM)


def step_rule() -> None:
    header("3. Межполевое правило: 2 млн на 6 месяцев запрещено")
    validate(BUSINESS_RULE_FORM)


def step_context() -> None:
    header("4. Тот же ввод, но лимит 1 000 000 передан через context")
    validate(VALID_FORM, context={"max_amount": 1_000_000})


def step_schema() -> None:
    header("5. CoreSchema: валидаторы вложены друг в друга")
    show_schema(LoanApplication, only_field="amount")


def step_decorators() -> None:
    header("6. DecoratorInfos: что собрано из декораторов при создании класса")
    show_decorators(LoanApplication)


STEPS = {
    "ok": step_ok,
    "error": step_error,
    "rule": step_rule,
    "context": step_context,
    "schema": step_schema,
    "decorators": step_decorators,
}


def main(argv: list[str]) -> None:
    names = argv or list(STEPS)
    for name in names:
        if name not in STEPS:
            raise SystemExit(f"Неизвестный шаг {name!r}. Доступно: {', '.join(STEPS)}")
        STEPS[name]()


if __name__ == "__main__":
    main(sys.argv[1:])
