# @spec(FR-013)
# .specs/features/078-requirement-evidence-integrity/spec.md#fr-013
"""Claude Code SDK wrapper for running LiveSpec commands in tests."""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType

try:
    from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, query

    HAS_SDK = True
except ImportError:
    HAS_SDK = False


@dataclass
class CommandResult:
    """SDK outcome retaining the temporary workspace for independent evaluation.

    Results returned by run_livespec_command transfer workspace ownership to the
    caller, even on reported failure. Call close() after evaluating its files or
    use ``with result:``; context exit cleans up even when evaluation raises.
    close() is idempotent and removes only an owned temporary workspace, never
    an arbitrary cwd supplied to a manually constructed result.

    Attributes:
        success: Whether the SDK reported supported terminal success, not proof
            that the generated behavior satisfies its independent oracle.
        cwd: Workspace path, whose owned files cease to exist after close().
        stdout_messages: Collected final SDK result text.
        total_input_tokens: Observed input usage; absent usage contributes zero.
        total_output_tokens: Observed output usage; absent usage contributes zero.
        error: Failure diagnostic, or None when no failure has been recorded.
        timed_out: Whether SDK message collection exceeded its timeout.
    """

    success: bool
    cwd: Path
    stdout_messages: list[str] = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    error: str | None = None
    timed_out: bool = False
    _workspace: tempfile.TemporaryDirectory[str] | None = field(default=None, repr=False)

    def close(self) -> None:
        """Release the workspace only after caller-owned independent evaluation."""
        if self._workspace is not None:
            self._workspace.cleanup()
            self._workspace = None

    def __enter__(self) -> CommandResult:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    @property
    def estimated_cost_usd(self) -> float:
        # claude-opus-4-6: $5/1M input, $25/1M output
        return self.total_input_tokens * 5 / 1_000_000 + self.total_output_tokens * 25 / 1_000_000


async def run_livespec_command(
    command: str,
    fixture_name: str,
    fixtures_base: Path,
    timeout_sec: float = 120,
    max_turns: int = 40,
) -> CommandResult:
    """Run a Claude SDK command against a copied fixture.

    Args:
        command: Prompt or LiveSpec command passed to the SDK.
        fixture_name: Fixture directory relative to fixtures_base.
        fixtures_base: Directory containing the source fixtures.
        timeout_sec: Positive timeout in seconds for SDK message collection.
        max_turns: Maximum SDK turns allowed for this invocation.
    Returns:
        Result owning a live temporary workspace, including on reported failure.
        Evaluate its files before calling result.close() or exiting ``with result:``.
    Raises:
        ValueError: If timeout_sec is not positive.
        asyncio.CancelledError: External cancellation, after workspace cleanup.
        OSError: If temporary workspace creation or cancellation cleanup fails.
    Side effects:
        Copies fixture files and starts an SDK session able to execute tools in
        that workspace. SDK/copy failures and timeouts are returned as diagnostics.
    """
    if timeout_sec <= 0:
        raise ValueError("timeout_sec must be positive")
    workspace = tempfile.TemporaryDirectory(prefix="livespec_test_")
    cwd = Path(workspace.name)
    result = CommandResult(success=False, cwd=cwd, _workspace=workspace)
    try:
        shutil.copytree(fixtures_base / fixture_name, cwd, dirs_exist_ok=True)
        if not HAS_SDK:
            result.error = "claude_agent_sdk unavailable"
            return result
        async with asyncio.timeout(timeout_sec):
            await _collect_messages(command, cwd, max_turns, result)
    except TimeoutError:
        result.success = False
        result.timed_out = True
        result.error = "generation_timeout"
    except asyncio.CancelledError:
        result.close()
        raise
    except Exception as exc:
        result.success = False
        # SDK/provider failures are returned as explicit diagnostics, never behavioral success.
        result.error = str(exc)
    return result


async def _collect_messages(command: str, cwd: Path, max_turns: int, result: CommandResult) -> None:
    """Close the SDK transport on timeout/cancellation so its subprocess is reaped."""
    messages = query(
        prompt=command,
        options=ClaudeAgentOptions(
            cwd=str(cwd),
            allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
            permission_mode="bypassPermissions",
            max_turns=max_turns,
            setting_sources=["project"],
        ),
    )
    iteration_error: BaseException | None = None
    try:
        async for message in messages:
            if isinstance(message, ResultMessage):
                _record_result(message, result)
            elif isinstance(message, AssistantMessage):
                # Usage is provider-version-dependent; missing counters remain zero in this
                # legacy estimate. Generation witnesses record measured nullable cost separately.
                usage = getattr(message, "usage", None)
                if isinstance(usage, dict):
                    result.total_input_tokens += usage.get("input_tokens", 0)
                    result.total_output_tokens += usage.get("output_tokens", 0)
    except BaseException as exc:
        # Remember and immediately re-raise cancellation/provider errors before cleanup.
        iteration_error = exc
        raise
    finally:
        # query promises AsyncIterator, not AsyncGenerator; implementations may own aclose.
        close = getattr(messages, "aclose", None)
        if callable(close):
            try:
                await close()
            except Exception as cleanup_error:
                if iteration_error is None:
                    raise
                # Retain the primary failure; a fresh cleanup cancellation still propagates.
                iteration_error.add_note(f"SDK transport cleanup failed: {cleanup_error}")


def _record_result(message: ResultMessage, result: CommandResult) -> None:
    """Require SDK success and a supported terminal model stop."""
    # SDK 0.2.110 permits absent stop_reason; API end_turn/stop_sequence are normal stops.
    # Unknown future stops remain incomplete until their completion semantics are verified.
    terminal_stops = {None, "end_turn", "stop_sequence"}
    result.success = (
        message.subtype == "success"
        and not message.is_error
        and message.stop_reason in terminal_stops
    )
    result.error = (
        None
        if result.success
        else (
            f"sdk_result_incomplete: subtype={message.subtype}, stop_reason={message.stop_reason}, "
            f"is_error={message.is_error}"
        )
    )
    result.stdout_messages.append(message.result or "")


async def run_with_retry(
    fn: Callable[[], Awaitable[CommandResult]],
    max_attempts: int = 2,
    retry_on: tuple[type[BaseException], ...] = (TimeoutError,),
) -> CommandResult:
    """
    Retry only on infrastructure errors (network timeout),
    never on test assertion failures.
    """
    last_error: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            result = await fn()
            if result.success or result.error is None:
                return result
            # Clean failure (command finished but result is bad) -- no retry
            return result
        except retry_on as e:
            last_error = e
            if attempt < max_attempts - 1:
                await asyncio.sleep(5 * (attempt + 1))
    if last_error is not None:
        raise last_error
    raise RuntimeError("retry exhausted without capturing an exception")
