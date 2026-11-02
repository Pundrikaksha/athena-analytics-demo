"""Validate the anomaly detector on held-out seeds.

The thresholds (OI 5.0, IV/volume 3.5) were chosen on seeds 0-49 ("tuning"). This script reports
precision, recall and F1 per anomaly type on those seeds and on the held-out seeds 1000-1199
("test"), the false-flag rate on clean chains with nothing planted, and a stress test on seeds
2000-2099 with anomalies at random legs and reduced sizes.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from athena_demo import evaluation  # noqa: E402


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", help="also write the JSON report to this file")
    args = ap.parse_args(argv)
    text = json.dumps(evaluation.report(), indent=2) + "\n"
    if args.out:
        pathlib.Path(args.out).write_text(text)
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
