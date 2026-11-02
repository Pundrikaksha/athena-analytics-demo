"""The in-browser engine must agree with the Python pipeline, value for value."""
import hashlib
import json
import pathlib
import random
import shutil
import subprocess
import unittest

from athena_demo import anomaly, site, synthetic

ROOT = pathlib.Path(__file__).resolve().parents[1]
SEEDS = [0, 7, 49, 1000, 1011, 1035, 1199, 2024, 999999]


@unittest.skipUnless(shutil.which("node"), "node is not installed; the browser engine was not compared")
class JsParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = "NIFTY-7"
        payload = {"config": site.engine_config(), "seeds": SEEDS, "text": cls.text,
                   "thresholds": site.engine_config()["thresholds"]}
        done = subprocess.run(["node", str(ROOT / "tests" / "js_parity_driver.js")], input=json.dumps(payload),
                              capture_output=True, text=True, check=True)
        cls.js = json.loads(done.stdout)

    def test_sha512_matches_hashlib(self):
        self.assertEqual(self.js["sha"], hashlib.sha512(self.text.encode()).hexdigest())

    def test_random_stream_matches_python(self):
        rng = random.Random(self.text)
        for i, value in enumerate(self.js["stream"]):
            self.assertAlmostEqual(value, rng.gauss(0, 1) if i % 2 else rng.random(), places=12)

    def test_chains_and_findings_match_python(self):
        self.assertEqual(len(self.js["chains"]), len(SEEDS) * len(synthetic.INDICES))
        for got in self.js["chains"]:
            with self.subTest(index=got["index"], seed=got["seed"]):
                chain = synthetic.option_chain(got["index"], seed=got["seed"])
                self.assertEqual(got["chain"], chain)
                self.assertEqual(got["findings"], anomaly.detect(chain))
                self.assertEqual({(p["strike"], p["kind"], p["type"]) for p in got["planted"]}, anomaly.compare(chain)[0])


if __name__ == "__main__":
    unittest.main()
