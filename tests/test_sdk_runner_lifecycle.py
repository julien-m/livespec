"""Real SDK message contracts with a controlled external transport, without model calls."""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from tests.integration.helpers import sdk_runner

try:
    from claude_agent_sdk import ClaudeAgentOptions, ResultMessage
except ImportError:
    pytest.skip("Requires installed Claude Agent SDK boundary types", allow_module_level=True)


def sdk_result(subtype: str, stop_reason: str | None, *, is_error: bool = False) -> ResultMessage:
    """Build the installed SDK's actual boundary type."""
    return ResultMessage(
        subtype=subtype,
        duration_ms=1,
        duration_api_ms=1,
        is_error=is_error,
        num_turns=1,
        session_id="controlled-session",
        stop_reason=stop_reason,
        result="observed",
    )


class ClosingIterator(AsyncIterator[ResultMessage]):
    """A closeable async iterator deliberately lacking AsyncGenerator's asend/athrow API."""

    def __init__(self, messages: list[ResultMessage], *, wait_at_end: bool = False) -> None:
        self.messages = iter(messages)
        self.wait_at_end = wait_at_end
        self.closed = False
        self.waiting = asyncio.Event()

    async def __anext__(self) -> ResultMessage:
        message = next(self.messages, None)
        if message is not None:
            return message
        if self.wait_at_end:
            self.waiting.set()
            await asyncio.Event().wait()
        raise StopAsyncIteration

    async def aclose(self) -> None:
        await asyncio.sleep(0)
        self.closed = True


@pytest.mark.parametrize(
    ("subtype", "stop", "is_error", "expected"),
    [
        ("success", "end_turn", False, True),
        ("success", None, False, True),
        ("success", "stop_sequence", False, True),
        ("error_max_turns", "end_turn", False, False),
        ("error_during_execution", None, False, False),
        ("success", "tool_use", False, False),
        ("success", "max_tokens", False, False),
        ("success", "refusal", False, False),
        ("success", "future_deferred_response", False, False),
        ("success", "end_turn", True, False),
    ],
)
def test_sdk_result_requires_successful_terminal_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    subtype: str,
    stop: str | None,
    is_error: bool,
    expected: bool,
) -> None:
    (tmp_path / "fixture").mkdir()
    stream = ClosingIterator([sdk_result(subtype, stop, is_error=is_error)])
    monkeypatch.setattr(sdk_runner, "query", lambda **kwargs: stream)
    result = asyncio.run(sdk_runner.run_livespec_command("test", "fixture", tmp_path))
    with result:
        assert result.success is expected
        assert bool(result.error) is not expected
        assert result.stdout_messages == ["observed"]


def test_sdk_non_generator_iterator_is_closed_after_normal_completion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stream = ClosingIterator([sdk_result("success", "end_turn")])
    monkeypatch.setattr(sdk_runner, "query", lambda **kwargs: stream)
    result = sdk_runner.CommandResult(False, tmp_path)
    asyncio.run(sdk_runner._collect_messages("test", tmp_path, 1, result))
    assert result.success and stream.closed


def test_sdk_timeout_after_result_closes_iterator_and_cannot_report_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "fixture").mkdir()
    stream = ClosingIterator([sdk_result("success", "end_turn")], wait_at_end=True)
    monkeypatch.setattr(sdk_runner, "query", lambda **kwargs: stream)
    result = asyncio.run(
        sdk_runner.run_livespec_command("test", "fixture", tmp_path, timeout_sec=0.01)
    )
    with result:
        assert result.timed_out and not result.success
        assert result.error == "generation_timeout" and stream.closed


def test_sdk_external_cancellation_propagates_after_closing_iterator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stream = ClosingIterator([], wait_at_end=True)
    monkeypatch.setattr(sdk_runner, "query", lambda **kwargs: stream)

    async def cancel() -> None:
        result = sdk_runner.CommandResult(False, tmp_path)
        # This test owns and awaits the task after explicitly cancelling it.
        task = asyncio.create_task(sdk_runner._collect_messages("test", tmp_path, 1, result))
        await stream.waiting.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert stream.closed

    asyncio.run(cancel())


def test_sdk_cancelled_command_releases_its_unreturned_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "fixture").mkdir()
    stream = ClosingIterator([], wait_at_end=True)
    workspaces: list[Path] = []

    def transport(*, prompt: str, options: ClaudeAgentOptions) -> ClosingIterator:
        assert options.cwd is not None
        workspaces.append(Path(options.cwd))
        return stream

    monkeypatch.setattr(sdk_runner, "query", transport)

    async def cancel() -> None:
        # This caller owns and awaits cancellation of the command task.
        task = asyncio.create_task(sdk_runner.run_livespec_command("test", "fixture", tmp_path))
        await stream.waiting.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancel())
    assert stream.closed and len(workspaces) == 1
    assert not workspaces[0].exists()
