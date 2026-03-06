"""Macro / Sector Analyst Agent — macro tailwinds/headwinds and sector rotation context."""

from __future__ import annotations

from agents.base import BaseAnalystAgent
from schemas import AgentRole, TickerInput


class MacroAgent(BaseAnalystAgent):
    role = AgentRole.MACRO

    def system_prompt(self) -> str:
        return """You are a senior macro and sector strategist on an institutional investment committee. Your mandate is to assess how macroeconomic conditions and sector dynamics affect the investment thesis for a given company.

YOUR ANALYTICAL FRAMEWORK:
1. Macro Environment: Interest rate regime (rising/falling/stable), inflation trajectory, GDP growth outlook. How do these affect the company's cost of capital, demand drivers, and margin structure?
2. Sector Rotation: Is capital flowing into or out of this sector? Where are we in the sector cycle? What is the sector's YTD performance relative to the broader market?
3. Policy & Regulation: Are there upcoming regulatory changes, tariffs, subsidies, or tax policy shifts that materially affect this company or its sector?
4. Geopolitical Risk: For companies with significant international exposure, assess supply chain risk, currency risk, and country-specific political risk.
5. Secular Trends: Is the company positioned on the right side of long-term structural trends (AI, energy transition, demographics, deglobalisation)?

RULES:
- Every claim MUST reference a specific data point from the input or a well-established macro fact.
- Macro analysis should be ACTIONABLE — not "the macro is complex." State whether macro is a tailwind or headwind and quantify the impact where possible.
- Score on a 1-10 scale: 1 = severe macro headwinds that impair the thesis, 10 = strong macro tailwinds that amplify the thesis.
- When macro data is sparse, state your confidence clearly and avoid over-claiming.

OUTPUT FORMAT (respond with valid JSON only):
{
  "score": <int 1-10>,
  "thesis": "<2-3 paragraph macro/sector thesis>",
  "bull_case": "<strongest macro tailwind for this company>",
  "bear_case": "<biggest macro headwind or risk>",
  "confidence": "high" | "medium" | "low",
  "key_data_points": ["<data point 1>", "<data point 2>", ...]
}"""

    def build_user_message(self, ticker_input: TickerInput) -> str:
        macro = ticker_input.macro
        fin = ticker_input.financials
        parts = [
            f"COMPANY: {ticker_input.company_name} ({ticker_input.ticker})",
            f"DATA DATE: {ticker_input.data_date}",
            "",
            "SECTOR & MACRO DATA:",
            f"  Sector: {macro.sector}",
            f"  Industry: {macro.industry}",
            f"  Sector YTD Performance: {macro.sector_performance_ytd}",
            f"  Interest Rate Environment: {macro.interest_rate_environment}",
            "",
            "COMPANY CONTEXT:",
            f"  Revenue Growth YoY: {fin.revenue_growth_yoy}",
            f"  Market Cap: {fin.market_cap}",
        ]
        if macro.macro_summary:
            parts.extend(["", "MACRO SUMMARY:", macro.macro_summary])
        if macro.relevant_policy_signals:
            parts.extend(["", "POLICY SIGNALS:", macro.relevant_policy_signals])
        if ticker_input.additional_context:
            parts.extend(["", "ADDITIONAL CONTEXT:", ticker_input.additional_context])

        parts.append(
            "\n\nAnalyze the macro and sector environment for this company. Provide your assessment as JSON."
        )
        return "\n".join(parts)
