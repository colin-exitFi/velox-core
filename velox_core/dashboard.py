"""Single-page dashboard. FastAPI + vanilla JS + a tiny Chart.js dependency.

Endpoints:
  GET  /                     — the one HTML page
  GET  /api/status           — equity, today's P&L, lite mode flag, kill switch state
  GET  /api/equity-curve     — series of {ts, equity, spy_price} for charting
  GET  /api/scoreboard       — Claude vs GPT vs Consensus P&L attribution
  GET  /api/decisions        — last N consensus decisions
  GET  /api/skips            — last N skipped trades (where models disagreed / low conf)
  GET  /api/positions        — open positions from broker + ratchet state
  POST /api/kill             — flip TRADING_HALTED runtime flag
"""

from __future__ import annotations

import asyncio
import os
import time as _time
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from velox_core import broker, config, state


app = FastAPI(title="Velox Core")

_kill_flag_runtime = bool(config.TRADING_HALTED)


def _check_token(request: Request):
    if not config.DASHBOARD_TOKEN:
        return  # no token = no auth (dev)
    token = request.query_params.get("token") or request.headers.get("x-dashboard-token", "")
    if token != config.DASHBOARD_TOKEN:
        raise HTTPException(status_code=401, detail="invalid token")


@app.get("/api/status")
async def api_status(request: Request):
    _check_token(request)
    try:
        acct = await broker.get_account()
        equity = float(acct.get("equity") or 0)
        last_equity = float(acct.get("last_equity") or equity)
        day_pnl = equity - last_equity
        day_pnl_pct = (day_pnl / last_equity * 100) if last_equity else 0
    except Exception:
        equity = 0
        day_pnl = 0
        day_pnl_pct = 0

    summary = state.trade_summary()
    return {
        "equity": equity,
        "day_pnl": day_pnl,
        "day_pnl_pct": day_pnl_pct,
        "trading_halted": _kill_flag_runtime or config.TRADING_HALTED,
        "summary": summary,
        "config": {
            "position_size_pct": config.POSITION_SIZE_PCT,
            "max_positions": config.MAX_CONCURRENT_POSITIONS,
            "min_consensus_confidence": config.MIN_CONSENSUS_CONFIDENCE,
            "ratchet": {
                "hard_stop_pct": config.RATCHET_HARD_STOP_PCT,
                "activation_pct": config.RATCHET_ACTIVATION_PCT,
                "trail_pct": config.RATCHET_TRAIL_PCT,
                "min_hold_seconds": config.RATCHET_MIN_HOLD_SECONDS,
            },
            "anthropic_model": config.ANTHROPIC_MODEL,
            "openai_model": config.OPENAI_MODEL,
        },
    }


@app.get("/api/equity-curve")
async def api_equity_curve(request: Request):
    _check_token(request)
    return state.equity_history()


@app.get("/api/scoreboard")
async def api_scoreboard(request: Request):
    _check_token(request)
    return state.model_scoreboard()


@app.get("/api/decisions")
async def api_decisions(request: Request, limit: int = 30):
    _check_token(request)
    return state.recent_decisions(limit=min(200, max(1, limit)))


@app.get("/api/skips")
async def api_skips(request: Request, limit: int = 30):
    _check_token(request)
    return state.recent_skips(limit=min(500, max(1, limit)))


@app.get("/api/trades")
async def api_trades(request: Request, limit: int = 50):
    _check_token(request)
    return state.recent_closed_trades(limit=min(200, max(1, limit)))


@app.get("/api/positions")
async def api_positions(request: Request):
    _check_token(request)
    try:
        positions = await broker.get_positions()
    except Exception as e:
        return {"error": str(e), "positions": []}
    out = []
    for p in positions:
        qty = float(p.get("qty") or 0)
        avg = float(p.get("avg_entry_price") or 0)
        current = float(p.get("current_price") or 0)
        unrealized = float(p.get("unrealized_pl") or 0)
        unrealized_pct = float(p.get("unrealized_plpc") or 0) * 100
        out.append({
            "symbol": p.get("symbol"),
            "side": "long" if qty > 0 else "short",
            "qty": qty,
            "entry": avg,
            "current": current,
            "unrealized": unrealized,
            "unrealized_pct": unrealized_pct,
        })
    return {"positions": out}


@app.post("/api/kill")
async def api_kill(request: Request):
    _check_token(request)
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    halted = bool(body.get("halted", True))
    global _kill_flag_runtime
    _kill_flag_runtime = halted
    config.TRADING_HALTED = halted  # propagate to in-process consumers
    state.audit("kill_switch", "warn", f"trading_halted={halted}")
    return {"trading_halted": halted}


@app.get("/api/audit")
async def api_audit(request: Request, limit: int = 50):
    _check_token(request)
    return state.recent_audit(limit=min(500, max(1, limit)))


# ── The single HTML page ───────────────────────────────────────────


HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<title>Velox Core</title>
<style>
* { box-sizing: border-box; }
body {
  font: 14px/1.45 -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #0d1117; color: #c9d1d9; margin: 0; padding: 24px;
}
h1, h2 { color: #f0f6fc; margin: 0 0 8px; font-weight: 600; }
h1 { font-size: 22px; } h2 { font-size: 16px; }
.muted { color: #8b949e; }
.positive { color: #3fb950; } .negative { color: #f85149; }
.row { display: flex; gap: 24px; flex-wrap: wrap; }
.card {
  background: #161b22; border: 1px solid #30363d; border-radius: 8px;
  padding: 18px; margin-bottom: 18px;
}
.card.full { width: 100%; }
.card.half { flex: 1 1 480px; }
.metric { display: inline-block; margin-right: 32px; vertical-align: top; }
.metric .v { font-size: 24px; font-weight: 600; color: #f0f6fc; }
.metric .l { color: #8b949e; font-size: 12px; text-transform: uppercase; letter-spacing: .5px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { padding: 8px 6px; text-align: left; border-bottom: 1px solid #21262d; }
th { color: #8b949e; font-weight: 500; font-size: 11px; text-transform: uppercase; letter-spacing: .5px; }
.tag {
  display: inline-block; padding: 2px 8px; border-radius: 3px;
  font-size: 11px; font-weight: 600;
}
.tag.buy { background: rgba(63,185,80,.15); color: #3fb950; }
.tag.short { background: rgba(248,81,73,.15); color: #f85149; }
.tag.exit { background: rgba(255,166,87,.15); color: #ffa657; }
.tag.hold { background: rgba(139,148,158,.15); color: #8b949e; }
button {
  background: #f85149; color: #fff; border: none; padding: 10px 18px;
  border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px;
}
button.resume { background: #3fb950; }
button:hover { opacity: .85; }
.banner {
  background: rgba(248,81,73,.1); border: 1px solid #f85149;
  color: #f85149; padding: 10px 14px; border-radius: 6px; margin-bottom: 16px;
  display: none; font-weight: 600;
}
.skip-reason { color: #d29922; font-size: 11px; }
.subtle { color: #8b949e; font-size: 11px; }
canvas { max-width: 100%; }
</style>
</head>
<body>

<h1>Velox Core</h1>
<div class="muted" id="subtitle">Loading…</div>

<div id="killBanner" class="banner">⛔ TRADING HALTED — kill switch active. Existing positions still being managed by ratchet.</div>

<div class="card full">
  <div id="metrics"></div>
  <div style="margin-top:14px">
    <button id="killBtn" onclick="toggleKill()">⛔ Halt trading</button>
    <span class="subtle" style="margin-left:12px">Halt blocks new entries. Open positions stay protected by the ratchet.</span>
  </div>
</div>

<div class="row">
  <div class="card half">
    <h2>Equity vs SPY</h2>
    <canvas id="equityChart" height="220"></canvas>
  </div>
  <div class="card half">
    <h2>Claude vs GPT — who's the better trader?</h2>
    <div id="scoreboard">Loading…</div>
  </div>
</div>

<div class="card full">
  <h2>Open positions</h2>
  <table id="positionsTable"><thead>
    <tr><th>Symbol</th><th>Side</th><th>Qty</th><th>Entry</th><th>Current</th><th>P&amp;L</th><th>%</th></tr>
  </thead><tbody></tbody></table>
</div>

<div class="card full">
  <h2>Most recent decisions <span class="subtle">(every consensus event, every skip)</span></h2>
  <table id="decisionsTable"><thead>
    <tr><th>Time</th><th>Symbol</th><th>Claude</th><th>GPT</th><th>Consensus</th><th>Result</th><th>Why</th></tr>
  </thead><tbody></tbody></table>
</div>

<div class="card full">
  <h2>Skip log <span class="subtle">(decisions where the consensus filter blocked a trade — the data ARC didn't measure)</span></h2>
  <table id="skipsTable"><thead>
    <tr><th>Time</th><th>Symbol</th><th>Claude</th><th>GPT</th><th>Skip reason</th></tr>
  </thead><tbody></tbody></table>
</div>

<div class="card full">
  <h2>Closed trades <span class="subtle">(attribution: which model was right)</span></h2>
  <table id="tradesTable"><thead>
    <tr><th>Time</th><th>Symbol</th><th>Side</th><th>Entry</th><th>Exit</th><th>P&amp;L</th><th>%</th><th>Hold</th><th>Reason</th><th>Votes</th></tr>
  </thead><tbody></tbody></table>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>
const TOKEN = new URLSearchParams(location.search).get('token') || '';
const Q = TOKEN ? '?token=' + encodeURIComponent(TOKEN) : '';

async function api(path) {
  const r = await fetch(path + Q);
  if (!r.ok) throw new Error(path + ' ' + r.status);
  return r.json();
}

function fmt(n) { return (n>=0?'+':'') + '$' + Math.abs(n).toFixed(2); }
function pct(n) { return (n>=0?'+':'') + n.toFixed(2) + '%'; }
function dt(ts) { const d = new Date(ts*1000); return d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}); }
function ago(ts) {
  const s = Math.floor(Date.now()/1000 - ts);
  if (s < 60) return s + 's ago';
  if (s < 3600) return Math.floor(s/60) + 'm ago';
  return Math.floor(s/3600) + 'h ago';
}
function actionTag(a) {
  const cls = (a||'HOLD').toLowerCase();
  return `<span class="tag ${cls}">${a||'HOLD'}</span>`;
}

let equityChart;

async function refreshStatus() {
  const s = await api('/api/status');
  const sub = `${s.config.anthropic_model} vs ${s.config.openai_model} · consensus ≥${s.config.min_consensus_confidence}% · ${s.config.position_size_pct}% per position · max ${s.config.max_positions} concurrent · ratchet ${s.config.ratchet.hard_stop_pct}% / +${s.config.ratchet.activation_pct}% / ${s.config.ratchet.trail_pct}% trail`;
  document.getElementById('subtitle').textContent = sub;

  const m = s.summary || {};
  const cls = (n) => n > 0 ? 'positive' : (n < 0 ? 'negative' : '');
  document.getElementById('metrics').innerHTML = `
    <div class="metric"><div class="v">$${(s.equity||0).toFixed(2)}</div><div class="l">Equity</div></div>
    <div class="metric"><div class="v ${cls(s.day_pnl)}">${fmt(s.day_pnl)}</div><div class="l">Day P&L</div></div>
    <div class="metric"><div class="v ${cls(s.day_pnl_pct)}">${pct(s.day_pnl_pct)}</div><div class="l">Day %</div></div>
    <div class="metric"><div class="v">${m.total_trades||0}</div><div class="l">Closed Trades</div></div>
    <div class="metric"><div class="v ${cls(m.total_pnl)}">${fmt(m.total_pnl||0)}</div><div class="l">Total P&L</div></div>
    <div class="metric"><div class="v">${(m.win_rate||0).toFixed(0)}%</div><div class="l">Win Rate</div></div>
  `;
  const banner = document.getElementById('killBanner');
  const btn = document.getElementById('killBtn');
  if (s.trading_halted) {
    banner.style.display = 'block';
    btn.textContent = '✅ Resume trading'; btn.classList.add('resume');
  } else {
    banner.style.display = 'none';
    btn.textContent = '⛔ Halt trading'; btn.classList.remove('resume');
  }
}

async function refreshEquity() {
  const data = await api('/api/equity-curve');
  if (!data.length) return;
  const labels = data.map(d => new Date(d.timestamp*1000).toLocaleString());
  const equityVals = data.map(d => d.equity);
  // Normalize SPY to start at the same equity for visual comparison
  const firstEq = equityVals[0] || 1;
  const firstSpy = data.find(d => d.spy)?.spy || 1;
  const spyVals = data.map(d => d.spy ? (d.spy / firstSpy * firstEq) : null);
  const ctx = document.getElementById('equityChart').getContext('2d');
  const cfg = {
    type: 'line',
    data: { labels, datasets: [
      { label: 'Velox', data: equityVals, borderColor: '#3fb950', tension: .25, pointRadius: 0 },
      { label: 'SPY (normalized)', data: spyVals, borderColor: '#8b949e', borderDash: [4,4], tension: .25, pointRadius: 0 },
    ]},
    options: {
      animation: false, responsive: true, plugins: { legend: { labels: { color: '#c9d1d9' } } },
      scales: {
        x: { ticks: { color: '#8b949e', maxTicksLimit: 8 }, grid: { color: '#21262d' } },
        y: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } },
      },
    },
  };
  if (equityChart) { equityChart.data = cfg.data; equityChart.update(); }
  else equityChart = new Chart(ctx, cfg);
}

async function refreshScoreboard() {
  const sb = await api('/api/scoreboard');
  const row = (label, s, color) => `
    <div style="margin-bottom:14px">
      <div style="color:${color}; font-weight:600">${label}</div>
      <div class="metric" style="margin-right:18px"><div class="v">${s.trades}</div><div class="l">Trades</div></div>
      <div class="metric" style="margin-right:18px"><div class="v">${s.wins}/${s.trades-s.wins}</div><div class="l">W/L</div></div>
      <div class="metric" style="margin-right:18px"><div class="v">${s.win_rate.toFixed(0)}%</div><div class="l">Win %</div></div>
      <div class="metric"><div class="v ${s.total_pnl>=0?'positive':'negative'}">${fmt(s.total_pnl)}</div><div class="l">P&L</div></div>
    </div>`;
  document.getElementById('scoreboard').innerHTML =
    row('Claude (when right side)', sb.claude, '#bf6d2c') +
    row('GPT (when right side)', sb.gpt, '#2c8bbf') +
    row('Both agreed (consensus)', sb.consensus, '#3fb950');
}

async function refreshPositions() {
  const data = await api('/api/positions');
  const tbody = document.querySelector('#positionsTable tbody');
  if (!data.positions.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="muted">No open positions</td></tr>';
    return;
  }
  tbody.innerHTML = data.positions.map(p => `
    <tr>
      <td><strong>${p.symbol}</strong></td>
      <td>${actionTag(p.side === 'long' ? 'BUY' : 'SHORT')}</td>
      <td>${p.qty}</td>
      <td>$${p.entry.toFixed(2)}</td>
      <td>$${p.current.toFixed(2)}</td>
      <td class="${p.unrealized>=0?'positive':'negative'}">${fmt(p.unrealized)}</td>
      <td class="${p.unrealized_pct>=0?'positive':'negative'}">${pct(p.unrealized_pct)}</td>
    </tr>`).join('');
}

async function refreshDecisions() {
  const data = await api('/api/decisions?limit=30');
  const tbody = document.querySelector('#decisionsTable tbody');
  if (!data.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="muted">No decisions yet — first session will populate this.</td></tr>';
    return;
  }
  tbody.innerHTML = data.map(d => {
    const result = d.executed ? `<span class="positive">EXECUTED</span>` : `<span class="muted">skipped</span>`;
    const why = d.skip_reason || '—';
    return `<tr>
      <td>${dt(d.timestamp)}</td>
      <td><strong>${d.symbol}</strong></td>
      <td>${actionTag(d.claude_action)} <span class="subtle">${(d.claude_confidence||0).toFixed(0)}%</span></td>
      <td>${actionTag(d.gpt_action)} <span class="subtle">${(d.gpt_confidence||0).toFixed(0)}%</span></td>
      <td>${actionTag(d.consensus_action)} <span class="subtle">${(d.consensus_confidence||0).toFixed(0)}%</span></td>
      <td>${result}</td>
      <td class="skip-reason">${why}</td>
    </tr>`;
  }).join('');
}

async function refreshSkips() {
  const data = await api('/api/skips?limit=30');
  const tbody = document.querySelector('#skipsTable tbody');
  if (!data.length) {
    tbody.innerHTML = '<tr><td colspan="5" class="muted">No skips yet.</td></tr>';
    return;
  }
  tbody.innerHTML = data.map(d => `
    <tr>
      <td>${dt(d.timestamp)}</td>
      <td><strong>${d.symbol}</strong></td>
      <td>${actionTag(d.claude_action)} <span class="subtle">${(d.claude_confidence||0).toFixed(0)}%</span></td>
      <td>${actionTag(d.gpt_action)} <span class="subtle">${(d.gpt_confidence||0).toFixed(0)}%</span></td>
      <td class="skip-reason">${d.skip_reason||'—'}</td>
    </tr>`).join('');
}

async function refreshTrades() {
  const data = await api('/api/trades?limit=30');
  const tbody = document.querySelector('#tradesTable tbody');
  if (!data.length) {
    tbody.innerHTML = '<tr><td colspan="10" class="muted">No closed trades yet.</td></tr>';
    return;
  }
  tbody.innerHTML = data.map(t => {
    const hold = t.hold_seconds ? Math.round(t.hold_seconds/60) + 'm' : '—';
    const pnlClass = (t.pnl||0) >= 0 ? 'positive' : 'negative';
    return `<tr>
      <td>${dt(t.exit_time||t.entry_time)}</td>
      <td><strong>${t.symbol}</strong></td>
      <td>${actionTag(t.side === 'long' ? 'BUY' : 'SHORT')}</td>
      <td>$${(t.entry_price||0).toFixed(2)}</td>
      <td>$${(t.exit_price||0).toFixed(2)}</td>
      <td class="${pnlClass}">${fmt(t.pnl||0)}</td>
      <td class="${pnlClass}">${pct(t.pnl_pct||0)}</td>
      <td>${hold}</td>
      <td class="subtle">${t.exit_reason||''}</td>
      <td class="subtle">C:${t.claude_vote||'?'} · G:${t.gpt_vote||'?'}</td>
    </tr>`;
  }).join('');
}

async function toggleKill() {
  const s = await api('/api/status');
  const r = await fetch('/api/kill' + Q, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({halted: !s.trading_halted}),
  });
  if (r.ok) refreshAll();
}

async function refreshAll() {
  try { await Promise.all([refreshStatus(), refreshEquity(), refreshScoreboard(), refreshPositions(), refreshDecisions(), refreshSkips(), refreshTrades()]); }
  catch (e) { console.error(e); }
}

refreshAll();
setInterval(refreshAll, 30000);
</script>

</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    _check_token(request)
    return HTMLResponse(content=HTML)


def serve():
    import uvicorn
    uvicorn.run(
        "velox_core.dashboard:app",
        host=config.DASHBOARD_HOST,
        port=config.DASHBOARD_PORT,
        log_level=config.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    serve()
