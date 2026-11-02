# ATHENA Analytics Demo

Educational options analytics for **NIFTY** and **BANKNIFTY** on **synthetic data**, with an
explainable anomaly detector. One command builds a self-contained static web page.

> ## ⚠ Not investment advice · No trading
> This project is an educational demo. It **does not trade**, contains **no order code**,
> **no broker SDKs or endpoints**, **no API keys** and **no real market data**. Every price,
> open-interest figure and price path is generated from a fixed random seed by
> `athena_demo/synthetic.py`. The "signal" and "paper P&L" views describe made-up data and are
> not recommendations to buy or sell anything. Simulated results say nothing about the future.

## What it shows

| Tab | What you get |
|---|---|
| Option chain | 31-strike weekly chain: OI, ΔOI, volume, IV, delta, LTP for calls and puts; ATM and ITM shading |
| IV & Greeks | Volatility smile chart, ATM IV, put−call skew, straddle price, implied move, ATM Greeks, straddle theta/vega per lot |
| PCR & OI build-up | OI and volume PCR, max pain, OI-by-strike chart, long/short build-up and covering/unwinding classification |
| Signal explainer | Four transparent rules (PCR, max pain, skew, price change) that each vote −1/0/+1, with the reason shown. Labelled *educational, not advice* |
| Anomalies | Unsupervised detector for OI spikes, IV-smile kinks and volume bursts, scored against planted ground truth |
| Paper P&L | Hypothetical rule-based P&L curve, drawdown and hit rate on a synthetic 250-day index path |

## Run it

Requires Python 3.10+ and nothing else (standard library only).

```sh
python3 -m athena_demo.build        # writes docs/index.html + docs/data/*.json
python3 -m unittest -v              # 15 tests
python3 scripts/evaluate_anomaly.py # held-out validation of the anomaly detector
```

Open `docs/index.html` in a browser. Deep links work: `docs/index.html#idx=BANKNIFTY&tab=anomaly`.
The `docs/` folder is ready for GitHub Pages ("Deploy from branch", folder `/docs`).

## Screenshots

| | |
|---|---|
| ![Option chain](screenshots/chain.png) | ![IV & Greeks](screenshots/iv.png) |
| ![PCR & OI](screenshots/oi.png) | ![Signal explainer](screenshots/signal.png) |
| ![Anomalies](screenshots/anomaly.png) | ![Paper P&L](screenshots/backtest.png) |

## The intelligent part: explainable anomaly detection

`athena_demo/anomaly.py` runs three unsupervised detectors per option leg. Each turns a residual
into a **robust z-score** (median and MAD, so a single outlier cannot hide by inflating the spread):

1. **OI spike**: log open interest minus the median of the 3 strikes either side.
2. **IV kink**: implied volatility minus a least-squares quadratic smile in log-moneyness.
3. **Volume burst**: log(volume ÷ OI) against the chain's typical turnover.

Thresholds are declared up front (OI z > 5.0; IV and volume |z| > 3.5) and were chosen on tuning
seeds 0–49 only. The generator plants three labelled anomalies per chain; labels are used for
scoring, never for detection.

**Held-out validation** (seeds 1000–1199, 400 chains, 1,200 planted anomalies,
`docs/data/anomaly_evaluation.json`):

| Split | Precision | Recall | False flags per clean chain |
|---|---|---|---|
| Tuning (seeds 0–49) | 0.932 | 1.000 | 0.25 |
| Test (seeds 1000–1199) | 0.905 | 0.988 | 0.40 |

Most false flags are round-number strikes, which carry genuinely more open interest.

## Layout

```
athena_demo/bs.py         Black-Scholes price, Greeks, implied-vol solver
athena_demo/synthetic.py  seeded chain + price-path generator with planted anomalies
athena_demo/analytics.py  PCR, max pain, OI build-up, IV/Greeks summary, signal explainer
athena_demo/anomaly.py    robust z-score anomaly detectors + evaluation
athena_demo/backtest.py   hypothetical paper P&L on a synthetic path
athena_demo/site.py       static HTML/SVG renderer (no CDN, no JS libraries)
tests/                    unit tests, including guards that fail if order/network/key code appears
```

## Data, attribution and licensing

- Data: 100% synthetic, generated in this repository. No third-party data or models.
- Formulas: textbook Black-Scholes; standard PCR, max-pain and OI build-up definitions.
- Code: original, MIT licensed (see `LICENSE`).

## Known limitations

- Synthetic data has a cleaner structure than real markets; detector scores on real chains would be lower.
- Black-Scholes assumes constant volatility and European exercise.
- Lot sizes and costs are illustrative, not current exchange values.
- The signal rules are deliberately simple and are not a strategy.
- The paper P&L ignores slippage, margin and gaps.
