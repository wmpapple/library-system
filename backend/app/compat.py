"""Runtime compatibility helpers for newer Python releases."""
from __future__ import annotations

import inspect
import sys
from typing import ForwardRef

_PATCH_ATTR = "_forward_ref_py312_patch"


def patch_forward_ref_for_py312() -> None:
    """Allow pydantic v1 to run on Python 3.12+ by patching ForwardRef._evaluate."""
    if getattr(ForwardRef, _PATCH_ATTR, False):  # already patched
        return

    if sys.version_info < (3, 12):
        return

    try:
        import pydantic  # type: ignore
    except Exception:  # pragma: no cover - defensive, import failure handled by env
        return

    if not pydantic.VERSION.startswith("1."):  # FastAPI with Pydantic v2 works without patch
        return

    signature = inspect.signature(ForwardRef._evaluate)
    recursive_guard = signature.parameters.get("recursive_guard")
    needs_patch = recursive_guard and recursive_guard.kind is inspect.Parameter.KEYWORD_ONLY

    if not needs_patch:
        return

    original = ForwardRef._evaluate

    def _patched(self, globalns, localns, *args, **kwargs):  # type: ignore[override]
        type_params = kwargs.pop("type_params", None)
        recursive_guard = kwargs.pop("recursive_guard", None)

        if args:
            if len(args) == 1:
                recursive_guard = args[0]
            elif len(args) == 2:
                type_params, recursive_guard = args
            else:  # pragma: no cover - defensive, mirrors CPython error
                raise TypeError("ForwardRef._evaluate() received unexpected positional arguments")

        if recursive_guard is None:
            recursive_guard = set()

        return original(self, globalns, localns, type_params, recursive_guard=recursive_guard)

    ForwardRef._evaluate = _patched  # type: ignore[assignment]
    setattr(ForwardRef, _PATCH_ATTR, True)
