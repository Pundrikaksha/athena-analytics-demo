import html.parser
import pathlib
import re
import unittest

from athena_demo import evaluation, site

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = site.build()
VARS = dict(re.findall(r"--([a-z-]+):(#[0-9a-f]{6})", site.CSS))


def contrast(a: str, b: str) -> float:
    def luminance(colour):
        def channel(v):
            v /= 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        r, g, bl = (channel(int(colour[i:i + 2], 16)) for i in (1, 3, 5))
        return 0.2126 * r + 0.7152 * g + 0.0722 * bl
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


class Tags(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.seen, self.ids = [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.seen.append((tag, attrs))
        if "id" in attrs:
            self.ids.append(attrs["id"])


class Content(unittest.TestCase):
    def test_explains_problem_method_and_how_to_read(self):
        for text in ("Find the anomaly in an option chain", "How the detection works", "How to read this page",
                     "Evidence and limits", "Limitations", "Not investment advice"):
            self.assertIn(text, PAGE)

    def test_headline_numbers_come_from_the_evaluation(self):
        test = evaluation.report()["test_seeds_1000_1199"]
        for key, label in (("precision", "Precision"), ("recall", "Recall"), ("f1", "F1")):
            self.assertIn(f"<span>{label}</span><b>{test[key]:.3f}</b>", PAGE)
        self.assertIn(f"<td>{test['by_type']['iv_kink']['precision']:.3f}</td>", PAGE)


class NoNetwork(unittest.TestCase):
    def test_content_security_policy_blocks_all_requests(self):
        self.assertIn('http-equiv="Content-Security-Policy"', PAGE)
        self.assertIn("default-src 'none'", site.CSP)
        self.assertNotRegex(site.CSP, r"https?:|connect-src")

    def test_no_external_references_or_network_apis(self):
        self.assertNotRegex(PAGE, r"https?://")
        self.assertNotRegex(PAGE, r"\bfetch\s*\(|XMLHttpRequest|WebSocket|EventSource|sendBeacon|importScripts|\bimport\s*\(|<link|<iframe|<img")

    def test_browser_code_has_no_trading_code(self):
        for name in ("engine.js", "ui.js"):
            text = (ROOT / "athena_demo" / name).read_text()
            self.assertNotRegex(text, r"(?i)place_?order|modify_?order|cancel_?order|api[_-]?key|access[_-]?token|api[_-]?secret")


class Accessibility(unittest.TestCase):
    def setUp(self):
        self.tags = Tags()
        self.tags.feed(PAGE)

    def test_text_colours_meet_wcag_aa(self):
        surfaces = ["bg", "panel", "raised", "atm", "itm"]
        for text in ("text", "mute"):
            for surface in surfaces:
                self.assertGreaterEqual(contrast(VARS[text], VARS[surface]), 4.5, f"{text} on {surface}")
        self.assertGreaterEqual(contrast(VARS["warn"], VARS["warn-bg"]), 4.5)
        self.assertGreaterEqual(contrast(VARS["acc"], VARS["bg"]), 4.5)
        self.assertGreaterEqual(contrast("#0d1117", VARS["acc"]), 4.5)

    def test_marks_and_controls_meet_the_non_text_minimum(self):
        for mark in ("ce", "pe", "flag", "control"):
            self.assertGreaterEqual(contrast(VARS[mark], VARS["panel"]), 3.0, mark)

    def test_calls_and_puts_are_not_red_and_green(self):
        self.assertEqual((site.CALL_COLOUR, site.PUT_COLOUR), ("#3987e5", "#d95926"))

    def test_structure(self):
        self.assertIn('<html lang="en">', PAGE)
        self.assertEqual(len(self.tags.ids), len(set(self.tags.ids)), "duplicate ids")
        self.assertEqual(sum(tag == "h1" for tag, _ in self.tags.seen), 1)
        tabs = [a for tag, a in self.tags.seen if a.get("role") == "tab"]
        self.assertEqual(len(tabs), 6)
        for tag, attrs in self.tags.seen:
            if tag == "svg":
                self.assertTrue(attrs.get("aria-label"), "chart without a text alternative")
        self.assertIn("<label for='seed'>", PAGE)
        self.assertIn("aria-live='polite'", PAGE)

    def test_works_without_javascript(self):
        self.assertIn("<noscript><style>.view{display:block}", PAGE)


class Responsive(unittest.TestCase):
    def test_viewport_and_breakpoint(self):
        self.assertIn('name="viewport" content="width=device-width,initial-scale=1"', PAGE)
        self.assertIn("@media (max-width:720px)", PAGE)

    def test_no_fixed_two_column_inline_layout(self):
        self.assertNotIn("grid-template-columns:1fr 2fr'", PAGE)


class SeedLab(unittest.TestCase):
    def test_controls_and_engine_present(self):
        for needle in ("id='lab-form'", "id='seed'", "id='seed-random'", "data-preset='miss'", "data-preset='false_flag'", "const Engine ="):
            self.assertIn(needle, PAGE)

    def test_script_cannot_be_closed_early_by_data(self):
        scripts = re.findall(r'<script id="data" type="application/json">(.*?)</script>', PAGE, re.S)
        self.assertEqual(len(scripts), 1)
        self.assertNotIn("</", scripts[0])

    def test_engine_uses_the_python_thresholds(self):
        self.assertEqual(site.engine_config()["thresholds"], {"oi": 5.0, "iv": 3.5, "volume": 3.5})


if __name__ == "__main__":
    unittest.main()
