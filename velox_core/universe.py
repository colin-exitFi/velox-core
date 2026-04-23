"""The Velox Core anchor universe.

A larger, sector-balanced list of liquid US equities. Every session evaluates
the full anchor list. The scanner module adds a small dynamic overlay on top
(today's most-active names) so the bot fishes in a real-sized pond, not a
40-name puddle.

Composition (~120 anchors):
  * 4 broad-market ETFs as benchmarks/hedges
  * S&P 100 mega/large caps for liquidity floor
  * Sector-leading mid-caps (AI, semis, fintech, biotech, energy, consumer)
  * Defensive sleeve so the bot has somewhere to hide when risk_off
"""

ETFS = [
    "SPY", "QQQ", "IWM", "DIA",
]

# S&P 100 (Top mega/large-caps with deep liquidity).
SP100 = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "BRK.B", "WMT",
    "JPM", "LLY", "V", "ORCL", "MA", "XOM", "COST", "PG", "JNJ", "HD",
    "NFLX", "BAC", "ABBV", "CVX", "KO", "CRM", "MRK", "AMD", "PEP", "TMO",
    "LIN", "WFC", "CSCO", "ACN", "MCD", "ABT", "GE", "ADBE", "DIS", "PM",
    "VZ", "INTU", "TXN", "CAT", "AMGN", "QCOM", "IBM", "PFE", "DHR", "GS",
    "NOW", "BX", "MS", "AXP", "RTX", "ISRG", "CMCSA", "T", "AMAT", "BLK",
    "NEE", "SPGI", "BKNG", "PGR", "C", "UBER", "HON", "TJX", "VRTX", "BSX",
    "PLD", "ETN", "DE",
]

# Mid-cap leaders by theme (where active management has a real shot).
MID_CAP_AI_SOFTWARE = [
    "PLTR", "SNOW", "CRWD", "DDOG", "NET", "MDB", "ANET", "PANW", "FTNT", "ZS",
    "OKTA", "TEAM", "CFLT",
]

MID_CAP_SEMIS = [
    "SMCI", "ARM", "MU", "ASML", "LRCX", "KLAC", "MRVL", "ON",
]

MID_CAP_FINTECH_NEWAGE = [
    "COIN", "HOOD", "MSTR", "SOFI", "SQ", "PYPL",
]

MID_CAP_HIGH_BETA = [
    "RIVN", "LCID", "ENPH", "FSLR", "SEDG", "DKNG", "RBLX", "U",
]

MID_CAP_BIOTECH = [
    "REGN", "GILD", "MRNA", "BIIB", "ALNY",
]

MID_CAP_CONSUMER_TRAVEL = [
    "ABNB", "MAR", "BKNG", "DASH", "LULU", "NKE",
]

DEFENSIVE = [
    "XLU", "XLP", "XLE",
]

UNIVERSE = sorted(set(
    ETFS + SP100
    + MID_CAP_AI_SOFTWARE + MID_CAP_SEMIS + MID_CAP_FINTECH_NEWAGE
    + MID_CAP_HIGH_BETA + MID_CAP_BIOTECH + MID_CAP_CONSUMER_TRAVEL + DEFENSIVE
))

CATEGORY_OF = {}
for s in ETFS:                    CATEGORY_OF[s] = "etf"
for s in SP100:                   CATEGORY_OF.setdefault(s, "sp100")
for s in MID_CAP_AI_SOFTWARE:     CATEGORY_OF[s] = "ai_software"
for s in MID_CAP_SEMIS:           CATEGORY_OF[s] = "semis"
for s in MID_CAP_FINTECH_NEWAGE:  CATEGORY_OF[s] = "fintech_new_age"
for s in MID_CAP_HIGH_BETA:       CATEGORY_OF[s] = "high_beta"
for s in MID_CAP_BIOTECH:         CATEGORY_OF[s] = "biotech"
for s in MID_CAP_CONSUMER_TRAVEL: CATEGORY_OF[s] = "consumer_travel"
for s in DEFENSIVE:               CATEGORY_OF[s] = "defensive"

# Backwards compat — old code referenced these as the only categories.
MEGA_CAP_TECH = [s for s in SP100 if s in (
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "AVGO", "TSLA", "AMD",
)]
AI_NARRATIVE_MIDCAP = MID_CAP_AI_SOFTWARE
HIGH_BETA_NARRATIVE = MID_CAP_HIGH_BETA

assert len(UNIVERSE) >= 100, f"Universe should be ~120 tickers, got {len(UNIVERSE)}"
assert len(set(UNIVERSE)) == len(UNIVERSE), "Universe contains duplicates"
