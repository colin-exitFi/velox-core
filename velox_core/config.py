"""Runtime configuration loaded from .env."""

import os
from pathlib import Path
from dotenv import load_dotenv

_root = Path(__file__).resolve().parent.parent
load_dotenv(_root / ".env", override=True)


def _str(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


def _int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


def _bool(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return str(raw).strip().lower() in ("true", "1", "yes", "on")


# ── Alpaca ─────────────────────────────────────────────────────────
ALPACA_API_KEY = _str("ALPACA_API_KEY")
ALPACA_SECRET_KEY = _str("ALPACA_SECRET_KEY")
ALPACA_PAPER = _bool("ALPACA_PAPER", True)
ALPACA_BASE_URL = (
    "https://paper-api.alpaca.markets" if ALPACA_PAPER else "https://api.alpaca.markets"
)
ALPACA_DATA_URL = "https://data.alpaca.markets"

# ── AI providers ───────────────────────────────────────────────────
ANTHROPIC_API_KEY = _str("ANTHROPIC_API_KEY")
OPENAI_API_KEY = _str("OPENAI_API_KEY")
PERPLEXITY_API_KEY = _str("PERPLEXITY_API_KEY")
# Defaults updated 2026-04-22 to current top-tier models.
# Claude Opus 4.7 + GPT-5.4 are the "voters" in the consensus.
# Perplexity sonar-pro is the "context layer" — runs once per session, injects
# a real-time market brief into both voters' prompts.
ANTHROPIC_MODEL = _str("ANTHROPIC_MODEL", "claude-opus-4-7")
OPENAI_MODEL = _str("OPENAI_MODEL", "gpt-5.4")
PERPLEXITY_MODEL = _str("PERPLEXITY_MODEL", "sonar-pro")
MARKET_BRIEF_ENABLED = _bool("MARKET_BRIEF_ENABLED", bool(PERPLEXITY_API_KEY))

# ── Trading ────────────────────────────────────────────────────────
POSITION_SIZE_PCT = _float("POSITION_SIZE_PCT", 4.0)
MAX_CONCURRENT_POSITIONS = _int("MAX_CONCURRENT_POSITIONS", 8)
MIN_CONSENSUS_CONFIDENCE = _float("MIN_CONSENSUS_CONFIDENCE", 60)
PAPER_STARTING_EQUITY = _float("PAPER_STARTING_EQUITY", 25000)

# Conviction-based sizing: scale linearly between MIN_PCT (at MIN_CONFIDENCE)
# and MAX_PCT (at 100% confidence). Higher conviction → bigger position.
# Inherited learning from velox-classic: don't size all entries equally.
POSITION_SIZE_MIN_PCT = _float("POSITION_SIZE_MIN_PCT", 3.0)
POSITION_SIZE_MAX_PCT = _float("POSITION_SIZE_MAX_PCT", 6.0)

# Concentration guard: cap exposure to any one category in universe.py.
# Prevents the bot from going 32% AI mid-cap on a single bullish session.
MAX_CATEGORY_EXPOSURE_PCT = _float("MAX_CATEGORY_EXPOSURE_PCT", 35.0)

# Daily review: Claude reads the day's data and writes an editorial summary
# at 16:00 ET. Inherited from velox-classic's auto-review pattern.
DAILY_REVIEW_ENABLED = _bool("DAILY_REVIEW_ENABLED", bool(ANTHROPIC_API_KEY))
DAILY_REVIEW_HOUR_ET = _int("DAILY_REVIEW_HOUR_ET", 16)
DAILY_REVIEW_MIN_ET = _int("DAILY_REVIEW_MIN_ET", 0)

# ── Ratchet (proven values from velox-classic 397-trade dataset) ───
RATCHET_HARD_STOP_PCT = _float("RATCHET_HARD_STOP_PCT", -0.75)
RATCHET_ACTIVATION_PCT = _float("RATCHET_ACTIVATION_PCT", 0.30)
RATCHET_TRAIL_PCT = _float("RATCHET_TRAIL_PCT", 1.00)
RATCHET_INITIAL_FLOOR_PCT = _float("RATCHET_INITIAL_FLOOR_PCT", 0.10)
RATCHET_MIN_HOLD_SECONDS = _int("RATCHET_MIN_HOLD_SECONDS", 120)

# ── Dashboard ──────────────────────────────────────────────────────
DASHBOARD_HOST = _str("DASHBOARD_HOST", "0.0.0.0")
DASHBOARD_PORT = _int("DASHBOARD_PORT", 8422)
DASHBOARD_TOKEN = _str("DASHBOARD_TOKEN", "")

# ── Operational ────────────────────────────────────────────────────
TRADING_HALTED = _bool("TRADING_HALTED", False)
LOG_LEVEL = _str("LOG_LEVEL", "INFO")

DATA_DIR = _root / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "velox_core.db"
EQUITY_HISTORY_PATH = DATA_DIR / "equity_history.json"
