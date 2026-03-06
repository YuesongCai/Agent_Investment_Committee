"""QA validation layer for decision packets and agent outputs."""

from __future__ import annotations

import json
import re
from pathlib import Path

from schemas import AgentOutput, DecisionPacket


class QAResult:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[str] = []
        self.warnings: list[str] = []

    @property
    def ok(self) -> bool:
        return len(self.failed) == 0

    def summary(self) -> str:
        total = len(self.passed) + len(self.failed)
        lines = [f"QA: {len(self.passed)}/{total} checks passed"]
        for f in self.failed:
            lines.append(f"  FAIL: {f}")
        for w in self.warnings:
            lines.append(f"  WARN: {w}")
        return "\n".join(lines)


def validate_decision_packet(packet: DecisionPacket) -> QAResult:
    """Run all QA checks on a decision packet."""
    result = QAResult()

    # Schema conformance
    _check_schema(packet, result)

    # Score bounds
    _check_scores(packet, result)

    # Claim hygiene per agent
    _check_claim_hygiene(packet, result)

    # Narrative not empty
    _check_narrative(packet, result)

    return result


def _check_schema(packet: DecisionPacket, result: QAResult) -> None:
    """Check all required fields are populated."""
    required = [
        ("ticker", packet.ticker),
        ("company_name", packet.company_name),
        ("run_date", packet.run_date),
        ("data_vintage", packet.data_vintage),
        ("recommendation", packet.recommendation),
        ("consensus_narrative", packet.consensus_narrative),
        ("action_plan", packet.action_plan),
    ]
    for name, value in required:
        if value:
            result.passed.append(f"Field '{name}' is populated")
        else:
            result.failed.append(f"Field '{name}' is missing or empty")

    if len(packet.agent_scores) == 5:
        result.passed.append("All 5 agent scores present")
    else:
        result.failed.append(
            f"Expected 5 agent scores, got {len(packet.agent_scores)}"
        )


def _check_scores(packet: DecisionPacket, result: QAResult) -> None:
    """Validate score ranges."""
    if 1.0 <= packet.composite_score <= 10.0:
        result.passed.append(
            f"Composite score {packet.composite_score} in valid range"
        )
    else:
        result.failed.append(
            f"Composite score {packet.composite_score} out of range [1, 10]"
        )

    for agent in packet.agent_scores:
        if 1 <= agent.score <= 10:
            result.passed.append(
                f"{agent.agent_role.value} score {agent.score} in range"
            )
        else:
            result.failed.append(
                f"{agent.agent_role.value} score {agent.score} out of range"
            )


def _check_claim_hygiene(packet: DecisionPacket, result: QAResult) -> None:
    """Check that agent theses reference specific data points."""
    for agent in packet.agent_scores:
        thesis = agent.one_line_thesis
        # Check for presence of numbers (data point references)
        has_number = bool(re.search(r"\d+\.?\d*[%$BMKbmk]?", thesis))
        if has_number:
            result.passed.append(
                f"{agent.agent_role.value} thesis contains data reference"
            )
        else:
            result.warnings.append(
                f"{agent.agent_role.value} thesis may lack specific data points"
            )


def _check_narrative(packet: DecisionPacket, result: QAResult) -> None:
    """Check consensus narrative quality."""
    if len(packet.consensus_narrative) > 100:
        result.passed.append("Consensus narrative has substantive content")
    else:
        result.warnings.append("Consensus narrative is very short")


def check_consistency(packet_a: DecisionPacket, packet_b: DecisionPacket) -> QAResult:
    """Compare two runs of the same ticker for consistency."""
    result = QAResult()

    if packet_a.ticker != packet_b.ticker:
        result.failed.append(
            f"Ticker mismatch: {packet_a.ticker} vs {packet_b.ticker}"
        )
        return result

    # Composite score delta
    delta = abs(packet_a.composite_score - packet_b.composite_score)
    if delta <= 1.0:
        result.passed.append(
            f"Composite score delta {delta:.2f} within tolerance (<=1.0)"
        )
    else:
        result.failed.append(
            f"Composite score delta {delta:.2f} exceeds tolerance (>1.0): "
            f"run A={packet_a.composite_score}, run B={packet_b.composite_score}"
        )

    # Per-agent score comparison
    scores_a = {a.agent_role: a.score for a in packet_a.agent_scores}
    scores_b = {b.agent_role: b.score for b in packet_b.agent_scores}
    for role in scores_a:
        if role in scores_b:
            agent_delta = abs(scores_a[role] - scores_b[role])
            if agent_delta <= 1:
                result.passed.append(
                    f"{role.value} score delta {agent_delta} within tolerance"
                )
            else:
                result.failed.append(
                    f"{role.value} score delta {agent_delta} exceeds tolerance: "
                    f"A={scores_a[role]}, B={scores_b[role]}"
                )

    # Recommendation consistency
    if packet_a.recommendation == packet_b.recommendation:
        result.passed.append("Recommendation consistent across runs")
    else:
        result.warnings.append(
            f"Recommendation changed: {packet_a.recommendation.value} "
            f"-> {packet_b.recommendation.value}"
        )

    return result


def append_to_run_log(packet: DecisionPacket, qa_result: QAResult, log_path: str) -> None:
    """Append run result to persistent JSON log."""
    log_file = Path(log_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    if log_file.exists():
        with open(log_file) as f:
            entries = json.load(f)

    entries.append({
        "ticker": packet.ticker,
        "run_date": packet.run_date,
        "composite_score": packet.composite_score,
        "recommendation": packet.recommendation.value,
        "cost_usd": packet.cost_estimate_usd,
        "qa_passed": len(qa_result.passed),
        "qa_failed": len(qa_result.failed),
        "qa_warnings": len(qa_result.warnings),
        "qa_ok": qa_result.ok,
    })

    with open(log_file, "w") as f:
        json.dump(entries, f, indent=2)
