"""Option-chain analytics: PCR, max pain, OI build-up, IV/Greeks summary, signal explainer."""
from __future__ import annotations

DISCLAIMER = "Educational, not advice. Synthetic data. No trading."


def pcr(chain: dict) -> dict:
    put_oi = sum(r["PE"]["oi"] for r in chain["rows"])
    call_oi = sum(r["CE"]["oi"] for r in chain["rows"])
    put_vol = sum(r["PE"]["volume"] for r in chain["rows"])
    call_vol = sum(r["CE"]["volume"] for r in chain["rows"])
    return {
        "oi_pcr": round(put_oi / call_oi, 3) if call_oi else None,
        "volume_pcr": round(put_vol / call_vol, 3) if call_vol else None,
        "put_oi": put_oi, "call_oi": call_oi,
    }


def max_pain(chain: dict) -> float:
    """Strike at which total intrinsic value paid to option holders is smallest."""
    strikes = [r["strike"] for r in chain["rows"]]
    best, best_val = None, None
    for settle in strikes:
        pain = 0.0
        for r in chain["rows"]:
            pain += max(0.0, settle - r["strike"]) * r["CE"]["oi"]
            pain += max(0.0, r["strike"] - settle) * r["PE"]["oi"]
        if best_val is None or pain < best_val:
            best, best_val = settle, pain
    return best


def classify_buildup(price_change: float, oi_change: float) -> str:
    """Standard four-way price/OI classification."""
    if oi_change >= 0:
        return "Long build-up" if price_change >= 0 else "Short build-up"
    return "Short covering" if price_change >= 0 else "Long unwinding"


def oi_buildup(chain: dict) -> list[dict]:
    out = []
    for r in chain["rows"]:
        for kind in ("CE", "PE"):
            leg = r[kind]
            dp = leg["ltp"] - leg["prev_ltp"]
            doi = leg["oi"] - leg["prev_oi"]
            out.append({"strike": r["strike"], "kind": kind, "price_change": round(dp, 2),
                        "oi_change": doi, "label": classify_buildup(dp, doi)})
    return out


def buildup_counts(chain: dict) -> dict:
    counts: dict = {}
    for b in oi_buildup(chain):
        key = f'{b["kind"]} {b["label"]}'
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def iv_greeks_summary(chain: dict) -> dict:
    atm_row = next(r for r in chain["rows"] if r["strike"] == chain["atm"])
    step = chain["step"]
    rows = {r["strike"]: r for r in chain["rows"]}
    # 25-delta-ish proxy: 4 strikes OTM each side
    otm_put = rows.get(chain["atm"] - 4 * step)
    otm_call = rows.get(chain["atm"] + 4 * step)
    skew = round(otm_put["PE"]["iv"] - otm_call["CE"]["iv"], 2) if otm_put and otm_call else None
    lot = chain["lot"]
    straddle = atm_row["CE"]["ltp"] + atm_row["PE"]["ltp"]
    return {
        "atm_strike": chain["atm"],
        "atm_iv": round((atm_row["CE"]["iv"] + atm_row["PE"]["iv"]) / 2, 2),
        "skew_put_minus_call": skew,
        "atm_straddle": round(straddle, 2),
        "implied_move_pct": round(straddle / chain["spot"] * 100, 2),
        "atm_call_greeks": {k: atm_row["CE"][k] for k in ("delta", "gamma", "vega", "theta")},
        "atm_put_greeks": {k: atm_row["PE"][k] for k in ("delta", "gamma", "vega", "theta")},
        "straddle_theta_per_lot": round((atm_row["CE"]["theta"] + atm_row["PE"]["theta"]) * lot, 2),
        "straddle_vega_per_lot": round((atm_row["CE"]["vega"] + atm_row["PE"]["vega"]) * lot, 2),
    }


def explain_signal(chain: dict) -> dict:
    """Transparent, rule-based 'tilt' with every factor shown. Educational only."""
    p = pcr(chain)
    mp = max_pain(chain)
    s = iv_greeks_summary(chain)
    spot = chain["spot"]
    factors = []

    oi_pcr = p["oi_pcr"]
    if oi_pcr > 1.2:
        factors.append(("Put-call ratio (OI)", +1, f"PCR {oi_pcr} > 1.2: more puts written than calls, often read as support below."))
    elif oi_pcr < 0.8:
        factors.append(("Put-call ratio (OI)", -1, f"PCR {oi_pcr} < 0.8: call writing dominates, often read as resistance above."))
    else:
        factors.append(("Put-call ratio (OI)", 0, f"PCR {oi_pcr} is between 0.8 and 1.2: no strong lean."))

    gap = (mp - spot) / spot * 100
    if gap > 0.3:
        factors.append(("Max pain vs spot", +1, f"Max pain {mp} is {gap:.2f}% above spot."))
    elif gap < -0.3:
        factors.append(("Max pain vs spot", -1, f"Max pain {mp} is {abs(gap):.2f}% below spot."))
    else:
        factors.append(("Max pain vs spot", 0, f"Max pain {mp} is within 0.3% of spot."))

    skew = s["skew_put_minus_call"] or 0
    if skew > 4:
        factors.append(("IV skew", -1, f"OTM puts carry {skew} vol points more than OTM calls: demand for downside protection."))
    else:
        factors.append(("IV skew", 0, f"Put-call skew of {skew} vol points is within its normal range."))

    move = spot - chain["prev_spot"]
    factors.append(("Price change", +1 if move > 0 else -1, f"Index {'up' if move > 0 else 'down'} {abs(move):.2f} points vs previous session."))

    score = sum(f[1] for f in factors)
    tilt = "Bullish tilt" if score >= 2 else "Bearish tilt" if score <= -2 else "Neutral"
    return {
        "tilt": tilt, "score": score,
        "factors": [{"name": n, "vote": v, "why": w} for n, v, w in factors],
        "disclaimer": DISCLAIMER,
    }
