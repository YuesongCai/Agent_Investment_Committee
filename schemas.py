"""Shared data schemas for the AI Investment Committee."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# --- Enums ---

class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Recommendation(str, Enum):
    STRONG_BUY = "Strong Buy"
    BUY = "Buy"
    HOLD = "Hold"
    SELL = "Sell"
    STRONG_SELL = "Strong Sell"


class AgentRole(str, Enum):
    FUNDAMENTALS = "fundamentals"
    VALUATION = "valuation"
    SENTIMENT = "sentiment"
    TECHNICAL = "technical"
    MACRO = "macro"


# --- Input schemas ---

class FinancialData(BaseModel):
    revenue_ttm: Optional[float] = None
    net_income_ttm: Optional[float] = None
    ebitda_ttm: Optional[float] = None
    free_cash_flow_ttm: Optional[float] = None
    total_debt: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    shares_outstanding: Optional[float] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    revenue_growth_yoy: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    roe: Optional[float] = None
    roic: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None


class PriceData(BaseModel):
    current_price: Optional[float] = None
    price_52w_high: Optional[float] = None
    price_52w_low: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    rsi_14: Optional[float] = None
    avg_volume_30d: Optional[float] = None
    beta: Optional[float] = None
    ytd_return: Optional[float] = None
    one_year_return: Optional[float] = None


class SentimentData(BaseModel):
    short_interest_pct: Optional[float] = None
    analyst_buy_pct: Optional[float] = None
    analyst_hold_pct: Optional[float] = None
    analyst_sell_pct: Optional[float] = None
    consensus_target_price: Optional[float] = None
    insider_net_shares_12m: Optional[float] = None
    news_sentiment_summary: Optional[str] = None
    options_put_call_ratio: Optional[float] = None


class MacroData(BaseModel):
    sector: Optional[str] = None
    industry: Optional[str] = None
    macro_summary: Optional[str] = None
    sector_performance_ytd: Optional[float] = None
    interest_rate_environment: Optional[str] = None
    relevant_policy_signals: Optional[str] = None


class TickerInput(BaseModel):
    """Complete input bundle for a single ticker analysis."""
    ticker: str
    company_name: str
    data_date: date
    earnings_transcript_summary: Optional[str] = None
    financials: FinancialData = Field(default_factory=FinancialData)
    price: PriceData = Field(default_factory=PriceData)
    sentiment: SentimentData = Field(default_factory=SentimentData)
    macro: MacroData = Field(default_factory=MacroData)
    additional_context: Optional[str] = None

    @field_validator("ticker")
    @classmethod
    def ticker_uppercase(cls, v: str) -> str:
        return v.upper().strip()


# --- Output schemas ---

class AgentOutput(BaseModel):
    """Structured output from each specialist analyst agent."""
    agent_role: AgentRole
    score: int = Field(ge=1, le=10)
    thesis: str
    bull_case: str
    bear_case: str
    confidence: Confidence
    key_data_points: list[str] = Field(
        default_factory=list,
        description="Specific data points cited to support the thesis",
    )

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: int) -> int:
        if not 1 <= v <= 10:
            raise ValueError("Score must be between 1 and 10")
        return v


class DebateExchange(BaseModel):
    """Record of a single debate exchange between two agents."""
    agent_a: AgentRole
    agent_b: AgentRole
    score_delta: int
    agent_a_rebuttal: str
    agent_b_rebuttal: str
    resolved: bool
    resolution_note: str = ""


class DissentRecord(BaseModel):
    """Unresolved minority position."""
    agent_role: AgentRole
    original_score: int
    post_debate_score: Optional[int] = None
    position: str


class AgentScoreBreakdown(BaseModel):
    agent_role: AgentRole
    score: int
    confidence: Confidence
    one_line_thesis: str


class DecisionPacket(BaseModel):
    """Final output of an investment committee run."""
    ticker: str
    company_name: str
    run_date: str
    data_vintage: str
    composite_score: float
    recommendation: Recommendation
    consensus_narrative: str
    agent_scores: list[AgentScoreBreakdown]
    debates: list[DebateExchange]
    dissent_log: list[DissentRecord]
    action_plan: str
    cost_estimate_usd: float = 0.0
    qa_flags: list[str] = Field(default_factory=list)


class WatchlistSummary(BaseModel):
    """Summary index for a watchlist run."""
    run_date: str
    tickers_analyzed: int
    total_cost_usd: float
    rankings: list[dict]
    flagged_disagreements: list[dict]


# --- Agent weights config ---

DEFAULT_AGENT_WEIGHTS: dict[AgentRole, float] = {
    AgentRole.FUNDAMENTALS: 0.25,
    AgentRole.VALUATION: 0.25,
    AgentRole.SENTIMENT: 0.15,
    AgentRole.TECHNICAL: 0.15,
    AgentRole.MACRO: 0.20,
}
