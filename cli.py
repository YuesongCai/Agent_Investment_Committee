"""CLI interface for the AI Investment Committee."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from config.settings import OUTPUT_DIR, RUN_LOG_PATH
from cost_tracker import CostTracker
from data.input_validator import InputValidationError, load_ticker_input
from orchestrator import Orchestrator
from qa.validator import (
    QAResult,
    append_to_run_log,
    check_consistency,
    validate_decision_packet,
)
from report import save_json_report, save_markdown_report, save_watchlist_summary
from schemas import AgentRole, DecisionPacket, WatchlistSummary

console = Console()


@click.group()
def main():
    """AI Investment Committee — Multi-Agent Equity Research System"""
    pass


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--json-only", is_flag=True, help="Output JSON only, skip Markdown")
def analyze(input_file: str, json_only: bool):
    """Run investment committee analysis on a single ticker."""
    console.print(f"\n[bold]Loading input:[/bold] {input_file}")

    try:
        ticker_input = load_ticker_input(input_file)
    except InputValidationError as e:
        console.print(f"[red]Input validation error:[/red] {e}")
        sys.exit(1)

    console.print(
        f"[bold]Running committee for:[/bold] "
        f"{ticker_input.company_name} ({ticker_input.ticker})"
    )

    cost_tracker = CostTracker()
    orchestrator = Orchestrator(cost_tracker=cost_tracker)

    with console.status("[bold green]Analysts deliberating..."):
        packet = orchestrator.run(ticker_input)

    # QA validation
    qa_result = validate_decision_packet(packet)
    packet.qa_flags.extend(
        [f"QA_FAIL: {f}" for f in qa_result.failed]
    )

    # Save outputs
    json_path = save_json_report(packet)
    console.print(f"[green]JSON report saved:[/green] {json_path}")

    if not json_only:
        md_path = save_markdown_report(packet)
        console.print(f"[green]Markdown report saved:[/green] {md_path}")

    # Append to run log
    append_to_run_log(packet, qa_result, RUN_LOG_PATH)

    # Print summary
    _print_summary(packet, qa_result, cost_tracker)


@main.command()
@click.argument("watchlist_file", type=click.Path(exists=True))
def watchlist(watchlist_file: str):
    """Run committee across a watchlist of tickers."""
    console.print(f"\n[bold]Loading watchlist:[/bold] {watchlist_file}")

    with open(watchlist_file) as f:
        config = json.load(f)

    ticker_files = config.get("tickers", [])
    weight_config = config.get("agent_weights", None)

    agent_weights = None
    if weight_config:
        agent_weights = {AgentRole(k): v for k, v in weight_config.items()}

    packets: list[DecisionPacket] = []
    total_cost_tracker = CostTracker()
    flagged_disagreements: list[dict] = []

    for ticker_file in ticker_files:
        try:
            ticker_input = load_ticker_input(ticker_file)
        except InputValidationError as e:
            console.print(f"[red]Skipping {ticker_file}:[/red] {e}")
            continue

        console.print(
            f"\n[bold]Analyzing:[/bold] {ticker_input.company_name} ({ticker_input.ticker})"
        )

        cost_tracker = CostTracker()
        orchestrator = Orchestrator(
            agent_weights=agent_weights, cost_tracker=cost_tracker
        )

        with console.status("[bold green]Analysts deliberating..."):
            packet = orchestrator.run(ticker_input)

        # QA
        qa_result = validate_decision_packet(packet)
        packet.qa_flags.extend([f"QA_FAIL: {f}" for f in qa_result.failed])

        # Save individual reports
        save_json_report(packet)
        save_markdown_report(packet)
        append_to_run_log(packet, qa_result, RUN_LOG_PATH)

        packets.append(packet)

        # Track costs
        for r in cost_tracker.records:
            total_cost_tracker.record(r.input_tokens, r.output_tokens)

        # Track disagreements
        for debate in packet.debates:
            if not debate.resolved:
                flagged_disagreements.append({
                    "ticker": packet.ticker,
                    "agent_a": debate.agent_a.value,
                    "agent_b": debate.agent_b.value,
                    "score_delta": debate.score_delta,
                })

        _print_summary(packet, qa_result, cost_tracker)

    # Build watchlist summary
    if packets:
        rankings = sorted(
            [
                {
                    "ticker": p.ticker,
                    "company_name": p.company_name,
                    "composite_score": p.composite_score,
                    "recommendation": p.recommendation.value,
                    "flags": p.qa_flags,
                }
                for p in packets
            ],
            key=lambda x: x["composite_score"],
            reverse=True,
        )

        summary = WatchlistSummary(
            run_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            tickers_analyzed=len(packets),
            total_cost_usd=total_cost_tracker.total_cost_usd,
            rankings=rankings,
            flagged_disagreements=flagged_disagreements,
        )

        summary_path = save_watchlist_summary(summary)
        console.print(f"\n[bold green]Watchlist summary saved:[/bold green] {summary_path}")
        console.print(f"[bold]Total batch cost:[/bold] ${total_cost_tracker.total_cost_usd:.4f}")

        # Print ranking table
        _print_watchlist_table(rankings, flagged_disagreements)


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
def consistency_test(input_file: str):
    """Run the same ticker twice and compare for consistency."""
    console.print(f"\n[bold]Consistency test:[/bold] {input_file}")

    try:
        ticker_input = load_ticker_input(input_file)
    except InputValidationError as e:
        console.print(f"[red]Input validation error:[/red] {e}")
        sys.exit(1)

    console.print(f"Running {ticker_input.ticker} twice with identical inputs...\n")

    # Run A
    console.print("[bold]Run A:[/bold]")
    cost_a = CostTracker()
    orch_a = Orchestrator(cost_tracker=cost_a)
    with console.status("[bold green]Run A deliberating..."):
        packet_a = orch_a.run(ticker_input)
    console.print(f"  Composite: {packet_a.composite_score}, Rec: {packet_a.recommendation.value}")

    # Run B
    console.print("[bold]Run B:[/bold]")
    cost_b = CostTracker()
    orch_b = Orchestrator(cost_tracker=cost_b)
    with console.status("[bold green]Run B deliberating..."):
        packet_b = orch_b.run(ticker_input)
    console.print(f"  Composite: {packet_b.composite_score}, Rec: {packet_b.recommendation.value}")

    # Compare
    qa_result = check_consistency(packet_a, packet_b)
    console.print(f"\n[bold]Consistency Results:[/bold]")
    console.print(qa_result.summary())

    if qa_result.ok:
        console.print("[bold green]PASS[/bold green] — Scores consistent within tolerance")
    else:
        console.print("[bold red]FAIL[/bold red] — Score drift detected")


def _print_summary(
    packet: DecisionPacket, qa_result: QAResult, cost_tracker: CostTracker
) -> None:
    """Print a formatted summary to the console."""
    table = Table(title=f"{packet.company_name} ({packet.ticker})")
    table.add_column("Agent", style="cyan")
    table.add_column("Score", justify="center")
    table.add_column("Confidence", justify="center")

    for agent in packet.agent_scores:
        score_style = "green" if agent.score >= 7 else "yellow" if agent.score >= 5 else "red"
        table.add_row(
            agent.agent_role.value.title(),
            f"[{score_style}]{agent.score}/10[/{score_style}]",
            agent.confidence.value,
        )

    console.print(table)

    rec_style = "green" if "Buy" in packet.recommendation.value else "yellow" if "Hold" in packet.recommendation.value else "red"
    console.print(
        f"[bold]Composite:[/bold] {packet.composite_score}/10  "
        f"[bold]Recommendation:[/bold] [{rec_style}]{packet.recommendation.value}[/{rec_style}]"
    )

    if packet.debates:
        console.print(f"[bold]Debates:[/bold] {len(packet.debates)} triggered")
    if packet.dissent_log:
        console.print(f"[bold]Dissent:[/bold] {len(packet.dissent_log)} minority position(s)")

    console.print(qa_result.summary())
    console.print(cost_tracker.summary())


def _print_watchlist_table(
    rankings: list[dict], flagged: list[dict]
) -> None:
    """Print the watchlist ranking table."""
    table = Table(title="Watchlist Rankings")
    table.add_column("Rank", justify="center", style="bold")
    table.add_column("Ticker", style="cyan")
    table.add_column("Score", justify="center")
    table.add_column("Recommendation")
    table.add_column("Flags")

    for i, r in enumerate(rankings, 1):
        score_style = "green" if r["composite_score"] >= 6.5 else "yellow" if r["composite_score"] >= 4.5 else "red"
        flags = ", ".join(r.get("flags", []))[:50]
        table.add_row(
            str(i),
            r["ticker"],
            f"[{score_style}]{r['composite_score']}/10[/{score_style}]",
            r["recommendation"],
            flags,
        )

    console.print(table)

    if flagged:
        console.print("\n[bold yellow]Flagged Disagreements:[/bold yellow]")
        for f in flagged:
            console.print(
                f"  {f['ticker']}: {f['agent_a']} vs {f['agent_b']} "
                f"(delta: {f['score_delta']})"
            )


if __name__ == "__main__":
    main()
