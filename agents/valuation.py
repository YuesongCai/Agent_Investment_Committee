"""Valuation Analyst Agent — DCF, comps, and margin of safety assessment."""

from __future__ import annotations

from agents.base import BaseAnalystAgent
from schemas import AgentRole, TickerInput


class ValuationAgent(BaseAnalystAgent):
    role = AgentRole.VALUATION

    def system_prompt(self) -> str:
        return """You are a senior valuation analyst on an institutional investment committee. Your mandate is to assess whether the current stock price offers an attractive risk/reward based on intrinsic value.

YOUR ANALYTICAL FRAMEWORK:
1. Absolute Valuation: Conceptual DCF — assess the plausibility of growth and margin assumptions needed to justify the current market cap. What FCF yield does the market imply?
2. Relative Valuation: P/E, EV/EBITDA vs. sector peers and historical ranges. Is the stock trading at a premium or discount to its quality?
3. Margin of Safety: What downside is priced in? What upside optionality exists? Quantify bull/bear price scenarios if possible.
4. Capital Return: Buyback yield, dividend yield, total shareholder return potential.

RULES:
- Every claim MUST reference a specific data point from the input.
- When data is missing, explicitly state the gap and how it limits your analysis.
- Score on a 1-10 scale: 1 = extremely overvalued / no margin of safety, 10 = deeply undervalued with asymmetric upside.
- Separate "good company" from "good stock" — a great business at a terrible price is still a bad investment.

OUTPUT FORMAT (respond with valid JSON only):
{
  "score": <int 1-10>,
  "thesis": "<2-3 paragraph valuation thesis>",
  "bull_case": "<upside scenario with implied price/return>",
  "bear_case": "<downside scenario with implied price/return>",
  "confidence": "high" | "medium" | "low",
  "key_data_points": ["<data point 1>", "<data point 2>", ...]
}"""

    def build_user_message(self, ticker_input: TickerInput) -> str:
        fin = ticker_input.financials
        price = ticker_input.price
        parts = [
            f"COMPANY: {ticker_input.company_name} ({ticker_input.ticker})",
            f"DATA DATE: {ticker_input.data_date}",
            "",
            "VALUATION DATA:",
            f"  Market Cap: {fin.market_cap}",
            f"  P/E Ratio: {fin.pe_ratio}",
            f"  EV/EBITDA: {fin.ev_ebitda}",
            f"  Current Price: {price.current_price}",
            f"  52-Week High: {price.price_52w_high}",
            f"  52-Week Low: {price.price_52w_low}",
            "",
            "FINANCIAL PROFILE:",
            f"  Revenue TTM: {fin.revenue_ttm}",
            f"  EBITDA TTM: {fin.ebitda_ttm}",
            f"  Free Cash Flow TTM: {fin.free_cash_flow_ttm}",
            f"  Revenue Growth YoY: {fin.revenue_growth_yoy}",
            f"  Net Margin: {fin.net_margin}",
            f"  Shares Outstanding: {fin.shares_outstanding}",
        ]
        if ticker_input.sentiment.consensus_target_price:
            parts.append(
                f"  Consensus Target Price: {ticker_input.sentiment.consensus_target_price}"
            )
        if ticker_input.earnings_transcript_summary:
            parts.extend([
                "",
                "EARNINGS TRANSCRIPT SUMMARY:",
                ticker_input.earnings_transcript_summary,
            ])

        parts.append(
            "\n\nAssess the valuation of this company. Provide your assessment as JSON."
        )
        return "\n".join(parts)
