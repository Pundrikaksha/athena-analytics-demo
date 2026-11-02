import json
import pathlib
import re
import unittest

from athena_demo import anomaly, evaluation, synthetic

ROOT = pathlib.Path(__file__).resolve().parents[1]


class Metrics(unittest.TestCase):
    def test_metric_formulas(self):
        m = evaluation._metrics(tp=8, fp=2, fn=8)
        self.assertEqual((m["precision"], m["recall"]), (0.8, 0.5))
        self.assertAlmostEqual(m["f1"], 2 * 0.8 * 0.5 / 1.3, places=4)

    def test_metrics_with_no_flags_or_nothing_planted(self):
        self.assertIsNone(evaluation._metrics(0, 0, 3)["precision"])
        self.assertIsNone(evaluation._metrics(0, 3, 0)["recall"])
        self.assertEqual(evaluation._metrics(0, 0, 0)["f1"], 0.0)


class Report(unittest.TestCase):
    def setUp(self):
        self.report = evaluation.report()
        self.splits = [self.report["tuning_seeds_0_49"], self.report["test_seeds_1000_1199"],
                       *self.report["stress_seeds_2000_2099"].values()]

    def test_per_type_counts_add_up_to_the_total(self):
        for split in self.splits:
            for key in ("planted", "flagged", "true_positives", "false_positives", "false_negatives",
                        "false_flags_at_round_strikes"):
                self.assertEqual(sum(t[key] for t in split["by_type"].values()), split[key])

    def test_every_chain_has_one_of_each_type(self):
        for split in self.splits:
            for t in split["by_type"].values():
                self.assertEqual(t["planted"], split["chains"])

    def test_seed_ranges_do_not_overlap(self):
        ranges = [set(evaluation.TUNING_SEEDS), set(evaluation.TEST_SEEDS), set(evaluation.STRESS_SEEDS)]
        self.assertEqual(len(set.union(*ranges)), sum(len(r) for r in ranges))

    def test_declared_thresholds_are_unchanged(self):
        self.assertEqual((anomaly.OI_THRESHOLD, anomaly.THRESHOLD), (5.0, 3.5))
        self.assertEqual(self.report["threshold_oi"], 5.0)

    def test_committed_report_matches_a_fresh_run(self):
        committed = json.loads((ROOT / "docs" / "data" / "anomaly_evaluation.json").read_text())
        self.assertEqual(committed, json.loads(json.dumps(self.report)))

    def test_readme_tables_match_the_report(self):
        readme = (ROOT / "README.md").read_text()
        names = {"oi_spike": "OI spike", "iv_kink": "IV kink", "volume_burst": "Volume burst"}
        test = self.report["test_seeds_1000_1199"]
        for name, m in [(names[k], v) for k, v in test["by_type"].items()] + [("**All types**", test)]:
            row = (f"| {name} | {m['planted']} | {m['flagged']} | {m['true_positives']} | {m['false_positives']} | "
                   f"{m['false_negatives']} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} |")
            self.assertIn(row, readme)
        for size, m in self.report["stress_seeds_2000_2099"].items():
            recalls = " | ".join(f"{m['by_type'][k]['recall']:.3f}" for k in names)
            row = f"| {float(size) * 100:.0f}% | {recalls} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} |"
            self.assertIn(row, readme)

    def test_stated_false_flag_finding_holds(self):
        by_type = self.report["test_seeds_1000_1199"]["by_type"]
        self.assertEqual(by_type["oi_spike"]["false_flags_at_round_strikes"], by_type["oi_spike"]["false_positives"])
        self.assertLess(by_type["iv_kink"]["false_flags_at_round_strikes"] * 2, by_type["iv_kink"]["false_positives"])


class Detector(unittest.TestCase):
    def test_detection_never_reads_the_labels(self):
        chain = synthetic.option_chain("NIFTY", seed=1035)
        before = anomaly.detect(chain)
        for row in chain["rows"]:
            for kind in anomaly.KINDS:
                del row[kind]["anomaly"]
        self.assertEqual(anomaly.detect(chain), before)

    def test_volume_detector_is_one_sided_and_iv_is_two_sided(self):
        chain = synthetic.option_chain("NIFTY", inject_anomalies=False)
        chain["rows"][10]["CE"]["volume"] = 1
        self.assertNotIn(("volume_burst", 10), [(f["type"], 10) for f in anomaly.detect(chain) if f["strike"] == chain["rows"][10]["strike"]])
        chain = synthetic.option_chain("NIFTY", inject_anomalies=False)
        chain["rows"][10]["CE"]["iv"] *= 0.6
        low = [f for f in anomaly.detect(chain) if f["type"] == "iv_kink" and f["strike"] == chain["rows"][10]["strike"]]
        self.assertTrue(low and low[0]["z"] < 0)


class StressPlanting(unittest.TestCase):
    def test_full_size_planting_matches_the_standard_sizes(self):
        clean = synthetic.option_chain("NIFTY", seed=2000, inject_anomalies=False)
        stressed = synthetic.option_chain("NIFTY", seed=2000, stress_strength=1.0)
        for a, b in zip(clean["rows"], stressed["rows"]):
            for kind in anomaly.KINDS:
                if b[kind]["anomaly"] == "oi_spike":
                    self.assertEqual(b[kind]["oi"], int(a[kind]["oi"] * 4.5))
                elif b[kind]["anomaly"] == "iv_kink":
                    self.assertEqual(b[kind]["iv"], round(a[kind]["iv"] * 1.45, 2))
                elif b[kind]["anomaly"] == "volume_burst":
                    self.assertEqual(b[kind]["volume"], int(a[kind]["oi"] * 6))
                else:
                    self.assertEqual(a[kind], b[kind])

    def test_plants_three_distinct_legs_that_move_with_the_seed(self):
        def planted(seed):
            return anomaly.compare(synthetic.option_chain("NIFTY", seed=seed, stress_strength=0.5))[0]
        self.assertEqual(len(planted(2000)), 3)
        self.assertEqual(planted(2000), planted(2000))
        self.assertNotEqual(planted(2000), planted(2001))

    def test_default_chain_is_unaffected(self):
        self.assertEqual(anomaly.compare(synthetic.option_chain("NIFTY", seed=3))[0],
                         {(24400, "CE", "oi_spike"), (23950, "PE", "iv_kink"), (23750, "PE", "volume_burst")})


class Examples(unittest.TestCase):
    def test_example_seeds_show_what_they_claim(self):
        for name in synthetic.INDICES:
            examples = evaluation.example_seeds(name)
            self.assertEqual(set(examples), {"clean", "false_flag", "miss"})
            def outcome(seed):
                return anomaly.compare(synthetic.option_chain(name, seed=seed))
            truth, found = outcome(examples["clean"])
            self.assertEqual(truth, found)
            truth, found = outcome(examples["false_flag"])
            self.assertTrue(found - truth)
            truth, found = outcome(examples["miss"])
            self.assertTrue(truth - found)


class Reproducibility(unittest.TestCase):
    def test_run_all_script_is_executable_and_runs_every_stage(self):
        script = ROOT / "run_all.sh"
        self.assertTrue(script.stat().st_mode & 0o111)
        text = script.read_text()
        for stage in ("athena_demo.build", "evaluate_anomaly.py", "-m unittest", "diff -r docs"):
            self.assertIn(stage, text)

    def test_readme_pins_the_same_python_as_the_script(self):
        pinned = re.search(r"^PINNED=(\S+)$", (ROOT / "run_all.sh").read_text(), re.M).group(1)
        self.assertRegex((ROOT / "README.md").read_text(), rf"\*\*Python {re.escape(pinned)}\*\*")


if __name__ == "__main__":
    unittest.main()
