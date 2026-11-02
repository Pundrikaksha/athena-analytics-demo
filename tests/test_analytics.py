import math
import pathlib
import re
import unittest

from athena_demo import analytics, anomaly, backtest, bs, site, synthetic

ROOT = pathlib.Path(__file__).resolve().parents[1]


class BlackScholes(unittest.TestCase):
    def test_put_call_parity(self):
        s, k, t, r, v = 24000, 24100, 7 / 365, 0.065, 0.14
        lhs = bs.price("CE", s, k, t, r, v) - bs.price("PE", s, k, t, r, v)
        self.assertAlmostEqual(lhs, s - k * math.exp(-r * t), places=6)

    def test_implied_vol_round_trip(self):
        for kind in ("CE", "PE"):
            p = bs.price(kind, 51800, 52000, 10 / 365, 0.065, 0.17)
            self.assertAlmostEqual(bs.implied_vol(kind, p, 51800, 52000, 10 / 365, 0.065), 0.17, places=4)

    def test_implied_vol_rejects_below_intrinsic(self):
        self.assertIsNone(bs.implied_vol("CE", 1.0, 25000, 24000, 7 / 365, 0.065))

    def test_greek_signs(self):
        c = bs.greeks("CE", 24000, 24000, 7 / 365, 0.065, 0.13)
        p = bs.greeks("PE", 24000, 24000, 7 / 365, 0.065, 0.13)
        self.assertTrue(0 < c["delta"] < 1 and -1 < p["delta"] < 0)
        self.assertAlmostEqual(c["delta"] - p["delta"], 1.0, places=9)
        self.assertGreater(c["gamma"], 0)
        self.assertLess(c["theta"], 0)


class Analytics(unittest.TestCase):
    def setUp(self):
        self.chain = synthetic.option_chain("NIFTY")

    def test_deterministic(self):
        self.assertEqual(self.chain, synthetic.option_chain("NIFTY"))

    def test_pcr_and_max_pain(self):
        p = analytics.pcr(self.chain)
        self.assertAlmostEqual(p["oi_pcr"], p["put_oi"] / p["call_oi"], places=3)
        self.assertIn(analytics.max_pain(self.chain), [r["strike"] for r in self.chain["rows"]])

    def test_buildup_quadrants(self):
        self.assertEqual(analytics.classify_buildup(+1, +1), "Long build-up")
        self.assertEqual(analytics.classify_buildup(-1, +1), "Short build-up")
        self.assertEqual(analytics.classify_buildup(+1, -1), "Short covering")
        self.assertEqual(analytics.classify_buildup(-1, -1), "Long unwinding")

    def test_signal_is_labelled_educational(self):
        sig = analytics.explain_signal(self.chain)
        self.assertIn("not advice", sig["disclaimer"])
        self.assertIn(sig["tilt"], {"Bullish tilt", "Bearish tilt", "Neutral"})
        self.assertEqual(sig["score"], sum(f["vote"] for f in sig["factors"]))


class Anomalies(unittest.TestCase):
    def test_finds_planted_anomalies_on_default_seed(self):
        for name in synthetic.INDICES:
            self.assertEqual(anomaly.evaluate(synthetic.option_chain(name))["recall"], 1.0)

    def test_held_out_seeds_quality(self):
        tp = planted = flagged = 0
        for name in synthetic.INDICES:
            for s in range(1000, 1040):
                ev = anomaly.evaluate(synthetic.option_chain(name, seed=s))
                tp += ev["true_positives"]; planted += ev["planted"]; flagged += ev["flagged"]
        self.assertGreaterEqual(tp / planted, 0.95)
        self.assertGreaterEqual(tp / flagged, 0.85)

    def test_robust_z_ignores_single_outlier(self):
        z = anomaly.robust_z([1, 1.1, 0.9, 1.0, 1.05, 50])
        self.assertGreater(z[-1], 10)
        self.assertTrue(all(abs(v) < 3 for v in z[:-1]))


class Backtest(unittest.TestCase):
    def test_equity_curve_consistent(self):
        path = synthetic.price_path("NIFTY")
        bt = backtest.run(path, 75)
        self.assertEqual(len(bt["equity"]), len(path) - 1)
        self.assertEqual(bt["final_pnl"], bt["equity"][-1])
        self.assertLessEqual(bt["max_drawdown"], 0)
        self.assertTrue(bt["hypothetical"])


class SafetyGuards(unittest.TestCase):
    """The demo must stay analytics-only."""
    BANNED = re.compile(r"place_?order|modify_?order|cancel_?order|kiteconnect|neo_api|smartapi|"
                        r"api[_-]?key|access[_-]?token|api[_-]?secret|requests\.post|urllib\.request|"
                        r"socket\.|http\.client", re.I)

    def test_no_trading_or_network_code(self):
        for path in list((ROOT / "athena_demo").glob("*.py")) + list((ROOT / "scripts").glob("*.py")):
            self.assertIsNone(self.BANNED.search(path.read_text()), f"banned pattern in {path.name}")

    def test_no_env_files(self):
        self.assertEqual([p for p in ROOT.rglob(".env*") if ".git" not in p.parts], [])

    def test_page_has_disclaimer_and_no_external_assets(self):
        page = site.build()
        self.assertIn("Not investment advice", page)
        self.assertIn("Educational, not advice", page)
        self.assertNotRegex(page, r"<script[^>]+src=|<link[^>]+href=\"http")


if __name__ == "__main__":
    unittest.main()
