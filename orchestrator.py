"""PM Orchestrator — aggregates analyst outputs, runs debates, produces decision packets."""

from __future__ import annotations

import re
from datetime import datetime

from agents.base import BaseAnalystAgent
from agents.fundamentals import FundamentalsAgent
from agents.valuation import ValuationAgent
from agents.sentiment import SentimentAgent
from agents.technical import TechnicalAgent
from agents.macro import MacroAgent
from config.settings import (
    DEBATE_SCORE_THRESHOLD,
    HUMAN_REVIEW_TRIGGER_THRESHOLD,
    MAX_DEBATE_ROUNDS,
)
from cost_tracker import CostTracker
from schemas import (
    AgentOutput,
    AgentRole,
    AgentScoreBreakdown,
    DebateExchange,
    DecisionPacket,
    DissentRecord,
    Recommendation,
    TickerInput,
    DEFAULT_AGENT_WEIGHTS,
)


def _score_to_recommendation(score: float) -> Recommendation:
    if score >= 8.0:
        return Recommendation.STRONG_BUY
    elif score >= 6.5:
        return Recommendation.BUY
    elif score >= 4.5:
        return Recommendation.HOLD
    elif score >= 3.0:
        return Recommendation.SELL
    else:
        return Recommendation.STRONG_SELL


def _extract_updated_score(rebuttal_text: str) -> int | None:
    match = re.search(r"UPDATED SCORE:\s*(\d+)", rebuttal_text)
    if match:
        return max(1, min(10, int(match.group(1))))
    return None


class Orchestrator:
    """PM-style orchestrator that runs the investment committee."""

    def __init__(
        self,
        agent_weights: dict[AgentRole, float] | None = None,
        cost_tracker: CostTracker | None = None,
    ):
        self.cost_tracker = cost_tracker or CostTracker()
        self.weights = agent_weights or DEFAULT_AGENT_WEIGHTS
        self.agents: dict[AgentRole, BaseAnalystAgent] = {
            AgentRole.FUNDAMENTALS: FundamentalsAgent(self.cost_tracker),
            AgentRole.VALUATION: ValuationAgent(self.cost_tracker),
            AgentRole.SENTIMENT: SentimentAgent(self.cost_tracker),
            AgentRole.TECHNICAL: TechnicalAgent(self.cost_tracker),
            AgentRole.MACRO: MacroAgent(self.cost_tracker),
        }

    def run(self, ticker_input: TickerInput) -> DecisionPacket:
        """Execute a full committee run for a single ticker."""
        # Phase 1: Collect analyst outputs
        agent_outputs: dict[AgentRole, AgentOutput] = {}
        for role, agent in self.agents.items():
            agent_outputs[role] = agent.analyze(ticker_input)

        # Phase 2: Identify disagreements and run debates
        debates: list[DebateExchange] = []
        updated_scores: dict[AgentRole, int] = {
            role: out.score for role, out in agent_outputs.items()
        }

        debate_pairs = self._find_debate_pairs(agent_outputs)
        for round_num in range(MAX_DEBATE_ROUNDS):
            if not debate_pairs:
                break
            for role_a, role_b in debate_pairs:
                exchange = self._run_debate(
                    ticker_input, agent_outputs[role_a], agent_outputs[role_b]
                )
                debates.append(exchange)

                # Update scores if agents revised
                if exchange.resolved:
                    a_new = _extract_updated_score(exchange.agent_a_rebuttal)
                    b_new = _extract_updated_score(exchange.agent_b_rebuttal)
                    if a_new is not None:
                        updated_scores[role_a] = a_new
                    if b_new is not None:
                        updated_scores[role_b] = b_new

            # Re-check for remaining disagreements
            debate_pairs = self._find_debate_pairs_from_scores(updated_scores)

        # Phase 3: Build dissent log
        dissent_log = self._build_dissent_log(agent_outputs, updated_scores, debates)

        # Phase 4: Compute composite score
        composite = sum(
            updated_scores[role] * self.weights.get(role, 0.2)
            for role in updated_scores
        )

        # Phase 5: Check human review triggers
        qa_flags: list[str] = []
        if len(debate_pairs) >= HUMAN_REVIEW_TRIGGER_THRESHOLD:
            qa_flags.append("HUMAN_REVIEW: Multiple unresolved disagreements")
        low_confidence_count = sum(
            1 for o in agent_outputs.values() if o.confidence.value == "low"
        )
        if low_confidence_count >= 3:
            qa_flags.append("HUMAN_REVIEW: Majority of agents have low confidence")

        # Phase 6: Build agent score breakdown
        agent_scores = [
            AgentScoreBreakdown(
                agent_role=role,
                score=updated_scores[role],
                confidence=agent_outputs[role].confidence,
                one_line_thesis=agent_outputs[role].thesis[:200],
            )
            for role in AgentRole
        ]

        # Phase 7: Synthesize consensus narrative
        narrative = self._synthesize_narrative(
            ticker_input, agent_outputs, updated_scores, debates
        )

        # Phase 8: Generate action plan
        action_plan = self._generate_action_plan(
            ticker_input, agent_outputs, updated_scores, debates
        )

        return DecisionPacket(
            ticker=ticker_input.ticker,
            company_name=ticker_input.company_name,
            run_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            data_vintage=str(ticker_input.data_date),
            composite_score=round(composite, 2),
            recommendation=_score_to_recommendation(composite),
            consensus_narrative=narrative,
            agent_scores=agent_scores,
            debates=debates,
            dissent_log=dissent_log,
            action_plan=action_plan,
            cost_estimate_usd=self.cost_tracker.total_cost_usd,
            qa_flags=qa_flags,
        )

    def _find_debate_pairs(
        self, outputs: dict[AgentRole, AgentOutput]
    ) -> list[tuple[AgentRole, AgentRole]]:
        roles = list(outputs.keys())
        pairs = []
        for i in range(len(roles)):
            for j in range(i + 1, len(roles)):
                delta = abs(outputs[roles[i]].score - outputs[roles[j]].score)
                if delta >= DEBATE_SCORE_THRESHOLD:
                    pairs.append((roles[i], roles[j]))
        return pairs

    def _find_debate_pairs_from_scores(
        self, scores: dict[AgentRole, int]
    ) -> list[tuple[AgentRole, AgentRole]]:
        roles = list(scores.keys())
        pairs = []
        for i in range(len(roles)):
            for j in range(i + 1, len(roles)):
                if abs(scores[roles[i]] - scores[roles[j]]) >= DEBATE_SCORE_THRESHOLD:
                    pairs.append((roles[i], roles[j]))
        return pairs

    def _run_debate(
        self,
        ticker_input: TickerInput,
        output_a: AgentOutput,
        output_b: AgentOutput,
    ) -> DebateExchange:
        agent_a = self.agents[output_a.agent_role]
        agent_b = self.agents[output_b.agent_role]

        # Agent A rebuts Agent B's view
        opposing_b = (
            f"[{output_b.agent_role.value} analyst, score {output_b.score}/10]\n"
            f"Thesis: {output_b.thesis}\n"
            f"Bull case: {output_b.bull_case}\n"
            f"Bear case: {output_b.bear_case}"
        )
        rebuttal_a = agent_a.rebuttal(ticker_input, opposing_b)

        # Agent B rebuts Agent A's view
        opposing_a = (
            f"[{output_a.agent_role.value} analyst, score {output_a.score}/10]\n"
            f"Thesis: {output_a.thesis}\n"
            f"Bull case: {output_a.bull_case}\n"
            f"Bear case: {output_a.bear_case}"
        )
        rebuttal_b = agent_b.rebuttal(ticker_input, opposing_a)

        # Check if scores converged
        new_a = _extract_updated_score(rebuttal_a)
        new_b = _extract_updated_score(rebuttal_b)
        score_a = new_a if new_a is not None else output_a.score
        score_b = new_b if new_b is not None else output_b.score
        resolved = abs(score_a - score_b) < DEBATE_SCORE_THRESHOLD

        return DebateExchange(
            agent_a=output_a.agent_role,
            agent_b=output_b.agent_role,
            score_delta=abs(output_a.score - output_b.score),
            agent_a_rebuttal=rebuttal_a,
            agent_b_rebuttal=rebuttal_b,
            resolved=resolved,
            resolution_note=(
                f"Scores converged: {output_a.agent_role.value}={score_a}, "
                f"{output_b.agent_role.value}={score_b}"
                if resolved
                else f"Unresolved: {output_a.agent_role.value}={score_a}, "
                f"{output_b.agent_role.value}={score_b}"
            ),
        )

    def _build_dissent_log(
        self,
        original_outputs: dict[AgentRole, AgentOutput],
        updated_scores: dict[AgentRole, int],
        debates: list[DebateExchange],
    ) -> list[DissentRecord]:
        """Log any agents whose final scores diverge significantly from consensus."""
        if not updated_scores:
            return []

        avg_score = sum(updated_scores.values()) / len(updated_scores)
        dissent = []
        for role, score in updated_scores.items():
            if abs(score - avg_score) >= DEBATE_SCORE_THRESHOLD:
                original = original_outputs[role]
                dissent.append(
                    DissentRecord(
                        agent_role=role,
                        original_score=original.score,
                        post_debate_score=score if score != original.score else None,
                        position=original.thesis[:300],
                    )
                )
        return dissent

    def _synthesize_narrative(
        self,
        ticker_input: TickerInput,
        outputs: dict[AgentRole, AgentOutput],
        scores: dict[AgentRole, int],
        debates: list[DebateExchange],
    ) -> str:
        """Build a 2-3 paragraph consensus narrative from all agent outputs."""
        composite = sum(
            scores[role] * self.weights.get(role, 0.2) for role in scores
        )
        recommendation = _score_to_recommendation(composite)

        # Identify highest and lowest scoring agents
        sorted_agents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        most_bullish = sorted_agents[0]
        most_bearish = sorted_agents[-1]

        paragraphs = []

        # Paragraph 1: Overall view
        paragraphs.append(
            f"The investment committee assigns {ticker_input.company_name} "
            f"({ticker_input.ticker}) a composite score of {composite:.1f}/10, "
            f"resulting in a {recommendation.value} recommendation. "
            f"The most constructive view comes from the {most_bullish[0].value} analyst "
            f"(score: {most_bullish[1]}/10), while the most cautious assessment is from "
            f"the {most_bearish[0].value} analyst (score: {most_bearish[1]}/10)."
        )

        # Paragraph 2: Key thesis points
        bull_points = [outputs[r].bull_case for r in [AgentRole.FUNDAMENTALS, AgentRole.VALUATION] if r in outputs]
        bear_points = [outputs[r].bear_case for r in [AgentRole.SENTIMENT, AgentRole.MACRO] if r in outputs]
        paragraphs.append(
            f"On the bull side, the committee highlights: {bull_points[0][:200] if bull_points else 'N/A'}. "
            f"Key risks include: {bear_points[0][:200] if bear_points else 'N/A'}."
        )

        # Paragraph 3: Debate outcomes
        if debates:
            unresolved = [d for d in debates if not d.resolved]
            resolved = [d for d in debates if d.resolved]
            debate_summary = (
                f"The committee debated {len(debates)} disagreement(s). "
                f"{len(resolved)} were resolved through rebuttal; "
                f"{len(unresolved)} remain as minority positions in the dissent log."
            )
            paragraphs.append(debate_summary)
        else:
            paragraphs.append(
                "No significant disagreements were identified among analysts — "
                "the committee view is largely aligned."
            )

        return "\n\n".join(paragraphs)

    def _generate_action_plan(
        self,
        ticker_input: TickerInput,
        outputs: dict[AgentRole, AgentOutput],
        scores: dict[AgentRole, int],
        debates: list[DebateExchange],
    ) -> str:
        """Generate suggested next research steps and monitoring triggers."""
        composite = sum(
            scores[role] * self.weights.get(role, 0.2) for role in scores
        )
        actions = []

        # Low confidence agents need more data
        for role, output in outputs.items():
            if output.confidence.value == "low":
                actions.append(
                    f"- Gather more data for {role.value} analysis (confidence was low)"
                )

        # Unresolved debates need follow-up
        unresolved = [d for d in debates if not d.resolved]
        for d in unresolved:
            actions.append(
                f"- Deep-dive into {d.agent_a.value} vs. {d.agent_b.value} disagreement"
            )

        # Standard monitoring triggers
        if composite >= 6.5:
            actions.append("- Monitor for position entry on next pullback to support levels")
            actions.append("- Review after next earnings report for thesis confirmation")
        elif composite <= 3.5:
            actions.append("- Monitor for further deterioration — potential risk management trigger")
            actions.append("- Revisit if macro conditions shift favorably")
        else:
            actions.append("- Revisit in 30 days or after next material catalyst")
            actions.append("- Track earnings estimates revisions for directional signal")

        if not actions:
            actions.append("- Standard quarterly review cycle")

        return "\n".join(actions)
