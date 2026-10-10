"""Runner-loaded pytest plugin recording actual passing assertion execution."""

from __future__ import annotations

import ast
import json
import os
import sys
from pathlib import Path
from types import FrameType
from typing import NamedTuple, Protocol

from _pytest.assertion.rewrite import _call_assertion_pass
from pytest import Config, Session, StashKey


class CaptureContext(NamedTuple):
    """Runner configuration frozen before tests can change their process environment."""

    root: Path
    trace: Path
    invocation: str
    feature: str


class TestItem(Protocol):
    """The stable pytest item fields needed to identify an assertion callback."""

    nodeid: str
    path: Path
    config: Config


# Pytest owns one plugin instance per child process. This transport buffer is
# invocation-local; it is never a parent-side substitute for a real callback.
_assertions: list[dict[str, str | int]] = []
_ASSERTION_DISPATCH_CODE = _call_assertion_pass.__code__
_CAPTURE_CONTEXT = StashKey[CaptureContext]()


def pytest_configure(config: Config) -> None:
    """Resolve runner-owned identity once at session setup, never during test callbacks."""
    config.stash[_CAPTURE_CONTEXT] = CaptureContext(
        root=Path(os.environ["LIVESPEC_EXECUTION_PROJECT"]),
        trace=Path(os.environ["LIVESPEC_ASSERTION_TRACE"]),
        invocation=os.environ["LIVESPEC_EXECUTION_NONCE"],
        feature=os.environ["LIVESPEC_EXECUTION_FEATURE"],
    )
    _assertions.clear()


def pytest_assertion_pass(item: TestItem, lineno: int, orig: str, expl: str) -> None:
    """Record only assertions for which pytest actually emitted a passing hook."""
    del expl  # Expanded values can contain user data; exact source text is sufficient.
    path = _assertion_origin(lineno, item.config.stash[_CAPTURE_CONTEXT].root)
    if path is not None:
        _assertions.append(
            {
                "test_id": item.nodeid,
                "path": str(path),
                "line": lineno,
                "assertion": orig,
                "status": "passed",
            }
        )


def _assertion_origin(lineno: int, root: Path) -> Path | None:
    # Keep the installed dispatcher's code identity captured before test imports.
    # Its immediate caller is the rewritten assertion, including helper assertions.
    frame: FrameType | None = sys._getframe(1)
    try:
        while frame is not None and frame.f_code is not _ASSERTION_DISPATCH_CODE:
            frame = frame.f_back
        origin = frame.f_back if frame is not None else None
        if origin is not None and origin.f_lineno == lineno:
            path = Path(origin.f_code.co_filename).resolve()
            if path.is_relative_to(root) and path.is_file():
                return path
        return None
    finally:
        del frame


class TracebackEntry(Protocol):
    """Actual pytest traceback entry exposed by CallInfo.excinfo."""

    path: Path
    lineno: int


class ExceptionInfo(Protocol):
    """Failure fields from pytest's actual captured call exception."""

    value: BaseException
    traceback: list[TracebackEntry]


class CallInfo(Protocol):
    """Only a real test call with AssertionError can establish RED evidence."""

    when: str
    excinfo: ExceptionInfo | None


def pytest_runtest_makereport(item: TestItem, call: CallInfo) -> None:
    """Capture a failing assertion traceback, never a mere failed process exit."""
    if (
        call.when != "call"
        or call.excinfo is None
        or not isinstance(call.excinfo.value, AssertionError)
    ):
        return
    entry = call.excinfo.traceback[-1]
    path = Path(str(entry.path))
    source = path.read_text()
    nodes = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Assert) and node.lineno == entry.lineno + 1
    ]
    if len(nodes) != 1:
        return  # Explicit raises and ambiguous same-line assertions are not observable assertions.
    expression = ast.get_source_segment(source, nodes[0].test)
    if expression:
        _assertions.append(
            {
                "test_id": item.nodeid,
                "path": str(path),
                "line": entry.lineno + 1,
                "assertion": expression,
                "status": "failed",
            }
        )


def pytest_sessionfinish(session: Session) -> None:
    """Publish the actual callback stream once, rejecting a precreated forged trace."""
    context = session.config.stash[_CAPTURE_CONTEXT]
    descriptor = os.open(context.trace, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    payload = {
        "schema_version": "1",
        "invocation": context.invocation,
        "project_root": str(context.root),
        "feature": context.feature,
        "assertions": _assertions,
    }
    with os.fdopen(descriptor, "w") as stream:
        json.dump(payload, stream)
        stream.flush()
        os.fsync(stream.fileno())
