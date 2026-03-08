# AI Investment Committee

A debate-driven, multi-agent equity research system that replicates how professional investment teams work -- multiple specialists with different analytical lenses who disagree, reconcile, and commit to a view.

## How It Works

```
                         +-----------------+
                         |  PM Orchestrator|
                         +--------+--------+
                                  |
             Collect scores, detect disagreements,
             run debate rounds, synthesize decision
                                  |
          +-------+-------+-------+-------+-------+
          |       |       |       |       |       |
       Fundamentals  Valuation  Sentiment  Technical  Macro
        Analyst     Analyst     Analyst     Analyst   Analyst
          |       |       |       |       |       |
       score 1-10  score 1-10  score 1-10  score 1-10  score 1-10
          +-------+-------+-------+-------+-------+
                                  |
                         Decision Packet
                      (JSON + Markdown report)
```

Five specialist analyst agents each evaluate a company from their domain. The PM orchestrator collects their scores, identifies disagreements (any pair with a score delta >= 3), forces a rebuttal debate round, then produces a final decision packet with composite score, recommendation, consensus narrative, and a logged dissent record for unresolved minority positions.

## Quick Start

### Prerequisites

- Python 3.11+
- Anthropic API key

### Installation

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-api-key"
```

### Run Analysis on a Single Ticker

```bash
python cli.py analyze data/fixtures/nvda.json
```

### Run a Watchlist (Batch Mode)

```bash
python cli.py watchlist config/watchlist.json
```

### Consistency Test

Runs the same ticker twice with identical inputs and checks score drift:

```bash
python cli.py consistency-test data/fixtures/nvda.json
```

## Agent Roster

| Agent | Mandate | Score Meaning |
|-------|---------|---------------|
| **Fundamentals** | Business quality, earnings trajectory, competitive moat | 1 = structurally impaired, 10 = exceptional quality compounder |
| **Valuation** | DCF, EV/EBITDA comps, margin of safety | 1 = extreme overvaluation, 10 = deep undervaluation |
| **Sentiment** | Crowding risk, short interest, options flow, media tone | 1 = extreme negative positioning, 10 = strong positive setup |
| **Technical** | Price action, momentum, entry/exit signals | 1 = severe breakdown, 10 = strong uptrend at key support |
| **Macro** | Macro tailwinds/headwinds, sector rotation | 1 = severe headwinds, 10 = strong tailwinds |

Default weights: Fundamentals (25%), Valuation (25%), Macro (20%), Sentiment (15%), Technical (15%). Configurable via watchlist config or code.

## Orchestration Logic

1. **Collect** -- All 5 agents analyze the ticker independently
2. **Detect** -- Any agent pair with score delta >= 3 triggers a debate
3. **Debate** -- Each disagreeing agent rebuts the other's position; they can update their scores
4. **Reconcile** -- If scores converge, the debate is marked resolved; otherwise it is logged as dissent
5. **Synthesize** -- Orchestrator produces composite score, recommendation, consensus narrative, and action plan
6. **QA** -- Output is validated for schema conformance, claim hygiene, and flagged for human review if needed

### Human Review Triggers

The orchestrator flags for human review when:
- 3+ agents have unresolved disagreements
- Majority of agents report low confidence
- Data quality checks fail

## Input Format

Each ticker is a JSON file with this structure:

```json
{
  "ticker": "NVDA",
  "company_name": "NVIDIA Corporation",
  "data_date": "2026-03-01",
  "earnings_transcript_summary": "...",
  "financials": {
    "revenue_ttm": 130000000000,
    "net_income_ttm": 72000000000,
    "pe_ratio": 38.5,
    "revenue_growth_yoy": 0.78,
    ...
  },
  "price": {
    "current_price": 950.00,
    "sma_50": 910.0,
    "rsi_14": 62.0,
    ...
  },
  "sentiment": {
    "short_interest_pct": 1.2,
    "analyst_buy_pct": 0.88,
    "news_sentiment_summary": "...",
    ...
  },
  "macro": {
    "sector": "Technology",
    "interest_rate_environment": "Rates stable at 4.25-4.50%",
    "macro_summary": "...",
    ...
  }
}
```

See `data/fixtures/` for complete examples (NVDA, AAPL, BABA).

## Decision Packet Output

Each run produces:

- **JSON** -- Machine-readable, stored in `output/` for logging and cross-run comparison
- **Markdown** -- Human-readable report with score tables, debate logs, and action plans

### Fields

| Field | Description |
|-------|-------------|
| Composite Score | Weighted average of 5 agent scores (1-10) |
| Recommendation | Strong Buy / Buy / Hold / Sell / Strong Sell |
| Consensus Narrative | 2-3 paragraph synthesis by the orchestrator |
| Agent Score Breakdown | Per-agent score, confidence, and one-line thesis |
| Debate Log | Which agents disagreed, rebuttals, and resolution status |
| Dissent Log | Unresolved minority positions |
| Action Plan | Suggested next research steps and monitoring triggers |
| QA Flags | Schema violations, claim hygiene issues, human review triggers |
| Cost Estimate | Estimated API cost for the run |

## QA & Evaluation

| Check | What It Does |
|-------|--------------|
| Schema validation | Verifies all required fields are populated and conform to spec |
| Claim hygiene | Flags agent outputs with no cited data points |
| Consistency test | Runs same ticker twice, alerts if score delta > 1 |
| Run log | Every run appends results to `output/run_log.json` for tracking over time |

## Cost Controls

- Target: **< $0.50 per ticker** with Claude Sonnet
- Agent prompts and inputs are capped at configurable token limits (`MAX_INPUT_TOKENS_PER_AGENT`)
- Per-run cost is estimated and logged
- Batch cost printed to console after watchlist runs

## Configuration

Key settings in `config/settings.py`:

```python
LLM_MODEL = "claude-sonnet-4-20250514"
DEBATE_SCORE_THRESHOLD = 3          # score delta to trigger debate
MAX_DEBATE_ROUNDS = 1               # rebuttal cycles before forcing decision
MAX_INPUT_TOKENS_PER_AGENT = 4000   # context trimming budget
MAX_COST_PER_RUN = 0.50             # cost ceiling per ticker
```

Agent weights can be overridden per-watchlist in `config/watchlist.json`.

## Project Structure

```
.
├── agents/
│   ├── base.py              # Base agent class with LLM interaction
│   ├── fundamentals.py      # Business quality & earnings analyst
│   ├── valuation.py         # DCF & comps analyst
│   ├── sentiment.py         # Positioning & crowding analyst
│   ├── technical.py         # Price action & momentum analyst
│   └── macro.py             # Macro & sector analyst
├── config/
│   ├── settings.py          # Model, cost, and orchestration settings
│   └── watchlist.json       # Example watchlist configuration
├── data/
│   ├── fixtures/            # Test input bundles (NVDA, AAPL, BABA)
│   └── input_validator.py   # Input validation and quality checks
├── qa/
│   └── validator.py         # Schema validation, claim hygiene, consistency
├── cli.py                   # CLI entry point (analyze, watchlist, consistency-test)
├── orchestrator.py          # PM orchestrator with debate logic
├── schemas.py               # Pydantic models for all data structures
├── cost_tracker.py          # API cost estimation and logging
├── report.py                # JSON and Markdown report generation
├── requirements.txt
└── pyproject.toml
```

## References

- AlphaAgents (2025) -- BlackRock researchers on multi-agent investment workflows
- TradingAgents (2024) -- Multi-agent debate structure for trading decisions
- CrewAI documentation -- https://docs.crewai.com
- Anthropic API documentation -- https://docs.anthropic.com
