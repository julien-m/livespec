# @spec(FR-013)
# .specs/features/078-requirement-evidence-integrity/spec.md#fr-013
"""SDK cleanup must retain active errors and cancellation without calling a model."""

import asyncio
from pathlib import Path

import pytest

from tests.integration.helpers import sdk_runner
from tests.test_sdk_runner_lifecycle import (
    ClaudeAgentOptions,
    ClosingIterator,
    ResultMessage,
    sdk_result,
)


class _FailingCloseIterator(ClosingIterator):
    """External iterator whose close fails independently from message collection."""

    def __init__(self, primary_error: BaseException | None = None, *, wait: bool = False) -> None:
        super().__init__([sdk_result("success", "end_turn")], wait_at_end=wait)
        self.primary_error = primary_error
        self.close_calls = 0
        self.cleanup_error: BaseException = OSError("transport close failed")

    async def __anext__(self) -> ResultMessage:
        if self.primary_error is not None:
            raise self.primary_error
        return await super().__anext__()

    async def aclose(self) -> None:
        self.close_calls += 1
        raise self.cleanup_error


@pytest.mark.parametrize(
    "primary_error", [RuntimeError("provider failed"), asyncio.CancelledError()]
)
def test_sdk_cleanup_retains_original_iteration_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, primary_error: BaseException
) -> None:
    stream = _FailingCloseIterator(primary_error)
    monkeypatch.setattr(sdk_runner, "query", lambda **kwargs: stream)
    result = sdk_runner.CommandResult(False, tmp_path)
    with pytest.raises(type(primary_error)) as caught:
        asyncio.run(sdk_runner._collect_messages("test", tmp_path, 1, result))
    assert caught.value is primary_error
    assert "transport close failed" in " ".join(caught.value.__notes__)
    assert stream.close_calls == 1


def test_sdk_cleanup_cannot_convert_external_cancellation_to_failed_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "fixture").mkdir()
    stream = _FailingCloseIterator(wait=True)
    monkeypatch.setattr(sdk_runner, "query", lambda **kwargs: stream)
    workspaces: list[Path] = []

    def transport(*, prompt: str, options: ClaudeAgentOptions) -> _FailingCloseIterator:
        assert options.cwd is not None
        workspaces.append(Path(options.cwd))
        return stream

    monkeypatch.setattr(sdk_runner, "query", transport)

    async def cancel() -> None:
        # The test owns the command task and awaits it after explicit cancellation.
        task = asyncio.create_task(sdk_runner.run_livespec_command("test", "fixture", tmp_path))
        async with asyncio.timeout(1):
            await stream.waiting.wait()
            task.cancel("caller cancelled")
            with pytest.raises(asyncio.CancelledError, match="caller cancelled") as caught:
                await task
            assert "transport close failed" in " ".join(caught.value.__notes__)

    asyncio.run(cancel())
    assert stream.close_calls == 1 and len(workspaces) == 1
    assert not workspaces[0].exists()


def test_sdk_cleanup_failure_after_successful_iteration_remains_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "fixture").mkdir()
    stream = _FailingCloseIterator()
    monkeypatch.setattr(sdk_runner, "query", lambda **kwargs: stream)
    with asyncio.run(sdk_runner.run_livespec_command("test", "fixture", tmp_path)) as result:
        assert not result.success and not result.timed_out
        assert result.error == "transport close failed"
        assert result.stdout_messages == ["observed"]
        assert stream.close_calls == 1 and result.cwd.is_dir()


def test_sdk_timeout_remains_timeout_when_transport_close_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "fixture").mkdir()
    stream = _FailingCloseIterator(wait=True)
    monkeypatch.setattr(sdk_runner, "query", lambda **kwargs: stream)
    with asyncio.run(
        sdk_runner.run_livespec_command("test", "fixture", tmp_path, timeout_sec=0.01)
    ) as result:
        assert result.timed_out and not result.success
        assert result.error == "generation_timeout"
        assert stream.close_calls == 1


@pytest.mark.parametrize("provider_error", [None, RuntimeError("provider failed")])
def test_sdk_new_cancellation_during_cleanup_always_propagates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, provider_error: BaseException | None
) -> None:
    stream = _FailingCloseIterator(provider_error)
    stream.cleanup_error = asyncio.CancelledError("cleanup cancelled")
    monkeypatch.setattr(sdk_runner, "query", lambda **kwargs: stream)
    with pytest.raises(asyncio.CancelledError, match="cleanup cancelled"):
        asyncio.run(
            sdk_runner._collect_messages(
                "test", tmp_path, 1, sdk_runner.CommandResult(False, tmp_path)
            )
        )
    assert stream.close_calls == 1
