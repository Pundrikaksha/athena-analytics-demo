"""Render the analytics as one self-contained static HTML page (no CDN, no JS libraries)."""
from __future__ import annotations

import html
import json

from . import analytics, anomaly, backtest, synthetic
from .analytics import DISCLAIMER

CSS = """
:root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--text:#e6edf3;--mute:#8b949e;--ce:#3fb950;--pe:#f85149;--acc:#58a6ff;--warn:#d29922}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--text)}
header{padding:18px 24px;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between}
h1{font-size:20px;margin:0}h2{font-size:16px;margin:0 0 10px}h3{font-size:14px;margin:14px 0 6px;color:var(--mute)}
.banner{background:#3b2300;border:1px solid var(--warn);color:#f0c674;padding:8px 24px;font-weight:600}
main{padding:16px 24px;max-width:1280px;margin:auto}.tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px}
.tabs button{background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:6px 12px;cursor:pointer}
.tabs button.on{border-color:var(--acc);color:var(--acc)}.idx button.on{background:var(--acc);color:#000}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin-bottom:14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px}.card b{display:block;font-size:20px}
.card span{color:var(--mute);font-size:12px}.panel{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px;margin-bottom:14px;overflow-x:auto}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:12.5px}th,td{padding:4px 8px;border-bottom:1px solid var(--line);text-align:right}
th{color:var(--mute);font-weight:500;position:sticky;top:0;background:var(--panel)}td.k{text-align:center;font-weight:700;background:#1f2630}
tr.atm td{background:#1c2b3a}.itm{background:#132017}.flag{outline:2px solid var(--warn)}
.ce{color:var(--ce)}.pe{color:var(--pe)}.mute{color:var(--mute)}.pill{display:inline-block;padding:2px 8px;border-radius:12px;border:1px solid var(--line);font-size:12px}
.v1{color:var(--ce)}.v-1{color:var(--pe)}.v0{color:var(--mute)}svg text{fill:var(--mute);font-size:11px}
.view{display:none}.view.on{display:block}footer{color:var(--mute);font-size:12px;padding:16px 24px;border-top:1px solid var(--line)}
"""

JS = """
const DATA = JSON.parse(document.getElementById('data').textContent);
let idx = Object.keys(DATA)[0], tab = 'chain';
function show(){document.querySelectorAll('.view').forEach(v=>v.classList.toggle('on',v.dataset.idx===idx&&v.dataset.tab===tab));
document.querySelectorAll('.idx button').forEach(b=>b.classList.toggle('on',b.dataset.idx===idx));
document.querySelectorAll('.tab button').forEach(b=>b.classList.toggle('on',b.dataset.tab===tab));
const h=new URLSearchParams(location.hash.slice(1));}
document.querySelectorAll('.idx button').forEach(b=>b.onclick=()=>{idx=b.dataset.idx;show()});
document.querySelectorAll('.tab button').forEach(b=>b.onclick=()=>{tab=b.dataset.tab;show()});
const p=new URLSearchParams(location.hash.slice(1));if(p.get('idx'))idx=p.get('idx');if(p.get('tab'))tab=p.get('tab');show();
"""


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
def line_chart(series: list[tuple[str, list[float], str]], w=900, h=260, pad=42, zero=False, xlabel="") -> str:
    allv = [v for _, vals, _ in series for v in vals if v is not None]
    lo, hi = min(allv), max(allv)
    if zero:
        lo, hi = min(lo, 0), max(hi, 0)
    if hi == lo:
        hi = lo + 1
    n = max(len(vals) for _, vals, _ in series)
    sx = lambda i: pad + (w - 2 * pad) * i / max(n - 1, 1)
    sy = lambda v: h - pad + (pad * 2 - h) * (v - lo) / (hi - lo)
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img">']
    for t in range(5):
        v = lo + (hi - lo) * t / 4
        out.append(f'<line x1="{pad}" x2="{w-pad}" y1="{sy(v):.1f}" y2="{sy(v):.1f}" stroke="#30363d"/>'
                   f'<text x="4" y="{sy(v)+4:.1f}">{v:,.0f}</text>')
    if zero:
        out.append(f'<line x1="{pad}" x2="{w-pad}" y1="{sy(0):.1f}" y2="{sy(0):.1f}" stroke="#8b949e" stroke-dasharray="4"/>')
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
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img">']
    for i, r in enumerate(rows):
        x = pad + i * bw
        for j, kind in enumerate(("CE", "PE")):
            v = r[kind]["oi"]
            bh = (h - 2 * pad) * v / mx
            colour = "#3fb950" if kind == "CE" else "#f85149"
            stroke = ' stroke="#d29922" stroke-width="2"' if r[kind]["anomaly"] else ""
            out.append(f'<rect x="{x + j * bw / 2 + 1:.1f}" y="{h - pad - bh:.1f}" width="{bw / 2 - 2:.1f}" height="{bh:.1f}" fill="{colour}"{stroke}>'
                       f'<title>{r["strike"]} {kind} OI {fmt_int(v)}</title></rect>')
        if i % 3 == 0:
            out.append(f'<text x="{x + bw / 2:.1f}" y="{h - pad + 14}" text-anchor="middle">{r["strike"]}</text>')
        if r["strike"] == chain["atm"]:
            out.append(f'<line x1="{x + bw / 2:.1f}" x2="{x + bw / 2:.1f}" y1="{pad}" y2="{h - pad}" stroke="#58a6ff" stroke-dasharray="4"/>'
                       f'<text x="{x + bw / 2 + 4:.1f}" y="{pad - 4}">ATM</text>')
    out.append(f'<rect x="{pad}" y="6" width="10" height="10" fill="#3fb950"/><text x="{pad+14}" y="15">Call OI</text>'
               f'<rect x="{pad+80}" y="6" width="10" height="10" fill="#f85149"/><text x="{pad+94}" y="15">Put OI</text>'
               f'<text x="{pad+170}" y="15">gold outline = planted anomaly</text></svg>')
    return "".join(out)


# ---------- views ----------
def view_chain(c: dict) -> str:
    head = ("<tr><th>OI</th><th>ΔOI</th><th>Vol</th><th>IV%</th><th>Δ</th><th>LTP</th>"
            "<th style='text-align:center'>Strike</th><th>LTP</th><th>Δ</th><th>IV%</th><th>Vol</th><th>ΔOI</th><th>OI</th></tr>")
    body = []
    for r in c["rows"]:
        ce, pe, k = r["CE"], r["PE"], r["strike"]
        cls = "atm" if k == c["atm"] else ""
        cc = "itm" if k < c["spot"] else ""
        pc = "itm" if k > c["spot"] else ""
        f = lambda leg: " flag" if leg["anomaly"] else ""
        body.append(
            f"<tr class='{cls}'><td class='{cc}{f(ce)}'>{fmt_int(ce['oi'])}</td><td class='{cc}'>{fmt_int(ce['oi']-ce['prev_oi'])}</td>"
            f"<td class='{cc}{f(ce)}'>{fmt_int(ce['volume'])}</td><td class='{cc}{f(ce)}'>{ce['iv']:.2f}</td><td class='{cc}'>{ce['delta']:.2f}</td>"
            f"<td class='{cc} ce'>{ce['ltp']:,.2f}</td><td class='k'>{k}</td><td class='{pc} pe'>{pe['ltp']:,.2f}</td>"
            f"<td class='{pc}'>{pe['delta']:.2f}</td><td class='{pc}{f(pe)}'>{pe['iv']:.2f}</td><td class='{pc}{f(pe)}'>{fmt_int(pe['volume'])}</td>"
            f"<td class='{pc}'>{fmt_int(pe['oi']-pe['prev_oi'])}</td><td class='{pc}{f(pe)}'>{fmt_int(pe['oi'])}</td></tr>")
    return (f"<div class='panel'><h2>Option chain · {c['index']} weekly · {c['days_to_expiry']} days to expiry</h2>"
            f"<p class='mute'>Calls left, puts right. Shaded = in the money. Blue row = ATM. Gold outline = planted anomaly (ground truth).</p>"
            f"<table><thead>{head}</thead><tbody>{''.join(body)}</tbody></table></div>")


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
    smile = line_chart([("Call IV %", [r["CE"]["iv"] for r in c["rows"]], "#3fb950"),
                        ("Put IV %", [r["PE"]["iv"] for r in c["rows"]], "#f85149")],
                       xlabel=f"strikes {strikes[0]} → {strikes[-1]}")
    return (f"<div class='grid'>{g}</div><div class='panel'><h2>Volatility smile</h2>{smile}</div>"
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
    trows = "".join(f"<tr><td>{b['strike']}</td><td class='{b['kind'].lower()}'>{b['kind']}</td><td>{b['price_change']:+.2f}</td>"
                    f"<td>{fmt_int(b['oi_change'])}</td><td style='text-align:left'>{b['label']}</td></tr>" for b in top)
    return (f"<div class='grid'>{g}</div><div class='panel'><h2>Open interest by strike</h2>{oi_bars(c)}</div>"
            f"<div class='grid' style='grid-template-columns:1fr 2fr'><div class='panel'><h2>Build-up mix</h2><table>{rows}</table>"
            f"<p class='mute'>Price ↑ OI ↑ long build-up · price ↓ OI ↑ short build-up · price ↑ OI ↓ short covering · price ↓ OI ↓ long unwinding.</p></div>"
            f"<div class='panel'><h2>Largest OI changes</h2><table><tr><th>Strike</th><th>Leg</th><th>ΔLTP</th><th>ΔOI</th><th style='text-align:left'>Reading</th></tr>{trows}</table></div></div>")


def view_signal(c: dict) -> str:
    sig = analytics.explain_signal(c)
    rows = "".join(f"<tr><td style='text-align:left'>{esc(f['name'])}</td><td class='v{f['vote']}'>{f['vote']:+d}</td>"
                   f"<td style='text-align:left'>{esc(f['why'])}</td></tr>" for f in sig["factors"])
    return (f"<div class='panel'><h2>Signal explainer <span class='pill' style='color:#f0c674;border-color:#d29922'>{esc(DISCLAIMER)}</span></h2>"
            f"<div class='grid'><div class='card'><span>Combined reading</span><b>{sig['tilt']}</b></div><div class='card'><span>Score (sum of votes)</span><b>{sig['score']:+d}</b></div></div>"
            f"<table><tr><th style='text-align:left'>Factor</th><th>Vote</th><th style='text-align:left'>Why</th></tr>{rows}</table>"
            "<p class='mute'>Every factor is a plain rule you can read in <code>athena_demo/analytics.py</code>. The reading describes "
            "synthetic data only; it is not a recommendation to buy or sell anything.</p></div>")


def view_anomaly(c: dict) -> str:
    found = anomaly.detect(c)
    ev = anomaly.evaluate(c)
    cards = [("Planted anomalies", ev["planted"]), ("Flagged", ev["flagged"]), ("Precision", ev["precision"]), ("Recall", ev["recall"]),
             ("Thresholds", f"OI z>{anomaly.OI_THRESHOLD} · IV/vol {anomaly.THRESHOLD}")]
    g = "".join(f"<div class='card'><span>{a}</span><b>{b}</b></div>" for a, b in cards)
    rows = "".join(f"<tr><td>{f['strike']}</td><td class='{f['kind'].lower()}'>{f['kind']}</td><td style='text-align:left'>{f['type']}</td>"
                   f"<td>{f['z']:+.2f}</td><td style='text-align:left'>{esc(f['why'])}</td></tr>" for f in found) or "<tr><td colspan=5>None</td></tr>"
    return (f"<div class='grid'>{g}</div><div class='panel'><h2>Anomaly detector (robust z-score, unsupervised)</h2>"
            "<p class='mute'>Three detectors: OI vs neighbouring strikes, IV vs a fitted quadratic smile, and volume/OI turnover. "
            "Each uses a median/MAD robust z-score so one outlier cannot hide itself by inflating the spread. "
            "Ground-truth labels are only used for scoring, never for detection.</p>"
            f"<table><tr><th>Strike</th><th>Leg</th><th style='text-align:left'>Type</th><th>Robust z</th><th style='text-align:left'>Explanation</th></tr>{rows}</table></div>")


def view_backtest(name: str, path: list[dict], bt: dict, lot: int) -> str:
    cards = [("Hypothetical P&L", inr(bt["final_pnl"])), ("Max drawdown", inr(bt["max_drawdown"])),
             ("Position switches", bt["switches"]), ("Hit rate (days in market)", bt["hit_rate"]), ("Lot size (illustrative)", lot)]
    g = "".join(f"<div class='card'><span>{a}</span><b>{b}</b></div>" for a, b in cards)
    eq = line_chart([("Cumulative paper P&L (₹)", bt["equity"], "#58a6ff")], zero=True, xlabel="synthetic trading days")
    px = line_chart([(f"Synthetic {name} close", [p["close"] for p in path], "#e6edf3"),
                     ("20-day average", backtest.sma([p["close"] for p in path], 20), "#d29922")], xlabel="synthetic trading days")
    return (f"<div class='grid'>{g}</div><div class='panel'><h2>Paper P&L on a synthetic path <span class='pill'>hypothetical · no orders</span></h2>{eq}"
            "<p class='mute'>Rule: long when PCR &gt; 1.1 and close &gt; 20-day average; short when PCR &lt; 0.9 and close &lt; average; otherwise flat. "
            f"₹{backtest.COST_PER_SWITCH:.0f} cost per switch. Past or simulated results say nothing about the future.</p></div>"
            f"<div class='panel'><h2>Synthetic index path</h2>{px}</div>")


def build(seed: int = 7) -> str:
    payload, views = {}, []
    tabs = [("chain", "Option chain"), ("iv", "IV & Greeks"), ("oi", "PCR & OI build-up"),
            ("signal", "Signal explainer"), ("anomaly", "Anomalies"), ("backtest", "Paper P&L")]
    for name in synthetic.INDICES:
        c = synthetic.option_chain(name, seed=seed)
        path = synthetic.price_path(name)
        bt = backtest.run(path, c["lot"])
        payload[name] = {"spot": c["spot"], "pcr": analytics.pcr(c), "max_pain": analytics.max_pain(c),
                         "signal": analytics.explain_signal(c)["tilt"], "anomaly_eval": anomaly.evaluate(c),
                         "backtest_final_pnl": bt["final_pnl"]}
        rendered = {"chain": view_chain(c), "iv": view_iv(c), "oi": view_oi(c), "signal": view_signal(c),
                    "anomaly": view_anomaly(c), "backtest": view_backtest(name, path, bt, c["lot"])}
        head = (f"<div class='grid'><div class='card'><span>{name} spot (synthetic)</span><b>{c['spot']:,.2f}</b></div>"
                f"<div class='card'><span>Change</span><b>{c['spot']-c['prev_spot']:+,.2f}</b></div>"
                f"<div class='card'><span>ATM strike</span><b>{c['atm']}</b></div></div>")
        for key, body in rendered.items():
            views.append(f"<section class='view' data-idx='{name}' data-tab='{key}'>{head}{body}</section>")
    idx_buttons = "".join(f"<button data-idx='{n}'>{n}</button>" for n in synthetic.INDICES)
    tab_buttons = "".join(f"<button data-tab='{k}'>{v}</button>" for k, v in tabs)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ATHENA Analytics Demo · synthetic options analytics</title><style>{CSS}</style></head><body>
<div class="banner">⚠ Educational demo on synthetic data. Not investment advice. No trading, no orders, no broker connection, no real market data.</div>
<header><h1>ATHENA Analytics Demo <span class="mute" style="font-size:13px">· NIFTY / BANKNIFTY options, synthetic</span></h1>
<div class="tabs idx">{idx_buttons}</div></header>
<main><div class="tabs tab">{tab_buttons}</div>{''.join(views)}</main>
<footer>Generated by <code>python -m athena_demo.build</code> from a fixed random seed ({seed}). All prices, open interest and paths are synthetic.
MIT licensed. Educational only: nothing here is a recommendation to trade.</footer>
<script id="data" type="application/json">{json.dumps(payload)}</script><script>{JS}</script></body></html>"""
