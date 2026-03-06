"""Token usage and cost tracking for API calls."""

from __future__ import annotations

from dataclasses import dataclass, field

from config.settings import INPUT_COST_PER_1M, OUTPUT_COST_PER_1M


@dataclass
class UsageRecord:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def cost_usd(self) -> float:
        return (
            self.input_tokens * INPUT_COST_PER_1M / 1_000_000
            + self.output_tokens * OUTPUT_COST_PER_1M / 1_000_000
        )


@dataclass
class CostTracker:
    records: list[UsageRecord] = field(default_factory=list)

    def record(self, input_tokens: int, output_tokens: int) -> None:
        self.records.append(UsageRecord(input_tokens, output_tokens))

    @property
    def total_input_tokens(self) -> int:
        return sum(r.input_tokens for r in self.records)

    @property
    def total_output_tokens(self) -> int:
        return sum(r.output_tokens for r in self.records)

    @property
    def total_cost_usd(self) -> float:
        return sum(r.cost_usd for r in self.records)

    def summary(self) -> str:
        return (
            f"API Cost: ${self.total_cost_usd:.4f} "
            f"(input: {self.total_input_tokens:,} tokens, "
            f"output: {self.total_output_tokens:,} tokens, "
            f"{len(self.records)} calls)"
        )
