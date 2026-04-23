from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


# Repository root used by the test suite to load source files directly.
REPO_ROOT = Path(__file__).resolve().parent.parent


def load_module(relative_path: str, module_name: str):
    """Load a module from a repo-relative path without requiring package setup.

    These tests are written as contract tests for an evolving codebase. Loading
    modules by path keeps the tests usable even when package structure changes
    during development.
    """
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module from {module_path}")

    # Several services import redis at module import time. The tests mock Redis
    # behavior explicitly, so a lightweight placeholder keeps imports working
    # even when the dependency is not installed in the current runner.
    if "redis" not in sys.modules:
        sys.modules["redis"] = types.SimpleNamespace(Redis=None)

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def require_attr(testcase, module, attr_name: str):
    """Assert that a module exposes a required contract symbol.

    Many of these tests define the intended future interface of each service.
    Using one helper keeps the failure message consistent and readable.
    """
    testcase.assertTrue(
        hasattr(module, attr_name),
        f"{module.__name__} should define `{attr_name}` as part of the service contract.",
    )
    return getattr(module, attr_name)
