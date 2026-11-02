"""Deterministic synthetic NIFTY / BANKNIFTY option-chain and price-path generator.

Everything here is made up from a fixed random seed. No market data is downloaded.
A handful of anomalies are injected on purpose, with ground-truth labels, so the
anomaly detector can be validated (see tests and the "Anomalies" tab).
"""
from __future__ import annotations

import math
import random

from . import bs

INDICES = {
    # name: spot, strike step, lot size (illustrative), base IV
    "NIFTY": {"spot": 24150.0, "step": 50, "lot": 75, "base_iv": 0.13},
    "BANKNIFTY": {"spot": 51820.0, "step": 100, "lot": 35, "base_iv": 0.16},
}
RISK_FREE = 0.065
DAYS_TO_EXPIRY = 7
N_STRIKES_EACH_SIDE = 15


def _smile(base_iv: float, moneyness: float) -> float:
    """Skewed smile: puts (moneyness < 0) richer than calls."""
    return base_iv * (1.0 - 1.6 * moneyness + 18.0 * moneyness * moneyness)


def option_chain(index: str, seed: int = 7, inject_anomalies: bool = True,
                 stress_strength: float | None = None) -> dict:
    """Build one chain. stress_strength switches to the stress test's random planting."""
    cfg = INDICES[index]
    rng = random.Random(f"{index}-{seed}")
    spot, step = cfg["spot"], cfg["step"]
    prev_spot = spot * (1 - 0.004)  # synthetic: index up 0.4% vs previous session
    t = DAYS_TO_EXPIRY / 365.0
    atm = round(spot / step) * step
    rows = []
    for i in range(-N_STRIKES_EACH_SIDE, N_STRIKES_EACH_SIDE + 1):
        k = atm + i * step
        m = math.log(k / spot)
        row = {"strike": k}
        for kind in ("CE", "PE"):
            iv = _smile(cfg["base_iv"], m) * (1 + rng.gauss(0, 0.01))
            ltp = bs.price(kind, spot, k, t, RISK_FREE, iv)
            prev_iv = iv * (1 + rng.gauss(0, 0.02))
            prev_ltp = bs.price(kind, prev_spot, k, t + 1 / 365.0, RISK_FREE, prev_iv)
            # OI: concentrated a little OTM; puts below spot, calls above
            centre = atm + (3 if kind == "CE" else -3) * step
            width = 6 * step
            base = 9.0e6 if index == "NIFTY" else 2.5e6
            oi = base * math.exp(-((k - centre) ** 2) / (2 * width ** 2)) * (0.85 + 0.3 * rng.random())
            if k % (step * 10) == 0:  # round-number strikes attract more OI
                oi *= 1.6
            oi_change_pct = rng.gauss(0.04 if kind == "PE" else 0.02, 0.05)
            prev_oi = oi / (1 + oi_change_pct)
            volume = oi * (0.3 + 0.4 * rng.random())
            row[kind] = {
                "ltp": round(max(ltp, 0.05), 2),
                "prev_ltp": round(max(prev_ltp, 0.05), 2),
                "iv": round(iv * 100, 2),
                "oi": int(oi),
                "prev_oi": int(prev_oi),
                "volume": int(volume),
                "anomaly": None,
            }
        rows.append(row)

    if stress_strength is not None:
        _inject_stress(rows, index, seed, stress_strength)
    elif inject_anomalies:
        _inject(rows, atm, step, rng)

    # recompute Greeks from the final (possibly anomalous) IV
    for row in rows:
        for kind in ("CE", "PE"):
            leg = row[kind]
            g = bs.greeks(kind, spot, row["strike"], t, RISK_FREE, leg["iv"] / 100.0)
            leg.update({key: round(val, 5) for key, val in g.items()})
    return {
        "index": index, "spot": spot, "prev_spot": round(prev_spot, 2), "atm": atm,
        "step": step, "lot": cfg["lot"], "days_to_expiry": DAYS_TO_EXPIRY,
        "risk_free": RISK_FREE, "rows": rows, "synthetic": True,
    }


def _inject(rows, atm, step, rng):
    """Plant labelled anomalies: an OI spike, an IV kink and a volume burst."""
    by_strike = {r["strike"]: r for r in rows}
    spike = by_strike.get(atm + 5 * step)
    if spike:
        spike["CE"]["oi"] = int(spike["CE"]["oi"] * 4.5)
        spike["CE"]["anomaly"] = "oi_spike"
    kink = by_strike.get(atm - 4 * step)
    if kink:
        kink["PE"]["iv"] = round(kink["PE"]["iv"] * 1.45, 2)
        kink["PE"]["anomaly"] = "iv_kink"
    burst = by_strike.get(atm - 8 * step)
    if burst:
        burst["PE"]["volume"] = int(burst["PE"]["oi"] * 6)
        burst["PE"]["anomaly"] = "volume_burst"


def _inject_stress(rows, index, seed, strength):
    """Plant one anomaly of each type on random legs, scaled by strength (1.0 = the standard size).

    Uses its own random stream, so the underlying chain is the same as for that seed without it.
    """
    rng = random.Random(f"stress-{index}-{seed}")
    legs = [(r, kind) for r in rows[3:-3] for kind in ("CE", "PE")]
    (spike, spike_kind), (kink, kink_kind), (burst, burst_kind) = rng.sample(legs, 3)
    spike[spike_kind]["oi"] = int(spike[spike_kind]["oi"] * (1 + 3.5 * strength))
    spike[spike_kind]["anomaly"] = "oi_spike"
    kink[kink_kind]["iv"] = round(kink[kink_kind]["iv"] * (1 + 0.45 * strength), 2)
    kink[kink_kind]["anomaly"] = "iv_kink"
    burst[burst_kind]["volume"] = int(burst[burst_kind]["oi"] * (0.5 + 5.5 * strength))
    burst[burst_kind]["anomaly"] = "volume_burst"


def price_path(index: str, days: int = 250, seed: int = 11) -> list[dict]:
    """Synthetic daily index closes, ATM IV and PCR with mild regime persistence."""
    cfg = INDICES[index]
    rng = random.Random(f"path-{index}-{seed}")
    s = cfg["spot"] * 0.9
    iv = cfg["base_iv"]
    pcr = 1.0
    regime = 1
    out = []
    for d in range(days):
        if rng.random() < 0.03:
            regime = -regime
        drift = 0.0006 * regime
        ret = drift + iv / math.sqrt(252) * rng.gauss(0, 1)
        s *= math.exp(ret)
        iv = max(0.08, min(0.35, iv + 0.15 * (cfg["base_iv"] - iv) + 0.01 * rng.gauss(0, 1) - 0.3 * ret))
        # PCR leans with the regime (put writing in up-trends) plus noise
        pcr = max(0.4, min(1.8, pcr + 0.25 * ((1.0 + 0.25 * regime) - pcr) + 0.08 * rng.gauss(0, 1)))
        out.append({"day": d, "close": round(s, 2), "atm_iv": round(iv * 100, 2), "pcr": round(pcr, 3)})
    return out
