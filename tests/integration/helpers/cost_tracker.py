"""Token and cost tracking per test run."""

from dataclasses import dataclass
from threading import Lock


@dataclass
class TestCost:
    test_name: str
    command: str
    input_tokens: int
    output_tokens: int
    duration_sec: float

    @property
    def usd(self) -> float:
        return self.input_tokens * 5 / 1_000_000 + self.output_tokens * 25 / 1_000_000


class CostTracker:
    def __init__(self, limit_usd: float):
        self.limit_usd = limit_usd
        self._costs: list[TestCost] = []
        self._lock = Lock()

    def record(self, cost: TestCost):
        with self._lock:
            self._costs.append(cost)
            total = sum(c.usd for c in self._costs)
            if total > self.limit_usd * 0.9:
                import warnings
                warnings.warn(
                    f"Budget at 90%: ${total:.2f} / ${self.limit_usd:.2f}",
                    stacklevel=2,
                )

    @property
    def total_usd(self) -> float:
        return sum(c.usd for c in self._costs)

    @property
    def over_budget(self) -> bool:
        return self.total_usd >= self.limit_usd

    def report(self) -> dict:
        total_usd = sum(c.usd for c in self._costs)
        return {
            "total_usd": round(total_usd, 4),
            "limit_usd": self.limit_usd,
            "tests": [
                {
                    "name": c.test_name,
                    "command": c.command,
                    "input_tokens": c.input_tokens,
                    "output_tokens": c.output_tokens,
                    "usd": round(c.usd, 4),
                    "duration_sec": round(c.duration_sec, 1),
                }
                for c in self._costs
            ],
        }
