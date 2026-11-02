"""Validate the anomaly detector on held-out seeds.

The thresholds (OI 5.0, IV/volume 3.5) were chosen on seeds 0-49 ("tuning"); this script reports results
on seeds 1000-1199 that were never looked at while choosing them ("test"), plus the
false-positive rate on clean chains with nothing planted.
"""
from __future__ import annotations

import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from athena_demo import anomaly, synthetic  # noqa: E402


def run(seeds) -> dict:
    tp = planted = flagged = clean_flags = 0
    for name in synthetic.INDICES:
        for s in seeds:
            ev = anomaly.evaluate(synthetic.option_chain(name, seed=s))
            tp += ev["true_positives"]; planted += ev["planted"]; flagged += ev["flagged"]
            clean_flags += len(anomaly.detect(synthetic.option_chain(name, seed=s, inject_anomalies=False)))
    chains = len(seeds) * len(synthetic.INDICES)
    return {"chains": chains, "planted": planted, "flagged": flagged,
            "precision": round(tp / flagged, 4) if flagged else None,
            "recall": round(tp / planted, 4) if planted else None,
            "false_flags_per_clean_chain": round(clean_flags / chains, 4)}


if __name__ == "__main__":
    result = {"threshold_iv_volume": anomaly.THRESHOLD, "threshold_oi": anomaly.OI_THRESHOLD, "tuning_seeds_0_49": run(range(50)),
              "test_seeds_1000_1199": run(range(1000, 1200))}
    print(json.dumps(result, indent=2))
