"""Base analyst agent with LLM interaction logic."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

import anthropic

from config.settings import ANTHROPIC_API_KEY, LLM_MODEL, MAX_INPUT_TOKENS_PER_AGENT
from cost_tracker import CostTracker
from schemas import AgentOutput, AgentRole, Confidence, TickerInput


def _trim_text(text: str, max_chars: int) -> str:
    """Trim text to approximate token budget (1 token ~ 4 chars)."""
    max_chars = max_chars * 4
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated for token budget]"


class BaseAnalystAgent(ABC):
    """Base class for specialist analyst agents."""

    role: AgentRole

    def __init__(self, cost_tracker: CostTracker | None = None):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.cost_tracker = cost_tracker or CostTracker()

    @abstractmethod
    def system_prompt(self) -> str:
        """Return the agent's system prompt."""

    @abstractmethod
    def build_user_message(self, ticker_input: TickerInput) -> str:
        """Build the user message from ticker input data."""

    def analyze(self, ticker_input: TickerInput) -> AgentOutput:
        """Run analysis and return structured output."""
        system = _trim_text(self.system_prompt(), MAX_INPUT_TOKENS_PER_AGENT)
        user_msg = _trim_text(
            self.build_user_message(ticker_input), MAX_INPUT_TOKENS_PER_AGENT
        )

        response = self.client.messages.create(
            model=LLM_MODEL,
            max_tokens=1500,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )

        self.cost_tracker.record(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        return self._parse_response(response.content[0].text)

    def rebuttal(self, ticker_input: TickerInput, opposing_view: str) -> str:
        """Produce a rebuttal to an opposing agent's view during debate."""
        system = self.system_prompt()
        user_msg = (
            f"You previously analyzed {ticker_input.ticker}. "
            f"Another analyst on the committee disagrees with your view. "
            f"Their position:\n\n{opposing_view}\n\n"
            f"Provide a concise rebuttal (2-3 paragraphs). "
            f"If their points have merit, acknowledge them and adjust your score if warranted. "
            f"End with 'UPDATED SCORE: X' if you change your score, or 'SCORE UNCHANGED' if not."
        )

        response = self.client.messages.create(
            model=LLM_MODEL,
            max_tokens=800,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )

        self.cost_tracker.record(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        return response.content[0].text

    def _parse_response(self, text: str) -> AgentOutput:
        """Parse LLM response into AgentOutput. Tries JSON first, then structured text."""
        # Try to extract JSON block
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return AgentOutput(
                    agent_role=self.role,
                    score=int(data.get("score", 5)),
                    thesis=str(data.get("thesis", "")),
                    bull_case=str(data.get("bull_case", "")),
                    bear_case=str(data.get("bear_case", "")),
                    confidence=Confidence(data.get("confidence", "medium").lower()),
                    key_data_points=data.get("key_data_points", []),
                )
            except (json.JSONDecodeError, ValueError, KeyError):
                pass

        # Fallback: extract from text
        score = 5
        score_match = re.search(r"[Ss]core[:\s]*(\d+)", text)
        if score_match:
            score = max(1, min(10, int(score_match.group(1))))

        confidence = Confidence.MEDIUM
        if re.search(r"[Cc]onfidence[:\s]*(high)", text, re.I):
            confidence = Confidence.HIGH
        elif re.search(r"[Cc]onfidence[:\s]*(low)", text, re.I):
            confidence = Confidence.LOW

        return AgentOutput(
            agent_role=self.role,
            score=score,
            thesis=text[:500],
            bull_case="See thesis for bull case arguments.",
            bear_case="See thesis for bear case arguments.",
            confidence=confidence,
            key_data_points=[],
        )
