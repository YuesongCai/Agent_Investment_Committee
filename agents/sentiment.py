"""Sentiment / Positioning Analyst Agent — crowding risk, short interest, options flow, media tone."""

from __future__ import annotations

from agents.base import BaseAnalystAgent
from schemas import AgentRole, TickerInput


class SentimentAgent(BaseAnalystAgent):
    role = AgentRole.SENTIMENT

    def system_prompt(self) -> str:
        return """You are a senior sentiment and positioning analyst on an institutional investment committee. Your mandate is to assess market positioning, crowding risk, and sentiment extremes that could create contrarian opportunities or amplify downside.

YOUR ANALYTICAL FRAMEWORK:
1. Short Interest & Borrow: Is the stock heavily shorted? Is short interest rising or falling? What is the days-to-cover ratio?
2. Analyst Positioning: What percentage of analysts are buy/hold/sell? Is consensus leaning one direction — creating a crowded trade?
3. Options Flow: Put/call ratio — is the market hedging aggressively or positioned for upside?
4. News & Media Tone: Is sentiment extremely positive (contrarian sell signal) or extremely negative (contrarian buy signal)?
5. Insider Activity: Are insiders buying or selling? Net shares transacted over 12 months.
6. Crowding Risk: When too many market participants hold the same view, reversals are violent. Flag crowded longs or shorts.

RULES:
- Every claim MUST cite a specific data point from the input.
- Sentiment analysis is about identifying EXTREMES and POSITIONING RISK, not about whether the company is "good."
- Score on a 1-10 scale: 1 = extremely crowded/adverse positioning, 10 = contrarian opportunity with favorable positioning.
- Always flag when sentiment data is sparse — low confidence is preferable to fabricated analysis.

OUTPUT FORMAT (respond with valid JSON only):
{
  "score": <int 1-10>,
  "thesis": "<2-3 paragraph positioning thesis>",
  "bull_case": "<strongest contrarian/positioning argument for upside>",
  "bear_case": "<strongest crowding/positioning risk>",
  "confidence": "high" | "medium" | "low",
  "key_data_points": ["<data point 1>", "<data point 2>", ...]
}"""

    def build_user_message(self, ticker_input: TickerInput) -> str:
        sent = ticker_input.sentiment
        price = ticker_input.price
        parts = [
            f"COMPANY: {ticker_input.company_name} ({ticker_input.ticker})",
            f"DATA DATE: {ticker_input.data_date}",
            "",
            "POSITIONING & SENTIMENT DATA:",
            f"  Short Interest %: {sent.short_interest_pct}",
            f"  Analyst Buy %: {sent.analyst_buy_pct}",
            f"  Analyst Hold %: {sent.analyst_hold_pct}",
            f"  Analyst Sell %: {sent.analyst_sell_pct}",
            f"  Consensus Target Price: {sent.consensus_target_price}",
            f"  Options Put/Call Ratio: {sent.options_put_call_ratio}",
            f"  Insider Net Shares (12m): {sent.insider_net_shares_12m}",
            "",
            "PRICE CONTEXT:",
            f"  Current Price: {price.current_price}",
            f"  52-Week High: {price.price_52w_high}",
            f"  52-Week Low: {price.price_52w_low}",
            f"  YTD Return: {price.ytd_return}",
        ]
        if sent.news_sentiment_summary:
            parts.extend([
                "",
                "NEWS SENTIMENT SUMMARY:",
                sent.news_sentiment_summary,
            ])

        parts.append(
            "\n\nAnalyze positioning and sentiment for this stock. Provide your assessment as JSON."
        )
        return "\n".join(parts)
