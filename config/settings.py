"""Configuration settings for the AI Investment Committee."""

from __future__ import annotations

import os

# LLM settings
LLM_MODEL = "claude-sonnet-4-20250514"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Cost settings (per 1M tokens, approximate for Claude Sonnet)
INPUT_COST_PER_1M = 3.00
OUTPUT_COST_PER_1M = 15.00
MAX_COST_PER_RUN = 0.50

# Token limits for context trimming
MAX_INPUT_TOKENS_PER_AGENT = 4000
MAX_EARNINGS_TRANSCRIPT_TOKENS = 3000

# Orchestrator settings
DEBATE_SCORE_THRESHOLD = 3  # score delta to trigger debate
MAX_DEBATE_ROUNDS = 1
HUMAN_REVIEW_TRIGGER_THRESHOLD = 3  # number of agents disagreeing to flag for human review
LOW_DATA_QUALITY_THRESHOLD = 3  # minimum required non-null fields in financials

# Output directories
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
RUN_LOG_PATH = os.path.join(OUTPUT_DIR, "run_log.json")
