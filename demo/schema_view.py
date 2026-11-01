from __future__ import annotations

from typing import Any

from pydantic import BaseModel

_CHILD_KEYS = ("schema", "items_schema", "values_schema")


def _func_name(node: dict[str, Any]) -> str:
    func = node.get("function")
    if isinstance(func, dict):
        func = func.get("function")
    if not func:
        return ""
    name = getattr(func, "__qualname__", getattr(func, "__name__", ""))
    return name.split("<locals>.")[-1]


def _label(node: dict[str, Any]) -> str:
    t = node.get("type", "?")
    extra = []
    name = _func_name(node)
    if name:
        extra.append(name)
    if t == "model":
        extra.append(node["cls"].__name__)
    for key in ("ge", "le", "min_length", "max_length"):
        if key in node:
            extra.append(f"{key}={node[key]}")
    return f"{t}" + (f"  ← {', '.join(extra)}" if extra else "")


def print_tree(node: dict[str, Any], depth: int = 0, only_field: str | None = None) -> None:
    pad = "│   " * depth
    print(f"{pad}{_label(node)}")
    t = node.get("type")
    if t == "definitions":
        print_tree(node["schema"], depth + 1, only_field)
        return
    if t == "model-fields":
        for name, field in node["fields"].items():
            if only_field and name != only_field:
                continue
            print(f"{pad}│   поле «{name}»")
            print_tree(field["schema"], depth + 2)
        return
    for key in _CHILD_KEYS:
        child = node.get(key)
        if isinstance(child, dict):
            print_tree(child, depth + 1, only_field)


def show_schema(model: type[BaseModel], only_field: str | None = None) -> None:
    print(f"CoreSchema модели {model.__name__} ({type(model.__pydantic_validator__).__name__} внутри):")
    print_tree(model.__pydantic_core_schema__, only_field=only_field)


def show_decorators(model: type[BaseModel]) -> None:
    infos = model.__pydantic_decorators__
    print(f"{type(infos).__name__} модели {model.__name__}:")
    for group in ("field_validators", "model_validators"):
        print(f"  {group}:")
        for name, dec in getattr(infos, group).items():
            fields = getattr(dec.info, "fields", None)
            target = f" поля {fields}" if fields else ""
            print(f"    {name:<26} mode={dec.info.mode:<7}{target}  ({type(dec.info).__name__})")
