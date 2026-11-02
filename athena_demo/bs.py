"""Black-Scholes pricing, Greeks and implied volatility (pure Python)."""
from __future__ import annotations

import math

SQRT_2PI = math.sqrt(2.0 * math.pi)


def norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / SQRT_2PI


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _d1_d2(s: float, k: float, t: float, r: float, sigma: float):
    vol_t = sigma * math.sqrt(t)
    d1 = (math.log(s / k) + (r + 0.5 * sigma * sigma) * t) / vol_t
    return d1, d1 - vol_t


def price(kind: str, s: float, k: float, t: float, r: float, sigma: float) -> float:
    """European option price. kind is 'CE' (call) or 'PE' (put)."""
    if t <= 0 or sigma <= 0:
        return max(0.0, s - k) if kind == "CE" else max(0.0, k - s)
    d1, d2 = _d1_d2(s, k, t, r, sigma)
    if kind == "CE":
        return s * norm_cdf(d1) - k * math.exp(-r * t) * norm_cdf(d2)
    return k * math.exp(-r * t) * norm_cdf(-d2) - s * norm_cdf(-d1)


def greeks(kind: str, s: float, k: float, t: float, r: float, sigma: float) -> dict:
    """Delta, gamma, vega (per 1 vol point), theta (per calendar day)."""
    d1, d2 = _d1_d2(s, k, t, r, sigma)
    pdf = norm_pdf(d1)
    gamma = pdf / (s * sigma * math.sqrt(t))
    vega = s * pdf * math.sqrt(t) / 100.0
    common = -(s * pdf * sigma) / (2.0 * math.sqrt(t))
    if kind == "CE":
        delta = norm_cdf(d1)
        theta = common - r * k * math.exp(-r * t) * norm_cdf(d2)
    else:
        delta = norm_cdf(d1) - 1.0
        theta = common + r * k * math.exp(-r * t) * norm_cdf(-d2)
    return {"delta": delta, "gamma": gamma, "vega": vega, "theta": theta / 365.0}


def implied_vol(kind: str, market_price: float, s: float, k: float, t: float,
                r: float, lo: float = 1e-4, hi: float = 5.0, tol: float = 1e-6) -> float | None:
    """Solve for IV by bisection. Returns None if the price is outside no-arbitrage bounds."""
    intrinsic = max(0.0, s - k * math.exp(-r * t)) if kind == "CE" else max(0.0, k * math.exp(-r * t) - s)
    if market_price < intrinsic - 1e-9 or market_price <= 0:
        return None
    if price(kind, s, k, t, r, hi) < market_price:
        return None
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if price(kind, s, k, t, r, mid) > market_price:
            hi = mid
        else:
            lo = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)
