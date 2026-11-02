"""Hypothetical paper backtest on a synthetic index path. No orders, no broker.

Rule (educational): go long one index-futures-equivalent lot when PCR > 1.1 and the
close is above its 20-day average; go short when PCR < 0.9 and below it; else flat.
Positions are decided on day t's close and earn day t+1's move, minus a flat cost.
"""
from __future__ import annotations

COST_PER_SWITCH = 40.0  # rupees, illustrative


def sma(values: list[float], n: int) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(values)):
        out.append(sum(values[i - n + 1:i + 1]) / n if i >= n - 1 else None)
    return out


def run(path: list[dict], lot: int) -> dict:
    closes = [p["close"] for p in path]
    avg = sma(closes, 20)
    pos = 0
    equity = 0.0
    curve, positions, trades = [], [], 0
    peak, max_dd = 0.0, 0.0
    wins = losses = 0
    for i in range(len(path) - 1):
        target = 0
        if avg[i] is not None:
            if path[i]["pcr"] > 1.1 and closes[i] > avg[i]:
                target = 1
            elif path[i]["pcr"] < 0.9 and closes[i] < avg[i]:
                target = -1
        if target != pos:
            equity -= COST_PER_SWITCH
            trades += 1
            pos = target
        pnl = pos * (closes[i + 1] - closes[i]) * lot
        if pos:
            wins += pnl > 0
            losses += pnl < 0
        equity += pnl
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)
        curve.append(round(equity, 2))
        positions.append(pos)
    days_in = wins + losses
    return {
        "equity": curve, "positions": positions, "final_pnl": round(equity, 2),
        "max_drawdown": round(max_dd, 2), "switches": trades,
        "hit_rate": round(wins / days_in, 3) if days_in else None,
        "days_in_market": days_in, "hypothetical": True,
    }
