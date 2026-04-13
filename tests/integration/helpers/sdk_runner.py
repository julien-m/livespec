"""Claude Code SDK wrapper for running LiveSpec commands in tests."""

import asyncio
import shutil
import tempfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path

try:
    from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, query

    HAS_SDK = True
except ImportError:
    HAS_SDK = False


@dataclass
class CommandResult:
    success: bool
    cwd: Path
    stdout_messages: list[str] = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    error: str | None = None

    @property
    def estimated_cost_usd(self) -> float:
        # claude-opus-4-6: $5/1M input, $25/1M output
        return self.total_input_tokens * 5 / 1_000_000 + self.total_output_tokens * 25 / 1_000_000


async def run_livespec_command(
    command: str,
    fixture_name: str,
    fixtures_base: Path,
    timeout_sec: int = 120,
    max_turns: int = 40,
) -> CommandResult:
    """
    Copy the fixture into a temporary directory and run the LiveSpec
    command via the Claude Code SDK.
    """
    fixture_src = fixtures_base / fixture_name

    with tempfile.TemporaryDirectory(prefix="livespec_test_") as tmp_dir:
        cwd = Path(tmp_dir)
        shutil.copytree(fixture_src, cwd, dirs_exist_ok=True)

        result = CommandResult(success=False, cwd=cwd)

        try:
            async for message in query(
                prompt=command,
                options=ClaudeAgentOptions(
                    cwd=str(cwd),
                    allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
                    permission_mode="bypassPermissions",
                    allow_dangerously_skip_permissions=True,
                    max_turns=max_turns,
                    setting_sources=["project"],
                ),
            ):
                if isinstance(message, ResultMessage):
                    result.success = message.stop_reason == "end_turn"
                    result.stdout_messages.append(message.result or "")
                elif isinstance(message, AssistantMessage) and message.usage:
                    result.total_input_tokens += message.usage.get("input_tokens", 0)
                    result.total_output_tokens += message.usage.get("output_tokens", 0)

        except Exception as e:
            result.error = str(e)

        return result


async def run_with_retry(
    fn: Callable[[], Awaitable[CommandResult]],
    max_attempts: int = 2,
    retry_on: tuple[type, ...] = (TimeoutError,),
) -> CommandResult:
    """
    Retry only on infrastructure errors (network timeout),
    never on test assertion failures.
    """
    last_error = None
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
    raise last_error
