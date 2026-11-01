# Цепочка валидаторов в Pydantic v2

**Автор:** Панчева Анастасия

**Исследуемая библиотека:** [Pydantic](https://github.com/pydantic/pydantic), версия **2.13.5**

- Тег: [`v2.13.5`](https://github.com/pydantic/pydantic/tree/v2.13.5)
- Коммит: `001dea020e0809844e5b17666432c9135a976f46`
- Ядро `pydantic-core` **2.46.5** (Rust) лежит в том же репозитории, в папке [`pydantic-core/`](https://github.com/pydantic/pydantic/tree/v2.13.5/pydantic-core)

**Исследуемый механизм:** цепочка пользовательских валидаторов.

- Декораторы `@field_validator` / `@model_validator` и аннотации `BeforeValidator`, `AfterValidator`, `WrapValidator`, `PlainValidator`.
- Как Pydantic собирает их при создании класса.
- Как вкладывает их друг в друга в `CoreSchema`.
- Как ядро на Rust обходит получившуюся «матрёшку» при валидации.

## Запуск

Нужен Python 3.9+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python -m demo.main          # основная демонстрация (6 шагов)
python -m demo.experiments   # эксперименты с перестройкой цепочки
python -m pytest -q          # тесты, фиксирующие порядок вызовов
```

Отдельные шаги запускаются так: `python -m demo.main ok` (также `error`, `rule`, `context`, `schema`, `decorators`). С экспериментами то же самое: `python -m demo.experiments order` (также `mode`, `wrap_fallback`, `plain`, `inherit`, `model_wrap`).

## Отладка с брейкпоинтами

- **VS Code:** в `.vscode/launch.json` готовые конфигурации. В них стоит `justMyCode: false`, поэтому дебаггер заходит внутрь кода Pydantic.
- **PyCharm:** создайте Run Configuration с типом *Module* `demo.main` и аргументом `ok`.

Ядро написано на Rust, и Python-дебаггер в него не заходит. Зато его видно по стеку вызовов, когда срабатывает брейкпоинт внутри нашего валидатора: ядро вызывает наши функции обратно.

Ключевые места для брейкпоинтов (номера строк для версии 2.13.5):

| Фаза | Файл | Строка | Что происходит |
|---|---|---|---|
| Создание класса | `pydantic/_internal/_model_construction.py` | 176 | `DecoratorInfos.build(cls)` собирает декораторы |
| Создание класса | `pydantic/_internal/_model_construction.py` | 688–690 | готовая схема сохраняется, создаётся `SchemaValidator` |
| Сборка схемы поля | `pydantic/_internal/_generate_schema.py` | 1289 | декораторы превращаются в `Before/After/WrapValidator` |
| Сборка схемы поля | `pydantic/_internal/_generate_schema.py` | 2252 | цепочка обработчиков разворачивается в схему |
| Сборка схемы модели | `pydantic/_internal/_generate_schema.py` | 892 | `apply_model_validators(..., 'outer')` |
| Валидация | `pydantic/main.py` | 732 | `__pydantic_validator__.validate_python(...)` — переход в Rust |
| Валидация | `demo/models.py` | `log_amount`, строка с `handler(value)` | управление уходит вглубь цепочки |

## Структура

```
demo/
  models.py        модель LoanApplication и её валидаторы
  main.py          сценарии демонстрации
  experiments.py   варианты перестройки цепочки (порядок, режимы, wrap, plain, наследование)
  schema_view.py   печать CoreSchema деревом и содержимого DecoratorInfos
  tracing.py       нумерованный лог вызовов
tests/test_chain.py  проверка порядка вызовов
```
