"""Unsupervised anomaly detection on an option chain.

Three explainable detectors, each a robust z-score (median / MAD) of a residual:
  * OI spike     - log OI minus the median log OI of neighbouring strikes
  * IV kink      - IV minus a least-squares quadratic smile fit
  * Volume burst - log(volume / OI) versus the chain's typical turnover
A point is flagged when its robust z exceeds that detector's declared threshold.
Thresholds were chosen on tuning seeds 0-49 only (see scripts/evaluate_anomaly.py).
The OI detector needs a higher bar because round-number strikes legitimately
carry more open interest than their neighbours.
"""
from __future__ import annotations

import math
import statistics

THRESHOLD = 3.5  # IV kink and volume burst
OI_THRESHOLD = 5.0
KINDS = ("CE", "PE")
TYPES = ("oi_spike", "iv_kink", "volume_burst")


def robust_z(values: list[float]) -> list[float]:
    med = statistics.median(values)
    mad = statistics.median(abs(v - med) for v in values) or 1e-9
    return [0.6745 * (v - med) / mad for v in values]


def _solve3(a, b):
    """Gaussian elimination for a 3x3 system."""
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(3):
        p = max(range(c, 3), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        for r in range(3):
            if r != c:
                f = m[r][c] / m[c][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    return [m[i][3] / m[i][i] for i in range(3)]


def quad_fit(xs: list[float], ys: list[float]) -> list[float]:
    s = [sum(x ** p for x in xs) for p in range(5)]
    t = [sum(y * x ** p for x, y in zip(xs, ys)) for p in range(3)]
    a = [[s[0], s[1], s[2]], [s[1], s[2], s[3]], [s[2], s[3], s[4]]]
    return _solve3(a, t)


def _neighbour_residuals(series: list[float], window: int = 3) -> list[float]:
    out = []
    for i, v in enumerate(series):
        nb = [series[j] for j in range(max(0, i - window), min(len(series), i + window + 1)) if j != i]
        out.append(v - statistics.median(nb))
    return out


def detect(chain: dict, threshold: float = THRESHOLD, oi_threshold: float = OI_THRESHOLD) -> list[dict]:
    rows = chain["rows"]
    spot = chain["spot"]
    findings = []
    for kind in KINDS:
        strikes = [r["strike"] for r in rows]
        # OI spike
        log_oi = [math.log(max(r[kind]["oi"], 1)) for r in rows]
        z = robust_z(_neighbour_residuals(log_oi))
        for k, zi in zip(strikes, z):
            if zi > oi_threshold:
                findings.append({"strike": k, "kind": kind, "type": "oi_spike", "z": round(zi, 2),
                                 "why": "Open interest far above neighbouring strikes."})
        # IV kink
        xs = [math.log(k / spot) for k in strikes]
        ys = [r[kind]["iv"] for r in rows]
        c = quad_fit(xs, ys)
        resid = [y - (c[0] + c[1] * x + c[2] * x * x) for x, y in zip(xs, ys)]
        z = robust_z(resid)
        for k, zi in zip(strikes, z):
            if abs(zi) > threshold:
                findings.append({"strike": k, "kind": kind, "type": "iv_kink", "z": round(zi, 2),
                                 "why": "Implied volatility breaks away from the fitted smile."})
        # Volume burst
        turnover = [math.log(max(r[kind]["volume"], 1) / max(r[kind]["oi"], 1)) for r in rows]
        z = robust_z(turnover)
        for k, zi in zip(strikes, z):
            if zi > threshold:
                findings.append({"strike": k, "kind": kind, "type": "volume_burst", "z": round(zi, 2),
                                 "why": "Traded volume unusually high relative to open interest."})
    return sorted(findings, key=lambda f: -abs(f["z"]))


def compare(chain: dict) -> tuple[set, set]:
    """Return the (planted, flagged) sets of (strike, leg, type). Labels are read only here."""
    truth = {(r["strike"], k, r[k]["anomaly"]) for r in chain["rows"] for k in KINDS if r[k]["anomaly"]}
    found = {(f["strike"], f["kind"], f["type"]) for f in detect(chain)}
    return truth, found


def evaluate(chain: dict) -> dict:
    """Compare detections with the injected ground-truth labels."""
    truth, found = compare(chain)
    tp = len(truth & found)
    precision = tp / len(found) if found else 1.0
    recall = tp / len(truth) if truth else 1.0
    return {"true_positives": tp, "planted": len(truth), "flagged": len(found),
            "precision": round(precision, 3), "recall": round(recall, 3)}
