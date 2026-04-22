"""The 40-ticker universe Velox Core trades.

Curated for legibility and regime balance:
- 3 broad-market ETFs as benchmarks/hedges
- 10 mega-cap tech (lowest spreads, highest liquidity)
- 10 AI-narrative mid-caps (where active management can add value)
- 10 high-beta narrative names (where consensus matters most)
- 7 defensives (gives the model real choices when regime shifts risk-off)

Total: 40 tickers. Re-evaluate quarterly, not weekly.
"""

ETFS = ["SPY", "QQQ", "IWM"]

MEGA_CAP_TECH = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "META",
    "AMZN", "AVGO", "TSLA", "AMD", "TSM",
]

AI_NARRATIVE_MIDCAP = [
    "PLTR", "SNOW", "CRWD", "DDOG", "NET",
    "MDB", "CRM", "ORCL", "NOW", "ANET",
]

HIGH_BETA_NARRATIVE = [
    "SMCI", "ARM", "COIN", "HOOD", "MSTR",
    "RIVN", "LCID", "ENPH", "FSLR", "SEDG",
]

DEFENSIVE = [
    "JNJ", "PG", "KO", "WMT", "COST",
    "XLU", "XLP",
]

UNIVERSE = ETFS + MEGA_CAP_TECH + AI_NARRATIVE_MIDCAP + HIGH_BETA_NARRATIVE + DEFENSIVE

CATEGORY_OF = {
    **{s: "etf" for s in ETFS},
    **{s: "mega_cap_tech" for s in MEGA_CAP_TECH},
    **{s: "ai_narrative" for s in AI_NARRATIVE_MIDCAP},
    **{s: "high_beta" for s in HIGH_BETA_NARRATIVE},
    **{s: "defensive" for s in DEFENSIVE},
}

assert len(UNIVERSE) == 40, f"Universe must be exactly 40 tickers, got {len(UNIVERSE)}"
assert len(set(UNIVERSE)) == 40, "Universe contains duplicates"
