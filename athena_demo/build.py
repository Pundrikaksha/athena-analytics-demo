"""CLI: generate synthetic data and the static dashboard into docs/."""
from __future__ import annotations

import argparse
import json
import pathlib

from . import site, synthetic


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="docs", help="output directory (default: docs)")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args(argv)
    out = pathlib.Path(args.out)
    (out / "data").mkdir(parents=True, exist_ok=True)
    for name in synthetic.INDICES:
        chain = synthetic.option_chain(name, seed=args.seed)
        (out / "data" / f"{name.lower()}_chain.json").write_text(json.dumps(chain, indent=1))
        (out / "data" / f"{name.lower()}_path.json").write_text(json.dumps(synthetic.price_path(name)))
    (out / "index.html").write_text(site.build(seed=args.seed), encoding="utf-8")
    (out / ".nojekyll").write_text("")
    print(f"wrote {out / 'index.html'} and synthetic data in {out / 'data'}")


if __name__ == "__main__":
    main()
