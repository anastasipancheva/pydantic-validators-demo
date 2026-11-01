from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

ENABLED = True
_step = 0
_depth = 0


def reset() -> None:
    global _step, _depth
    _step = 0
    _depth = 0


def trace(who: str, what: str, value: Any = None) -> None:
    global _step
    if not ENABLED:
        return
    _step += 1
    pad = "    " * _depth
    shown = f" | вход: {value!r} ({type(value).__name__})" if value is not None else ""
    print(f"  {_step:>2}. {pad}[{who}] {what}{shown}")


@contextmanager
def nested() -> Iterator[None]:
    global _depth
    _depth += 1
    try:
        yield
    finally:
        _depth -= 1
