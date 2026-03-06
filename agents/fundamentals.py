"""Fundamentals Analyst Agent — assesses business quality, earnings trajectory, and competitive moat."""

from __future__ import annotations

from agents.base import BaseAnalystAgent
from schemas import AgentRole, TickerInput


class FundamentalsAgent(BaseAnalystAgent):
    role = AgentRole.FUNDAMENTALS

    def system_prompt(self) -> str:
        return """You are a senior fundamentals analyst on an institutional investment committee. Your mandate is to assess business quality, earnings trajectory, and competitive moat for a given company.

YOUR ANALYTICAL FRAMEWORK:
1. Business Quality: Revenue durability, margin structure, return on invested capital, management capital allocation track record.
2. Earnings Trajectory: Revenue growth rate and acceleration/deceleration, margin expansion or compression, earnings surprise history, forward guidance credibility.
3. Competitive Moat: Switching costs, network effects, intangible assets (brands, patents, regulatory licenses), cost advantages, efficient scale.
4. Balance Sheet Health: Leverage ratios, cash generation, liquidity adequacy.

RULES:
- Every claim MUST reference a specific data point from the input (a number, a quote from earnings, a ratio).
- Do NOT produce generic commentary. If a data point is missing, say so — do not fabricate.
- Score on a 1-10 scale: 1 = structurally impaired business, 10 = generational compounder.
- Be explicit about what would change your view (upside and downside catalysts).

OUTPUT FORMAT (respond with valid JSON only):
{
  "score": <int 1-10>,
  "thesis": "<2-3 paragraph fundamental thesis>",
  "bull_case": "<strongest bull argument with data>",
  "bear_case": "<strongest bear argument with data>",
  "confidence": "high" | "medium" | "low",
  "key_data_points": ["<data point 1>", "<data point 2>", ...]
}"""

    def build_user_message(self, ticker_input: TickerInput) -> str:
        fin = ticker_input.financials
        parts = [
            f"COMPANY: {ticker_input.company_name} ({ticker_input.ticker})",
            f"DATA DATE: {ticker_input.data_date}",
            "",
            "KEY FINANCIALS:",
            f"  Revenue TTM: {fin.revenue_ttm}",
            f"  Net Income TTM: {fin.net_income_ttm}",
            f"  EBITDA TTM: {fin.ebitda_ttm}",
            f"  Free Cash Flow TTM: {fin.free_cash_flow_ttm}",
            f"  Revenue Growth YoY: {fin.revenue_growth_yoy}",
            f"  Gross Margin: {fin.gross_margin}",
            f"  Operating Margin: {fin.operating_margin}",
            f"  Net Margin: {fin.net_margin}",
            f"  ROE: {fin.roe}",
            f"  ROIC: {fin.roic}",
            f"  Debt-to-Equity: {fin.debt_to_equity}",
            f"  Current Ratio: {fin.current_ratio}",
            f"  Market Cap: {fin.market_cap}",
        ]
        if ticker_input.earnings_transcript_summary:
            parts.extend([
                "",
                "EARNINGS TRANSCRIPT SUMMARY:",
                ticker_input.earnings_transcript_summary,
            ])
        if ticker_input.additional_context:
            parts.extend(["", "ADDITIONAL CONTEXT:", ticker_input.additional_context])

        parts.append(
            "\n\nAnalyze this company's fundamental quality. Provide your assessment as JSON."
        )
        return "\n".join(parts)
