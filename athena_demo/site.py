"""Render the analytics as one self-contained static HTML page (no CDN, no JS libraries)."""
from __future__ import annotations

import html
import json
import pathlib

from . import analytics, anomaly, backtest, evaluation, synthetic
from .analytics import DISCLAIMER

HERE = pathlib.Path(__file__).parent
CALL_COLOUR, PUT_COLOUR, FLAG_COLOUR = "#3987e5", "#d95926", "#f0e442"  # safe under colour-blindness simulation
GRID_COLOUR = "#30363d"

# The browser itself refuses any network request from this page
CSP = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"

CSS = f"""
:root{{--bg:#0d1117;--panel:#161b22;--raised:#1f2630;--atm:#1c2b3a;--itm:#1a2029;--line:#30363d;--control:#7d8590;--text:#e6edf3;--mute:#a8b3bf;--ce:{CALL_COLOUR};--pe:{PUT_COLOUR};--acc:#79c0ff;--flag:{FLAG_COLOUR};--warn-bg:#3b2300;--warn:#f0c674}}
*{{box-sizing:border-box}}html{{scroll-behavior:auto}}body{{margin:0;font:15px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--text)}}
a{{color:var(--acc)}}:focus-visible{{outline:3px solid var(--acc);outline-offset:2px}}
.skip{{position:absolute;left:-999px;background:var(--panel);padding:8px 12px}}.skip:focus{{left:8px;top:8px;z-index:2}}
.sr{{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}}
.banner{{background:var(--warn-bg);border-bottom:1px solid var(--warn);color:var(--warn);padding:8px 24px;font-weight:600}}
.wrap{{max-width:1180px;margin:auto;padding:0 24px}}
.hero{{padding:36px 0 12px}}.eyebrow{{color:var(--mute);font-size:13px;margin:0 0 8px}}
h1{{font-size:clamp(26px,4.4vw,40px);line-height:1.15;margin:0 0 14px;max-width:24em}}h2{{font-size:20px;margin:0 0 12px}}h3{{font-size:15px;margin:0 0 8px}}
.lede{{font-size:17px;max-width:46em;margin:0 0 12px}}.cta{{display:inline-block;margin:6px 0 18px;padding:10px 16px;border-radius:6px;background:var(--acc);color:#0d1117;font-weight:700;text-decoration:none}}
section.block{{padding:18px 0}}.steps{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:12px;margin:0;padding:0;list-style:none}}
.steps li{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px}}.steps p{{margin:0}}
.guide{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:4px 28px;margin:12px 0 0}}.guide dt{{font-weight:700;margin-top:10px}}.guide dd{{margin:0;color:var(--mute)}}
.tabs{{display:flex;gap:6px;flex-wrap:wrap}}.tab{{margin-bottom:14px}}.bar{{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;margin-bottom:12px}}
button{{font:inherit;background:var(--panel);color:var(--text);border:1px solid var(--control);border-radius:6px;padding:7px 12px;cursor:pointer;min-height:38px}}
button.on{{background:var(--acc);border-color:var(--acc);color:#0d1117;font-weight:600}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:14px}}.two{{display:grid;grid-template-columns:1fr 2fr;gap:10px}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px;min-width:0}}.card b{{display:block;font-size:22px;overflow-wrap:anywhere}}.card span{{color:var(--mute);font-size:13px}}
.panel{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px;margin-bottom:14px;min-width:0}}.scroll,.chart{{overflow-x:auto}}
summary{{cursor:pointer;font-weight:600;padding:2px 0}}details[open] summary{{margin-bottom:10px}}
table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:13px}}th,td{{padding:5px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}}
th{{color:var(--mute);font-weight:500}}td.k,th.k{{text-align:center;font-weight:700;background:var(--raised)}}.l{{text-align:left!important}}td.wrap-text{{white-space:normal;min-width:16em}}
tr.atm td{{background:var(--atm)}}td.itm{{background:var(--itm)}}td.flag{{outline:2px solid var(--flag);outline-offset:-2px;font-weight:700}}
.mute{{color:var(--mute)}}.pill{{display:inline-block;padding:2px 8px;border-radius:12px;border:1px solid var(--warn);color:var(--warn);font-size:12px;font-weight:400}}
.leg{{display:inline-flex;align-items:center;gap:5px;margin-right:12px}}.legend{{margin:0 0 8px;font-size:13px}}.sw{{display:inline-block;width:10px;height:10px;border-radius:50%}}.sw.ce{{background:var(--ce)}}.sw.pe{{background:var(--pe)}}
.key-ring{{display:inline-block;width:12px;height:12px;border-radius:50%;border:2px solid var(--flag)}}.key-ring.miss{{border-style:dashed}}
.charts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:14px}}
svg text{{fill:var(--mute);font-size:12px}}svg text.ct{{fill:var(--text);font-weight:600;font-size:13px}}.axis{{stroke:var(--line)}}.limit{{stroke:var(--flag);stroke-dasharray:4}}
.dot.ce{{fill:var(--ce)}}.dot.pe{{fill:var(--pe)}}.ring{{fill:none;stroke:var(--flag);stroke-width:2}}.ring.miss{{stroke-dasharray:3}}.hit{{fill:transparent}}
#lab-form{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 8px}}#seed{{font:inherit;width:8em;min-height:38px;padding:6px 8px;background:var(--bg);color:var(--text);border:1px solid var(--control);border-radius:6px}}#seed[aria-invalid=true]{{border-color:var(--flag)}}
#lab-status{{margin:0 0 14px;color:var(--mute)}}.view{{display:none}}.view.on{{display:block}}
footer{{color:var(--mute);font-size:13px;padding:16px 0 28px;border-top:1px solid var(--line);margin-top:12px}}
@media (max-width:720px){{.wrap{{padding:0 14px}}.banner{{padding:8px 14px}}.two{{grid-template-columns:1fr}}.chart svg{{min-width:600px}}button{{min-height:44px}}#seed{{min-height:44px}}.hero{{padding-top:22px}}.lede{{font-size:16px}}}}
@media (forced-colors:active){{.ring,.dot.ce,.dot.pe,.limit{{forced-color-adjust:none}}}}
"""

JS = (HERE / "engine.js").read_text(encoding="utf-8") + (HERE / "ui.js").read_text(encoding="utf-8")


REFERENCE_SEED = 7


def esc(x) -> str:
    return html.escape(str(x))


def inr(x: float) -> str:
    return ("−" if x < 0 else "") + f"₹{abs(x):,.0f}"


def fmt_int(n: float) -> str:
    n = float(n)
    for unit, div in (("Cr", 1e7), ("L", 1e5)):
        if abs(n) >= div:
            return f"{n / div:.2f} {unit}"
    return f"{n:,.0f}"


# ---------- SVG helpers ----------
def line_chart(series: list[tuple[str, list[float], str]], w=900, h=260, pad=42, zero=False, xlabel="", label="Line chart") -> str:
    allv = [v for _, vals, _ in series for v in vals if v is not None]
    lo, hi = min(allv), max(allv)
    if zero:
        lo, hi = min(lo, 0), max(hi, 0)
    if hi == lo:
        hi = lo + 1
    n = max(len(vals) for _, vals, _ in series)
    sx = lambda i: pad + (w - 2 * pad) * i / max(n - 1, 1)
    sy = lambda v: h - pad + (pad * 2 - h) * (v - lo) / (hi - lo)
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{esc(label)}">']
    for t in range(5):
        v = lo + (hi - lo) * t / 4
        out.append(f'<line x1="{pad}" x2="{w-pad}" y1="{sy(v):.1f}" y2="{sy(v):.1f}" stroke="{GRID_COLOUR}"/>'
                   f'<text x="4" y="{sy(v)+4:.1f}">{v:,.0f}</text>')
    if zero:
        out.append(f'<line x1="{pad}" x2="{w-pad}" y1="{sy(0):.1f}" y2="{sy(0):.1f}" stroke="#a8b3bf" stroke-dasharray="4"/>')
    for name, vals, colour in series:
        pts = " ".join(f"{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(vals) if v is not None)
        out.append(f'<polyline fill="none" stroke="{colour}" stroke-width="1.8" points="{pts}"><title>{esc(name)}</title></polyline>')
    lx = pad
    for name, _, colour in series:
        out.append(f'<rect x="{lx}" y="6" width="10" height="10" fill="{colour}"/><text x="{lx+14}" y="15">{esc(name)}</text>')
        lx += 14 + 8 * len(name) + 16
    if xlabel:
        out.append(f'<text x="{w/2:.0f}" y="{h-6}" text-anchor="middle">{esc(xlabel)}</text>')
    out.append("</svg>")
    return "".join(out)


def oi_bars(chain: dict, w=900, h=280, pad=46) -> str:
    rows = chain["rows"]
    mx = max(max(r["CE"]["oi"], r["PE"]["oi"]) for r in rows)
    bw = (w - 2 * pad) / len(rows)
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Open interest by strike for calls and puts, with the planted OI spike outlined.">']
    for i, r in enumerate(rows):
        x = pad + i * bw
        for j, kind in enumerate(("CE", "PE")):
            v = r[kind]["oi"]
            bh = (h - 2 * pad) * v / mx
            colour = CALL_COLOUR if kind == "CE" else PUT_COLOUR
            stroke = f' stroke="{FLAG_COLOUR}" stroke-width="2"' if r[kind]["anomaly"] == "oi_spike" else ""
            out.append(f'<rect x="{x + j * bw / 2 + 1:.1f}" y="{h - pad - bh:.1f}" width="{bw / 2 - 2:.1f}" height="{bh:.1f}" fill="{colour}"{stroke}>'
                       f'<title>{r["strike"]} {kind} OI {fmt_int(v)}</title></rect>')
        if i % 3 == 0:
            out.append(f'<text x="{x + bw / 2:.1f}" y="{h - pad + 14}" text-anchor="middle">{r["strike"]}</text>')
        if r["strike"] == chain["atm"]:
            out.append(f'<line x1="{x + bw / 2:.1f}" x2="{x + bw / 2:.1f}" y1="{pad}" y2="{h - pad}" stroke="#79c0ff" stroke-dasharray="4"/>'
                       f'<text x="{x + bw / 2 + 4:.1f}" y="{pad - 4}">ATM</text>')
    out.append(f'<rect x="{pad}" y="6" width="10" height="10" fill="{CALL_COLOUR}"/><text x="{pad+14}" y="15">Call OI</text>'
               f'<rect x="{pad+80}" y="6" width="10" height="10" fill="{PUT_COLOUR}"/><text x="{pad+94}" y="15">Put OI</text>'
               f'<text x="{pad+170}" y="15">yellow outline = planted OI spike</text></svg>')
    return "".join(out)


# ---------- views ----------
def view_chain(c: dict) -> str:
    head = ("<tr><th>OI</th><th>ΔOI</th><th>Vol</th><th>IV%</th><th>Δ</th><th>LTP</th>"
            "<th class='k'>Strike</th><th>LTP</th><th>Δ</th><th>IV%</th><th>Vol</th><th>ΔOI</th><th>OI</th></tr>")
    body = []
    for r in c["rows"]:
        ce, pe, k = r["CE"], r["PE"], r["strike"]
        cls = "atm" if k == c["atm"] else ""
        cc = "itm" if k < c["spot"] else ""
        pc = "itm" if k > c["spot"] else ""

        def cell(leg, base, kind, text):
            planted = leg["anomaly"] == kind
            return f"<td class='{base}{' flag' if planted else ''}'>{'⚑ ' if planted else ''}{text}</td>"
        body.append(
            f"<tr class='{cls}'>{cell(ce, cc, 'oi_spike', fmt_int(ce['oi']))}<td class='{cc}'>{fmt_int(ce['oi']-ce['prev_oi'])}</td>"
            f"{cell(ce, cc, 'volume_burst', fmt_int(ce['volume']))}{cell(ce, cc, 'iv_kink', format(ce['iv'], '.2f'))}<td class='{cc}'>{ce['delta']:.2f}</td>"
            f"<td class='{cc}'>{ce['ltp']:,.2f}</td><td class='k'>{k}</td><td class='{pc}'>{pe['ltp']:,.2f}</td>"
            f"<td class='{pc}'>{pe['delta']:.2f}</td>{cell(pe, pc, 'iv_kink', format(pe['iv'], '.2f'))}{cell(pe, pc, 'volume_burst', fmt_int(pe['volume']))}"
            f"<td class='{pc}'>{fmt_int(pe['oi']-pe['prev_oi'])}</td>{cell(pe, pc, 'oi_spike', fmt_int(pe['oi']))}</tr>")
    return (f"<div class='panel'><h2>Option chain · {c['index']} weekly · {c['days_to_expiry']} days to expiry</h2>"
            f"<p class='mute'>Calls left, puts right. Shaded = in the money. Blue row = ATM. ⚑ with a yellow outline = the value that was planted as an anomaly (ground truth, reference seed {REFERENCE_SEED}).</p>"
            f"<div class='scroll' tabindex='0' role='region' aria-label='Option chain table'><table><thead>{head}</thead><tbody>{''.join(body)}</tbody></table></div></div>")


def view_iv(c: dict) -> str:
    s = analytics.iv_greeks_summary(c)
    cards = [("ATM IV", f"{s['atm_iv']}%"), ("Put − call skew", f"{s['skew_put_minus_call']} vol pts"),
             ("ATM straddle", f"₹{s['atm_straddle']:,.2f}"), ("Implied move to expiry", f"±{s['implied_move_pct']}%"),
             ("Straddle theta / lot / day", inr(s["straddle_theta_per_lot"])), ("Straddle vega / lot / vol pt", f"₹{s['straddle_vega_per_lot']:,.0f}")]
    g = "".join(f"<div class='card'><span>{a}</span><b>{b}</b></div>" for a, b in cards)
    greeks = "".join(
        f"<tr><td style='text-align:left'>{name}</td>" + "".join(f"<td>{s[key][x]:.4f}</td>" for x in ("delta", "gamma", "vega", "theta")) + "</tr>"
        for name, key in (("ATM call", "atm_call_greeks"), ("ATM put", "atm_put_greeks")))
    strikes = [r["strike"] for r in c["rows"]]
    smile = line_chart([("Call IV %", [r["CE"]["iv"] for r in c["rows"]], CALL_COLOUR),
                        ("Put IV %", [r["PE"]["iv"] for r in c["rows"]], PUT_COLOUR)],
                       xlabel=f"strikes {strikes[0]} → {strikes[-1]}", label="Implied volatility by strike for calls and puts.")
    return (f"<div class='grid'>{g}</div><div class='panel'><h2>Volatility smile</h2><div class='chart'>{smile}</div></div>"
            f"<div class='panel'><h2>ATM Greeks (Black-Scholes, r = {c['risk_free']*100:.1f}%)</h2><table><tr><th style='text-align:left'>Leg</th>"
            f"<th>Delta</th><th>Gamma</th><th>Vega / vol pt</th><th>Theta / day</th></tr>{greeks}</table></div>")


def view_oi(c: dict) -> str:
    p = analytics.pcr(c)
    mp = analytics.max_pain(c)
    cards = [("PCR (OI)", p["oi_pcr"]), ("PCR (volume)", p["volume_pcr"]), ("Max pain", mp),
             ("Total call OI", fmt_int(p["call_oi"])), ("Total put OI", fmt_int(p["put_oi"]))]
    g = "".join(f"<div class='card'><span>{a}</span><b>{b}</b></div>" for a, b in cards)
    counts = analytics.buildup_counts(c)
    rows = "".join(f"<tr><td style='text-align:left'>{esc(k)}</td><td>{v}</td></tr>" for k, v in counts.items())
    top = sorted(analytics.oi_buildup(c), key=lambda b: -abs(b["oi_change"]))[:8]
    trows = "".join(f"<tr><td>{b['strike']}</td><td>{b['kind']}</td><td>{b['price_change']:+.2f}</td>"
                    f"<td>{fmt_int(b['oi_change'])}</td><td style='text-align:left'>{b['label']}</td></tr>" for b in top)
    return (f"<div class='grid'>{g}</div><div class='panel'><h2>Open interest by strike</h2><div class='chart'>{oi_bars(c)}</div></div>"
            f"<div class='two'><div class='panel'><h2>Build-up mix</h2><table>{rows}</table>"
            f"<p class='mute'>Price ↑ OI ↑ long build-up · price ↓ OI ↑ short build-up · price ↑ OI ↓ short covering · price ↓ OI ↓ long unwinding.</p></div>"
            f"<div class='panel'><h2>Largest OI changes</h2><table><tr><th>Strike</th><th>Leg</th><th>ΔLTP</th><th>ΔOI</th><th style='text-align:left'>Reading</th></tr>{trows}</table></div></div>")


def view_signal(c: dict) -> str:
    sig = analytics.explain_signal(c)
    rows = "".join(f"<tr><td style='text-align:left'>{esc(f['name'])}</td><td>{f['vote']:+d}</td>"
                   f"<td class='l wrap-text'>{esc(f['why'])}</td></tr>" for f in sig["factors"])
    return (f"<div class='panel'><h2>Signal explainer <span class='pill'>{esc(DISCLAIMER)}</span></h2>"
            f"<div class='grid'><div class='card'><span>Combined reading</span><b>{sig['tilt']}</b></div><div class='card'><span>Score (sum of votes)</span><b>{sig['score']:+d}</b></div></div>"
            f"<div class='scroll'><table><tr><th style='text-align:left'>Factor</th><th>Vote</th><th style='text-align:left'>Why</th></tr>{rows}</table></div>"
            "<p class='mute'>Every factor is a plain rule you can read in <code>athena_demo/analytics.py</code>. The reading describes "
            "synthetic data only; it is not a recommendation to buy or sell anything.</p></div>")


def view_anomaly(c: dict) -> str:
    """Findings for the reference seed. Shown without JavaScript; the seed lab replaces it otherwise."""
    truth, _ = anomaly.compare(c)
    rows = "".join(f"<tr><td>{f['strike']}</td><td>{f['kind']}</td><td class='l'>{f['type']}</td><td>{f['z']:+.2f}</td>"
                   f"<td class='l'>{'Hit' if (f['strike'], f['kind'], f['type']) in truth else 'False flag'}</td><td class='l'>{esc(f['why'])}</td></tr>"
                   for f in anomaly.detect(c)) or "<tr><td colspan=6>None</td></tr>"
    return (f"<div class='panel'><h3>{c['index']}, seed {REFERENCE_SEED}</h3><div class='scroll'><table><tr><th>Strike</th><th>Leg</th><th class='l'>Type</th><th>Robust z</th>"
            f"<th class='l'>Verdict</th><th class='l'>Explanation</th></tr>{rows}</table></div></div>")


def view_backtest(name: str, path: list[dict], bt: dict, lot: int) -> str:
    cards = [("Hypothetical P&L", inr(bt["final_pnl"])), ("Max drawdown", inr(bt["max_drawdown"])),
             ("Position switches", bt["switches"]), ("Hit rate (days in market)", bt["hit_rate"]), ("Lot size (illustrative)", lot)]
    g = "".join(f"<div class='card'><span>{a}</span><b>{b}</b></div>" for a, b in cards)
    eq = line_chart([("Cumulative paper P&L (₹)", bt["equity"], CALL_COLOUR)], zero=True, xlabel="synthetic trading days", label="Cumulative hypothetical P&L over synthetic trading days.")
    px = line_chart([(f"Synthetic {name} close", [p["close"] for p in path], CALL_COLOUR),
                     ("20-day average", backtest.sma([p["close"] for p in path], 20), PUT_COLOUR)], xlabel="synthetic trading days", label="Synthetic index close and its 20-day average.")
    return (f"<div class='grid'>{g}</div><div class='panel'><h2>Paper P&L on a synthetic path <span class='pill'>hypothetical · no orders</span></h2><div class='chart'>{eq}</div>"
            "<p class='mute'>Rule: long when PCR &gt; 1.1 and close &gt; 20-day average; short when PCR &lt; 0.9 and close &lt; average; otherwise flat. "
            f"₹{backtest.COST_PER_SWITCH:.0f} cost per switch. Past or simulated results say nothing about the future.</p></div>"
            f"<div class='panel'><h2>Synthetic index path</h2><div class='chart'>{px}</div></div>")


def engine_config() -> dict:
    return {"indices": synthetic.INDICES, "risk_free": synthetic.RISK_FREE, "days_to_expiry": synthetic.DAYS_TO_EXPIRY,
            "strikes_each_side": synthetic.N_STRIKES_EACH_SIDE,
            "thresholds": {"oi": anomaly.OI_THRESHOLD, "iv": anomaly.THRESHOLD, "volume": anomaly.THRESHOLD}}


def _metric(x) -> str:
    return "n/a" if x is None else f"{x:.3f}"


def _hero() -> str:
    test = evaluation.report()["test_seeds_1000_1199"]
    cards = [("Precision", _metric(test["precision"])), ("Recall", _metric(test["recall"])), ("F1", _metric(test["f1"])),
             ("False flags per clean chain", f"{test['false_flags_per_clean_chain']:.2f}")]
    stats = "".join(f"<div class='card'><span>{a}</span><b>{b}</b></div>" for a, b in cards)
    return (
        "<section class='hero'><p class='eyebrow'>Aegython 2026 · Track 2: Find the Anomaly</p>"
        "<h1>Find the anomaly in an option chain, and see exactly why it was flagged</h1>"
        "<p class='lede'>A single options expiry is a wall of numbers: 31 strikes, each with a call and a put, each with its own open interest, "
        "implied volatility and volume. That is 186 values for one value out of line to hide among, and in practice nobody has labels saying which ones are wrong. "
        "So a useful detector has to work without labels, declare its rules in advance and explain every flag.</p>"
        "<p class='lede'>ATHENA does that with three plain statistical checks. To measure it honestly, the generator plants three labelled anomalies "
        "in each synthetic chain. The detector never sees those labels; they are used only to mark its answers.</p>"
        "<a class='cta' href='#lab'>Try a seed yourself</a>"
        f"<h2>Held-out result <span class='mute' style='font-size:14px;font-weight:400'>· seeds 1000–1199, {test['chains']} synthetic chains, {test['planted']:,} planted anomalies</span></h2>"
        f"<div class='grid'>{stats}</div></section>")


def _how_it_works() -> str:
    steps = [("1. Predict the normal value",
              "<b>OI</b>: the median of the 3 strikes either side (on log OI). <b>IV</b>: a quadratic smile fitted across all strikes. "
              "<b>Volume</b>: the chain's typical log(volume ÷ OI). The gap between the actual and predicted value is the residual."),
             ("2. Measure how unusual the gap is",
              "Each residual becomes a <b>robust z-score</b>: 0.6745 × (residual − median) ÷ MAD. The median and MAD barely move when one value is extreme, "
              "so an outlier can't hide by inflating the spread, as it can with a mean and standard deviation."),
             ("3. Flag it against a declared threshold",
              f"OI spike: z &gt; {anomaly.OI_THRESHOLD}. IV kink: |z| &gt; {anomaly.THRESHOLD}. Volume burst: z &gt; {anomaly.THRESHOLD}. "
              "Chosen on tuning seeds 0–49 only, then scored on seeds that played no part in choosing them. Every flag shows its score and reason.")]
    items = "".join(f"<li><h3>{a}</h3><p>{b}</p></li>" for a, b in steps)
    return f"<section class='block'><h2>How the detection works</h2><ol class='steps'>{items}</ol></section>"


def _how_to_read() -> str:
    terms = [("Robust z-score", "How many typical spreads a value sits from normal. Higher means stranger. It is a ranking, not a probability."),
             ("✓ Hit, ✕ False flag, ○ Missed", "Hit: flagged and planted. False flag: flagged but not planted. Missed: planted but under the threshold."),
             ("Dots and rings", "Blue dots are calls and orange dots are puts. A yellow ring marks a flag, a dashed ring marks a miss, and the dashed line is the threshold."),
             ("Seeds", "A seed fixes every random draw, so one seed always gives one chain. 0–49 tuned the thresholds; 1000–1199 are held out. Results vary by seed: try the failure examples."),
             ("Open interest (OI), volume", "OI is the number of contracts still open. Volume is the number traded in the session."),
             ("Implied volatility (IV), smile", "IV is the volatility implied by an option's price. Plotted across strikes it forms a smooth curve, the smile, so a sudden break stands out."),
             ("ATM, call (CE), put (PE)", "ATM is the strike nearest the index level. CE and PE are the exchange's labels for calls and puts."),
             ("What this is not", "Everything is synthetic, so a flag here says nothing about any real market, and nothing here is a suggestion to trade.")]
    items = "".join(f"<div><dt>{a}</dt><dd>{b}</dd></div>" for a, b in terms)
    return (f"<section class='block'><details class='panel' open><summary>How to read this page</summary><dl class='guide'>{items}</dl></details></section>")


TYPE_NAMES = {"oi_spike": "OI spike", "iv_kink": "IV kink", "volume_burst": "Volume burst"}


def _evidence() -> str:
    rep = evaluation.report()
    test, tune = rep["test_seeds_1000_1199"], rep["tuning_seeds_0_49"]

    def row(name, m):
        return (f"<tr><td class='l'>{name}</td><td>{m['planted']}</td><td>{m['flagged']}</td><td>{m['true_positives']}</td><td>{m['false_positives']}</td>"
                f"<td>{m['false_negatives']}</td><td>{_metric(m['precision'])}</td><td>{_metric(m['recall'])}</td><td>{_metric(m['f1'])}</td></tr>")
    head = ("<tr><th class='l'>Anomaly type</th><th>Planted</th><th>Flagged</th><th>TP</th><th>FP</th><th>FN</th><th>Precision</th><th>Recall</th><th>F1</th></tr>")
    rows = "".join(row(TYPE_NAMES[t], test["by_type"][t]) for t in anomaly.TYPES) + row("<b>All types</b>", test)
    sweep = "".join(
        f"<tr><td>{float(s) * 100:.0f}%</td>" + "".join(f"<td>{_metric(v['by_type'][t]['recall'])}</td>" for t in anomaly.TYPES)
        + f"<td>{_metric(v['recall'])}</td><td>{_metric(v['precision'])}</td><td>{_metric(v['f1'])}</td></tr>"
        for s, v in rep["stress_seeds_2000_2099"].items())
    return (
        "<section class='block'><h2>Evidence and limits</h2>"
        f"<div class='panel'><h3>Held-out test, per anomaly type (seeds 1000–1199)</h3><div class='scroll' tabindex='0' role='region' aria-label='Held-out results'><table>{head}{rows}</table></div>"
        f"<p class='mute'>Tuning seeds 0–49 for comparison: precision {_metric(tune['precision'])}, recall {_metric(tune['recall'])}, F1 {_metric(tune['f1'])}. "
        "Each number on this page is computed when the page is built, by the same code as <code>scripts/evaluate_anomaly.py</code>.</p></div>"
        "<div class='panel'><h3>Stress test: random legs, weaker anomalies (seeds 2000–2099)</h3>"
        f"<div class='scroll' tabindex='0' role='region' aria-label='Stress test results'><table><tr><th>Anomaly size</th>{''.join(f'<th>{TYPE_NAMES[t]} recall</th>' for t in anomaly.TYPES)}<th>Recall</th><th>Precision</th><th>F1</th></tr>{sweep}</table></div>"
        "<p class='mute'>In the standard chains every anomaly sits on the same leg at the same size, which flatters any detector. "
        "Here each lands on a random leg, scaled from a quarter of the standard size up to full size. Thresholds are unchanged.</p></div>"
        "<div class='panel'><h3>Limitations</h3><ul class='mute' style='margin:0;padding-left:20px'>"
        "<li>The data is synthetic and cleaner than a real market, so these scores do not predict performance on real chains.</li>"
        "<li>Test seeds come from the same generator as the tuning seeds. They test for overfitting to particular random draws, not for a change in the data's structure.</li>"
        "<li>IV kink precision is the weakest result: its false flags mostly occur away from round-number strikes.</li>"
        "<li>The OI detector misses small spikes, as the stress table shows, because its threshold is set high: round-number strikes legitimately carry more OI than their neighbours.</li></ul></div></section>")


def build(seed: int = REFERENCE_SEED) -> str:
    payload = {"config": engine_config(), "default_seed": seed,
               "presets": {name: evaluation.example_seeds(name) for name in synthetic.INDICES}}
    views = []
    tabs = [("anomaly", "Anomalies"), ("chain", "Option chain"), ("iv", "IV & Greeks"), ("oi", "PCR & OI build-up"),
            ("signal", "Signal explainer"), ("backtest", "Paper P&L")]
    static_findings = []
    for name in synthetic.INDICES:
        c = synthetic.option_chain(name, seed=seed)
        path = synthetic.price_path(name)
        bt = backtest.run(path, c["lot"])
        static_findings.append(view_anomaly(c))
        rendered = {"chain": view_chain(c), "iv": view_iv(c), "oi": view_oi(c), "signal": view_signal(c),
                    "backtest": view_backtest(name, path, bt, c["lot"])}
        head = (f"<div class='grid'><div class='card'><span>{name} spot (synthetic)</span><b>{c['spot']:,.2f}</b></div>"
                f"<div class='card'><span>Change</span><b>{c['spot']-c['prev_spot']:+,.2f}</b></div>"
                f"<div class='card'><span>ATM strike</span><b>{c['atm']}</b></div></div>")
        for key, body in rendered.items():
            views.append(f"<section class='view' data-idx='{name}' data-tab='{key}'>{head}<p class='mute'>This tab shows reference seed {seed}. The seed picker is on the Anomalies tab.</p>{body}</section>")
    lab = ("<section class='view' data-idx='all' data-tab='anomaly'>"
           "<form id='lab-form' novalidate><label for='seed'>Seed</label>"
           f"<input id='seed' type='number' inputmode='numeric' min='0' max='999999' step='1' value='{seed}'>"
           "<button type='submit'>Generate chain</button><button type='button' id='seed-random'>Random seed</button>"
           "<span class='mute'>Examples from the held-out seeds:</span>"
           "<button type='button' data-preset='clean'>All correct</button><button type='button' data-preset='false_flag'>A false flag</button><button type='button' data-preset='miss'>A miss</button></form>"
           "<p id='lab-status' role='status' aria-live='polite'></p>"
           f"<div id='lab-out'>{''.join(static_findings)}</div></section>")
    idx_buttons = "".join(f"<button type='button' data-idx='{n}'>{n}</button>" for n in synthetic.INDICES)
    tab_buttons = "".join(f"<button type='button' role='tab' data-tab='{k}'>{v}</button>" for k, v in tabs)
    data_json = json.dumps(payload).replace("</", "<\\/")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<title>ATHENA Analytics Demo · explainable anomaly detection on synthetic option chains</title><style>{CSS}</style>
<noscript><style>.view{{display:block}}#lab-form{{display:none}}</style></noscript></head><body>
<a class="skip" href="#lab">Skip to the anomaly lab</a>
<div class="banner" role="note">⚠ Educational demo on synthetic data. Not investment advice. No trading, no orders, no broker connection, no real market data.</div>
<div class="wrap"><header>{_hero()}</header>
<main>{_how_it_works()}{_how_to_read()}
<section class="block" id="lab"><div class="bar"><h2 style="margin:0">Explore a chain</h2><div class="tabs idx" role="group" aria-label="Index">{idx_buttons}</div></div>
<div class="tabs tab" role="tablist" aria-label="Views">{tab_buttons}</div>{lab}{''.join(views)}</section>
{_evidence()}</main>
<footer>Generated by <code>python3 -m athena_demo.build</code>. All prices, open interest and paths are synthetic, and this page makes no network requests.
MIT licensed. Educational only: nothing here is a recommendation to trade.</footer></div>
<script id="data" type="application/json">{data_json}</script><script>{JS}</script></body></html>"""
