// In-browser port of synthetic.py, bs.py and anomaly.py. It reproduces Python's random module exactly
// (SHA-512 string seeding + MT19937), so a seed gives the same chain here as in Python.
// tests/test_js_parity.py compares the two. No I/O of any kind.
"use strict";
const Engine = (() => {
  // ---------- SHA-512 (constants derived from the primes, as the standard defines them) ----------
  const MASK64 = (1n << 64n) - 1n;
  const PRIMES = [];
  for (let n = 2; PRIMES.length < 80; n++) if (PRIMES.every(p => n % p)) PRIMES.push(n);

  function iroot(n, k) {
    const K = BigInt(k);
    let x = 1n << BigInt(Math.ceil(n.toString(2).length / k));
    for (;;) {
      const y = ((K - 1n) * x + n / x ** (K - 1n)) / K;
      if (y >= x) return x;
      x = y;
    }
  }
  const SHA_K = PRIMES.map(p => iroot(BigInt(p) << 192n, 3) & MASK64);
  const SHA_H = PRIMES.slice(0, 8).map(p => iroot(BigInt(p) << 128n, 2) & MASK64);
  const rotr = (x, n) => ((x >> n) | (x << (64n - n))) & MASK64;

  function sha512(bytes) {
    const padded = new Uint8Array(((bytes.length + 17 + 127) >> 7) << 7);
    padded.set(bytes);
    padded[bytes.length] = 0x80;
    new DataView(padded.buffer).setUint32(padded.length - 4, bytes.length * 8);
    const h = SHA_H.slice();
    for (let off = 0; off < padded.length; off += 128) {
      const w = [];
      for (let t = 0; t < 16; t++) {
        let v = 0n;
        for (let b = 0; b < 8; b++) v = (v << 8n) | BigInt(padded[off + t * 8 + b]);
        w.push(v);
      }
      for (let t = 16; t < 80; t++) {
        const s0 = rotr(w[t - 15], 1n) ^ rotr(w[t - 15], 8n) ^ (w[t - 15] >> 7n);
        const s1 = rotr(w[t - 2], 19n) ^ rotr(w[t - 2], 61n) ^ (w[t - 2] >> 6n);
        w.push((w[t - 16] + s0 + w[t - 7] + s1) & MASK64);
      }
      let [a, b, c, d, e, f, g, hh] = h;
      for (let t = 0; t < 80; t++) {
        const S1 = rotr(e, 14n) ^ rotr(e, 18n) ^ rotr(e, 41n);
        const ch = (e & f) ^ (~e & MASK64 & g);
        const t1 = (hh + S1 + ch + SHA_K[t] + w[t]) & MASK64;
        const S0 = rotr(a, 28n) ^ rotr(a, 34n) ^ rotr(a, 39n);
        const maj = (a & b) ^ (a & c) ^ (b & c);
        [hh, g, f, e, d, c, b, a] = [g, f, e, (d + t1) & MASK64, c, b, a, (t1 + S0 + maj) & MASK64];
      }
      [a, b, c, d, e, f, g, hh].forEach((v, i) => { h[i] = (h[i] + v) & MASK64; });
    }
    const out = new Uint8Array(64);
    h.forEach((v, i) => { for (let b = 0; b < 8; b++) out[i * 8 + b] = Number((v >> BigInt(56 - 8 * b)) & 255n); });
    return out;
  }

  // ---------- Python's random.Random(str) ----------
  class PyRandom {
    constructor(text) {
      const raw = new TextEncoder().encode(text);
      const all = new Uint8Array(raw.length + 64);
      all.set(raw);
      all.set(sha512(raw), raw.length);
      // Python reads these bytes as one big-endian integer, then splits it into 32-bit words, low word first
      const key = [];
      for (let end = all.length; end > 0; end -= 4) {
        let word = 0;
        for (let i = Math.max(0, end - 4); i < end; i++) word = ((word * 256) + all[i]) >>> 0;
        key.push(word);
      }
      while (key.length > 1 && key[key.length - 1] === 0) key.pop();
      this._seed(key);
      this.gaussNext = null;
    }
    _init(s) {
      this.mt = new Uint32Array(624);
      this.mt[0] = s >>> 0;
      for (let i = 1; i < 624; i++) {
        const prev = this.mt[i - 1] ^ (this.mt[i - 1] >>> 30);
        this.mt[i] = (Math.imul(1812433253, prev) + i) >>> 0;
      }
      this.index = 624;
    }
    _seed(key) {
      this._init(19650218);
      const mt = this.mt;
      let i = 1, j = 0;
      for (let k = Math.max(624, key.length); k > 0; k--) {
        const prev = mt[i - 1] ^ (mt[i - 1] >>> 30);
        mt[i] = ((mt[i] ^ Math.imul(prev, 1664525)) + key[j] + j) >>> 0;
        i++; j++;
        if (i >= 624) { mt[0] = mt[623]; i = 1; }
        if (j >= key.length) j = 0;
      }
      for (let k = 623; k > 0; k--) {
        const prev = mt[i - 1] ^ (mt[i - 1] >>> 30);
        mt[i] = ((mt[i] ^ Math.imul(prev, 1566083941)) - i) >>> 0;
        i++;
        if (i >= 624) { mt[0] = mt[623]; i = 1; }
      }
      mt[0] = 0x80000000;
    }
    _next() {
      const mt = this.mt;
      if (this.index >= 624) {
        for (let k = 0; k < 624; k++) {
          const y = (mt[k] & 0x80000000) | (mt[(k + 1) % 624] & 0x7fffffff);
          mt[k] = mt[(k + 397) % 624] ^ (y >>> 1) ^ (y & 1 ? 0x9908b0df : 0);
        }
        this.index = 0;
      }
      let y = mt[this.index++];
      y ^= y >>> 11;
      y ^= (y << 7) & 0x9d2c5680;
      y ^= (y << 15) & 0xefc60000;
      y ^= y >>> 18;
      return y >>> 0;
    }
    random() {
      const a = this._next() >>> 5, b = this._next() >>> 6;
      return (a * 67108864 + b) / 9007199254740992;
    }
    gauss(mu, sigma) {
      let z = this.gaussNext;
      this.gaussNext = null;
      if (z === null) {
        const x2pi = this.random() * 2 * Math.PI;
        const g2rad = Math.sqrt(-2 * Math.log(1 - this.random()));
        z = Math.cos(x2pi) * g2rad;
        this.gaussNext = Math.sin(x2pi) * g2rad;
      }
      return mu + z * sigma;
    }
  }

  // ---------- Black-Scholes (bs.py) ----------
  const round = (x, d) => Number(x.toFixed(d));
  const SQRT_PI = Math.sqrt(Math.PI);

  function erf(x) {
    const abs = Math.abs(x), x2 = x * x;
    if (abs < 1.5) {
      let acc = 0, fk = 25.5;
      for (let i = 0; i < 25; i++) { acc = 2 + x2 * acc / fk; fk -= 1; }
      return acc * x * Math.exp(-x2) / SQRT_PI;
    }
    if (abs >= 30) return x > 0 ? 1 : -1;
    let a = 0, da = 0.5, p = 1, pLast = 0, q = da + x2, qLast = 1;
    for (let i = 0; i < 50; i++) {
      a += da; da += 2;
      const b = da + x2;
      [p, pLast] = [b * p - a * pLast, p];
      [q, qLast] = [b * q - a * qLast, q];
    }
    const erfc = p / q * abs * Math.exp(-x2) / SQRT_PI;
    return x > 0 ? 1 - erfc : erfc - 1;
  }
  const normCdf = x => 0.5 * (1 + erf(x / Math.SQRT2));
  const normPdf = x => Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);

  function d1d2(s, k, t, r, sigma) {
    const volT = sigma * Math.sqrt(t);
    const d1 = (Math.log(s / k) + (r + 0.5 * sigma * sigma) * t) / volT;
    return [d1, d1 - volT];
  }
  function price(kind, s, k, t, r, sigma) {
    const [d1, d2] = d1d2(s, k, t, r, sigma);
    if (kind === "CE") return s * normCdf(d1) - k * Math.exp(-r * t) * normCdf(d2);
    return k * Math.exp(-r * t) * normCdf(-d2) - s * normCdf(-d1);
  }
  function greeks(kind, s, k, t, r, sigma) {
    const [d1, d2] = d1d2(s, k, t, r, sigma);
    const pdf = normPdf(d1), rootT = Math.sqrt(t);
    const common = -(s * pdf * sigma) / (2 * rootT);
    const call = kind === "CE";
    return {
      delta: call ? normCdf(d1) : normCdf(d1) - 1,
      gamma: pdf / (s * sigma * rootT),
      vega: s * pdf * rootT / 100,
      theta: (call ? common - r * k * Math.exp(-r * t) * normCdf(d2)
                   : common + r * k * Math.exp(-r * t) * normCdf(-d2)) / 365,
    };
  }

  // ---------- chain generator (synthetic.py) ----------
  function optionChain(index, seed, config) {
    const cfg = config.indices[index];
    const rng = new PyRandom(`${index}-${seed}`);
    const { spot, step } = cfg, r = config.risk_free;
    const prevSpot = spot * (1 - 0.004);
    const t = config.days_to_expiry / 365;
    const atm = Math.round(spot / step) * step;
    const rows = [];
    for (let i = -config.strikes_each_side; i <= config.strikes_each_side; i++) {
      const k = atm + i * step, m = Math.log(k / spot);
      const row = { strike: k };
      for (const kind of ["CE", "PE"]) {
        const iv = cfg.base_iv * (1 - 1.6 * m + 18 * m * m) * (1 + rng.gauss(0, 0.01));
        const ltp = price(kind, spot, k, t, r, iv);
        const prevIv = iv * (1 + rng.gauss(0, 0.02));
        const prevLtp = price(kind, prevSpot, k, t + 1 / 365, r, prevIv);
        const centre = atm + (kind === "CE" ? 3 : -3) * step, width = 6 * step;
        const base = index === "NIFTY" ? 9.0e6 : 2.5e6;
        let oi = base * Math.exp(-((k - centre) ** 2) / (2 * width ** 2)) * (0.85 + 0.3 * rng.random());
        if (k % (step * 10) === 0) oi *= 1.6;
        const oiChange = rng.gauss(kind === "PE" ? 0.04 : 0.02, 0.05);
        const volume = oi * (0.3 + 0.4 * rng.random());
        row[kind] = {
          ltp: round(Math.max(ltp, 0.05), 2), prev_ltp: round(Math.max(prevLtp, 0.05), 2),
          iv: round(iv * 100, 2), oi: Math.trunc(oi), prev_oi: Math.trunc(oi / (1 + oiChange)),
          volume: Math.trunc(volume), anomaly: null,
        };
      }
      rows.push(row);
    }
    const at = n => rows.find(row => row.strike === atm + n * step);
    const spike = at(5).CE, kink = at(-4).PE, burst = at(-8).PE;
    spike.oi = Math.trunc(spike.oi * 4.5); spike.anomaly = "oi_spike";
    kink.iv = round(kink.iv * 1.45, 2); kink.anomaly = "iv_kink";
    burst.volume = Math.trunc(burst.oi * 6); burst.anomaly = "volume_burst";
    for (const row of rows) {
      for (const kind of ["CE", "PE"]) {
        const g = greeks(kind, spot, row.strike, t, r, row[kind].iv / 100);
        for (const key of Object.keys(g)) row[kind][key] = round(g[key], 5);
      }
    }
    return { index, spot, prev_spot: round(prevSpot, 2), atm, step, lot: cfg.lot,
             days_to_expiry: config.days_to_expiry, risk_free: r, rows, synthetic: true };
  }

  // ---------- detector (anomaly.py) ----------
  function median(values) {
    const s = [...values].sort((a, b) => a - b), n = s.length;
    return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2;
  }
  function robustZ(values) {
    const med = median(values);
    const mad = median(values.map(v => Math.abs(v - med))) || 1e-9;
    return values.map(v => 0.6745 * (v - med) / mad);
  }
  function quadFit(xs, ys) {
    const sum = f => xs.reduce((acc, x, i) => acc + f(x, ys[i]), 0);
    const s = [0, 1, 2, 3, 4].map(p => sum(x => x ** p));
    const m = [[s[0], s[1], s[2], sum((x, y) => y)],
               [s[1], s[2], s[3], sum((x, y) => y * x)],
               [s[2], s[3], s[4], sum((x, y) => y * x * x)]];
    for (let c = 0; c < 3; c++) {
      let p = c;
      for (let r = c + 1; r < 3; r++) if (Math.abs(m[r][c]) > Math.abs(m[p][c])) p = r;
      [m[c], m[p]] = [m[p], m[c]];
      for (let r = 0; r < 3; r++) {
        if (r !== c) { const f = m[r][c] / m[c][c]; m[r] = m[r].map((x, i) => x - f * m[c][i]); }
      }
    }
    return [0, 1, 2].map(i => m[i][3] / m[i][i]);
  }
  function neighbourResiduals(series, window = 3) {
    return series.map((v, i) => {
      const nb = [];
      for (let j = Math.max(0, i - window); j < Math.min(series.length, i + window + 1); j++) if (j !== i) nb.push(series[j]);
      return v - median(nb);
    });
  }
  // Every strike's z-score for one leg, by detector
  function scores(chain, kind) {
    const rows = chain.rows;
    const xs = rows.map(r => Math.log(r.strike / chain.spot));
    const ys = rows.map(r => r[kind].iv);
    const c = quadFit(xs, ys);
    return {
      oi_spike: robustZ(neighbourResiduals(rows.map(r => Math.log(Math.max(r[kind].oi, 1))))),
      iv_kink: robustZ(ys.map((y, i) => y - (c[0] + c[1] * xs[i] + c[2] * xs[i] * xs[i]))),
      volume_burst: robustZ(rows.map(r => Math.log(Math.max(r[kind].volume, 1) / Math.max(r[kind].oi, 1)))),
    };
  }
  const WHY = {
    oi_spike: "Open interest far above neighbouring strikes.",
    iv_kink: "Implied volatility breaks away from the fitted smile.",
    volume_burst: "Traded volume unusually high relative to open interest.",
  };
  const isFlagged = (type, z, t) => (type === "oi_spike" ? z > t.oi : type === "iv_kink" ? Math.abs(z) > t.iv : z > t.volume);

  function detect(chain, thresholds) {
    const findings = [];
    for (const kind of ["CE", "PE"]) {
      const z = scores(chain, kind);
      for (const type of ["oi_spike", "iv_kink", "volume_burst"]) {
        z[type].forEach((zi, i) => {
          if (isFlagged(type, zi, thresholds)) {
            findings.push({ strike: chain.rows[i].strike, kind, type, z: round(zi, 2), why: WHY[type] });
          }
        });
      }
    }
    return findings.map((f, i) => [f, i]).sort((a, b) => Math.abs(b[0].z) - Math.abs(a[0].z) || a[1] - b[1]).map(p => p[0]);
  }
  function planted(chain) {
    const out = [];
    for (const r of chain.rows) for (const kind of ["CE", "PE"]) {
      if (r[kind].anomaly) out.push({ strike: r.strike, kind, type: r[kind].anomaly });
    }
    return out;
  }
  return { sha512, PyRandom, optionChain, scores, detect, planted, isFlagged };
})();
if (typeof module === "object") module.exports = Engine;
