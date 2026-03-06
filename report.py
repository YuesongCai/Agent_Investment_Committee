"""Report generators — JSON and Markdown output for decision packets."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from config.settings import OUTPUT_DIR
from schemas import DecisionPacket, WatchlistSummary


def ensure_output_dir() -> Path:
    path = Path(OUTPUT_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_json_report(packet: DecisionPacket) -> str:
    """Save decision packet as JSON. Returns the file path."""
    out_dir = ensure_output_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{packet.ticker}_{timestamp}.json"
    filepath = out_dir / filename

    with open(filepath, "w") as f:
        json.dump(packet.model_dump(), f, indent=2, default=str)

    return str(filepath)


def save_markdown_report(packet: DecisionPacket) -> str:
    """Save decision packet as Markdown. Returns the file path."""
    out_dir = ensure_output_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{packet.ticker}_{timestamp}.md"
    filepath = out_dir / filename

    md = generate_markdown(packet)
    with open(filepath, "w") as f:
        f.write(md)

    return str(filepath)


def generate_markdown(packet: DecisionPacket) -> str:
    """Generate a human-readable Markdown report from a decision packet."""
    lines = [
        f"# Investment Committee Report: {packet.company_name} ({packet.ticker})",
        "",
        f"**Run Date:** {packet.run_date}",
        f"**Data Vintage:** {packet.data_vintage}",
        f"**Composite Score:** {packet.composite_score}/10",
        f"**Recommendation:** {packet.recommendation.value}",
        f"**Estimated Cost:** ${packet.cost_estimate_usd:.4f}",
        "",
    ]

    # QA flags
    if packet.qa_flags:
        lines.append("## QA Flags")
        lines.append("")
        for flag in packet.qa_flags:
            lines.append(f"- {flag}")
        lines.append("")

    # Consensus narrative
    lines.append("## Consensus Narrative")
    lines.append("")
    lines.append(packet.consensus_narrative)
    lines.append("")

    # Agent score breakdown
    lines.append("## Agent Score Breakdown")
    lines.append("")
    lines.append("| Agent | Score | Confidence | Thesis |")
    lines.append("|-------|-------|------------|--------|")
    for agent in packet.agent_scores:
        thesis_short = agent.one_line_thesis[:100].replace("|", "/")
        lines.append(
            f"| {agent.agent_role.value.title()} | {agent.score}/10 | "
            f"{agent.confidence.value} | {thesis_short} |"
        )
    lines.append("")

    # Debates
    if packet.debates:
        lines.append("## Debate Log")
        lines.append("")
        for i, debate in enumerate(packet.debates, 1):
            lines.append(
                f"### Debate {i}: {debate.agent_a.value.title()} vs "
                f"{debate.agent_b.value.title()} (delta: {debate.score_delta})"
            )
            lines.append("")
            lines.append(f"**Status:** {'Resolved' if debate.resolved else 'UNRESOLVED'}")
            lines.append(f"**Resolution:** {debate.resolution_note}")
            lines.append("")
            lines.append(f"**{debate.agent_a.value.title()} rebuttal:**")
            lines.append(debate.agent_a_rebuttal[:500])
            lines.append("")
            lines.append(f"**{debate.agent_b.value.title()} rebuttal:**")
            lines.append(debate.agent_b_rebuttal[:500])
            lines.append("")

    # Dissent log
    if packet.dissent_log:
        lines.append("## Dissent Log")
        lines.append("")
        for dissent in packet.dissent_log:
            score_change = ""
            if dissent.post_debate_score is not None:
                score_change = f" -> {dissent.post_debate_score}/10 post-debate"
            lines.append(
                f"- **{dissent.agent_role.value.title()}** "
                f"(score: {dissent.original_score}/10{score_change}): "
                f"{dissent.position[:200]}"
            )
        lines.append("")

    # Action plan
    lines.append("## Action Plan")
    lines.append("")
    lines.append(packet.action_plan)
    lines.append("")

    return "\n".join(lines)


def save_watchlist_summary(summary: WatchlistSummary) -> str:
    """Save watchlist summary as both JSON and Markdown."""
    out_dir = ensure_output_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON
    json_path = out_dir / f"watchlist_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(summary.model_dump(), f, indent=2, default=str)

    # Markdown
    md_path = out_dir / f"watchlist_{timestamp}.md"
    lines = [
        "# Watchlist Summary",
        "",
        f"**Run Date:** {summary.run_date}",
        f"**Tickers Analyzed:** {summary.tickers_analyzed}",
        f"**Total Cost:** ${summary.total_cost_usd:.4f}",
        "",
        "## Rankings",
        "",
        "| Rank | Ticker | Score | Recommendation | Flags |",
        "|------|--------|-------|----------------|-------|",
    ]
    for i, r in enumerate(summary.rankings, 1):
        flags = ", ".join(r.get("flags", []))
        lines.append(
            f"| {i} | {r['ticker']} | {r['composite_score']}/10 | "
            f"{r['recommendation']} | {flags} |"
        )
    lines.append("")

    if summary.flagged_disagreements:
        lines.append("## Flagged Disagreements")
        lines.append("")
        for flag in summary.flagged_disagreements:
            lines.append(
                f"- **{flag['ticker']}**: {flag['agent_a']} vs {flag['agent_b']} "
                f"(delta: {flag['score_delta']})"
            )
        lines.append("")

    with open(md_path, "w") as f:
        f.write("\n".join(lines))

    return str(json_path)
