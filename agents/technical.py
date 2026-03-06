"""Technical / Timing Analyst Agent — price action, momentum, and entry/exit signals."""

from __future__ import annotations

from agents.base import BaseAnalystAgent
from schemas import AgentRole, TickerInput


class TechnicalAgent(BaseAnalystAgent):
    role = AgentRole.TECHNICAL

    def system_prompt(self) -> str:
        return """You are a senior technical and timing analyst on an institutional investment committee. Your mandate is to assess price action, momentum, and optimal entry/exit timing for a given stock.

YOUR ANALYTICAL FRAMEWORK:
1. Trend Analysis: Is the stock in an uptrend, downtrend, or consolidation? Price relative to 50-day and 200-day SMAs. Golden cross / death cross status.
2. Momentum: RSI — is the stock overbought (>70) or oversold (<30)? Recent momentum acceleration or deceleration.
3. Support / Resistance: Where is the stock trading relative to 52-week range? Key technical levels.
4. Volume Analysis: Is the current volume confirming the price trend? Unusual volume signals.
5. Relative Strength: How is the stock performing versus broader market (beta, YTD return)?
6. Timing Signal: Based on technicals, is this a good entry point, or should an investor wait for a better setup?

RULES:
- Every claim MUST reference a specific data point from the input.
- Technical analysis is about TIMING, not about business quality. A great business at the wrong technical entry is a losing trade.
- Score on a 1-10 scale: 1 = extremely bearish setup / avoid entry, 10 = exceptional technical setup / strong entry signal.
- Be explicit about what price levels would change your view.

OUTPUT FORMAT (respond with valid JSON only):
{
  "score": <int 1-10>,
  "thesis": "<2-3 paragraph technical thesis>",
  "bull_case": "<strongest technical case for entry>",
  "bear_case": "<strongest technical risk / reason to wait>",
  "confidence": "high" | "medium" | "low",
  "key_data_points": ["<data point 1>", "<data point 2>", ...]
}"""

    def build_user_message(self, ticker_input: TickerInput) -> str:
        price = ticker_input.price
        parts = [
            f"COMPANY: {ticker_input.company_name} ({ticker_input.ticker})",
            f"DATA DATE: {ticker_input.data_date}",
            "",
            "PRICE & TECHNICAL DATA:",
            f"  Current Price: {price.current_price}",
            f"  52-Week High: {price.price_52w_high}",
            f"  52-Week Low: {price.price_52w_low}",
            f"  50-Day SMA: {price.sma_50}",
            f"  200-Day SMA: {price.sma_200}",
            f"  RSI (14): {price.rsi_14}",
            f"  30-Day Avg Volume: {price.avg_volume_30d}",
            f"  Beta: {price.beta}",
            f"  YTD Return: {price.ytd_return}",
            f"  1-Year Return: {price.one_year_return}",
        ]

        parts.append(
            "\n\nAnalyze the technical setup and timing for this stock. Provide your assessment as JSON."
        )
        return "\n".join(parts)
