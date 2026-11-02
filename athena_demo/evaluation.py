"""Score the anomaly detector over many seeds: overall, per anomaly type and under stress.

Three seed ranges, which never overlap:
  * tuning (0-49): the only seeds used to choose the thresholds
  * test (1000-1199): held out from threshold selection
  * stress (2000-2099): anomalies at random legs and at reduced sizes
"""
from __future__ import annotations

from functools import lru_cache

from . import anomaly, synthetic

TUNING_SEEDS = range(50)
TEST_SEEDS = range(1000, 1200)
STRESS_SEEDS = range(2000, 2100)
STRESS_STRENGTHS = (0.25, 0.5, 0.75, 1.0)


def _metrics(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
    return {"planted": tp + fn, "flagged": tp + fp, "true_positives": tp, "false_positives": fp,
            "false_negatives": fn,
            "precision": round(precision, 4) if precision is not None else None,
            "recall": round(recall, 4) if recall is not None else None,
            "f1": round(f1, 4)}


def score_split(seeds, stress_strength: float | None = None) -> dict:
    counts = {t: {"tp": 0, "fp": 0, "fn": 0, "round_fp": 0, "clean": 0} for t in anomaly.TYPES}
    for name, cfg in synthetic.INDICES.items():
        for seed in seeds:
            chain = synthetic.option_chain(name, seed=seed, stress_strength=stress_strength)
            truth, found = anomaly.compare(chain)
            for _, _, kind in truth & found:
                counts[kind]["tp"] += 1
            for strike, _, kind in found - truth:
                counts[kind]["fp"] += 1
                counts[kind]["round_fp"] += strike % (cfg["step"] * 10) == 0
            for _, _, kind in truth - found:
                counts[kind]["fn"] += 1
            for f in anomaly.detect(synthetic.option_chain(name, seed=seed, inject_anomalies=False)):
                counts[f["type"]]["clean"] += 1

    chains = len(seeds) * len(synthetic.INDICES)
    by_type = {}
    for kind, c in counts.items():
        by_type[kind] = {**_metrics(c["tp"], c["fp"], c["fn"]),
                         "false_flags_at_round_strikes": c["round_fp"],
                         "false_flags_per_clean_chain": round(c["clean"] / chains, 4)}
    total = {k: sum(c[k] for c in counts.values()) for k in ("tp", "fp", "fn", "round_fp", "clean")}
    return {"chains": chains, **_metrics(total["tp"], total["fp"], total["fn"]),
            "false_flags_at_round_strikes": total["round_fp"],
            "false_flags_per_clean_chain": round(total["clean"] / chains, 4),
            "by_type": by_type}


@lru_cache(maxsize=1)
def report() -> dict:
    return {
        "threshold_iv": anomaly.THRESHOLD,
        "threshold_volume": anomaly.THRESHOLD,
        "threshold_oi": anomaly.OI_THRESHOLD,
        "tuning_seeds_0_49": score_split(TUNING_SEEDS),
        "test_seeds_1000_1199": score_split(TEST_SEEDS),
        "stress_seeds_2000_2099": {f"{s:.2f}": score_split(STRESS_SEEDS, stress_strength=s)
                                   for s in STRESS_STRENGTHS},
    }


def example_seeds(index: str) -> dict:
    """First held-out seed showing each outcome, so the page can show failures as well as successes."""
    found: dict = {}
    for seed in TEST_SEEDS:
        truth, flagged = anomaly.compare(synthetic.option_chain(index, seed=seed))
        if truth - flagged:
            found.setdefault("miss", seed)
        elif flagged - truth:
            found.setdefault("false_flag", seed)
        else:
            found.setdefault("clean", seed)
        if len(found) == 3:
            break
    return found
