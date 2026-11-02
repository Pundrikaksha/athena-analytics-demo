const DATA = JSON.parse(document.getElementById('data').textContent);
const INDICES = Object.keys(DATA.config.indices), TABS = [...document.querySelectorAll('.tab button')].map(b => b.dataset.tab);
const T = DATA.config.thresholds, MAX_SEED = 999999;
const TYPE = {oi_spike: 'OI spike', iv_kink: 'IV kink', volume_burst: 'Volume burst'};
const AXIS = {oi_spike: 'OI vs neighbouring strikes', iv_kink: 'IV vs fitted smile', volume_burst: 'Volume / OI turnover'};
const LIMIT = {oi_spike: T.oi, iv_kink: T.iv, volume_burst: T.volume};
const VERDICT = {hit: '✓ Hit', false: '✕ False flag', miss: '○ Missed'};
let idx = INDICES[0], tab = 'anomaly', seed = DATA.default_seed;
const $ = id => document.getElementById(id);

function seedRange(s) {
  if (s < 50) return 'a tuning seed';
  if (s >= 1000 && s < 1200) return 'a held-out test seed';
  return 'outside the tuning and test ranges';
}
function legChip(kind) { return `<span class="leg"><i class="sw ${kind.toLowerCase()}"></i>${kind === 'CE' ? 'Call' : 'Put'}</span>`; }

function zChart(chain, type, marks) {
  const w = 360, h = 210, l = 32, r = 8, top = 26, bottom = 28, rows = chain.rows, limit = LIMIT[type];
  const series = ['CE', 'PE'].map(kind => ({kind, z: Engine.scores(chain, kind)[type]}));
  const all = series.flatMap(s => s.z);
  const hi = Math.max(limit, ...all) * 1.08, lo = Math.min(type === 'iv_kink' ? -limit : 0, ...all) * 1.08;
  const sx = i => l + (w - l - r) * i / (rows.length - 1), sy = v => top + (h - top - bottom) * (hi - v) / (hi - lo);
  const rule = (v, cls) => `<line class="${cls}" x1="${l}" x2="${w - r}" y1="${sy(v).toFixed(1)}" y2="${sy(v).toFixed(1)}"/>`;
  let out = `<svg viewBox="0 0 ${w} ${h}" width="100%" role="img" aria-label="${AXIS[type]}: robust z-score at each strike, with the flag threshold at ${limit}. The table below lists every flagged point.">`;
  out += `<text class="ct" x="0" y="15">${TYPE[type]}: ${AXIS[type]}</text>`;
  out += rule(0, 'axis') + rule(limit, 'limit') + (type === 'iv_kink' ? rule(-limit, 'limit') : '');
  out += `<text x="${w - r}" y="${(sy(limit) - 5).toFixed(1)}" text-anchor="end">threshold ${limit}</text>`;
  out += `<text x="${l - 6}" y="${(sy(0) + 4).toFixed(1)}" text-anchor="end">0</text><text x="${l - 6}" y="${(sy(limit) + 4).toFixed(1)}" text-anchor="end">${limit}</text>`;
  out += `<text x="${l}" y="${h - 8}">${rows[0].strike}</text><text x="${w - r}" y="${h - 8}" text-anchor="end">${rows[rows.length - 1].strike}</text><text x="${(l + w - r) / 2}" y="${h - 8}" text-anchor="middle">strike</text>`;
  for (const s of series) {
    s.z.forEach((z, i) => {
      const x = sx(i).toFixed(1), y = sy(z).toFixed(1), mark = marks[`${rows[i].strike}|${s.kind}|${type}`];
      const tip = `${rows[i].strike} ${s.kind === 'CE' ? 'call' : 'put'}: z ${z.toFixed(2)}${mark ? ' · ' + VERDICT[mark] : ''}`;
      if (mark) out += `<circle class="${mark === 'miss' ? 'ring miss' : 'ring'}" cx="${x}" cy="${y}" r="7"/>`;
      out += `<circle class="dot ${s.kind.toLowerCase()}" cx="${x}" cy="${y}" r="3"/><circle class="hit" cx="${x}" cy="${y}" r="7"><title>${tip}</title></circle>`;
    });
  }
  return out + '</svg>';
}

function chainTable(chain, marks) {
  const cell = (r, kind, field, type, text) => {
    const m = marks[`${r.strike}|${kind}|${type}`];
    return `<td${m ? ' class="flag"' : ''}>${m ? '⚑ ' : ''}${text}</td>`;
  };
  const leg = (r, kind) => [cell(r, kind, 'oi', 'oi_spike', r[kind].oi.toLocaleString('en-IN')), cell(r, kind, 'iv', 'iv_kink', r[kind].iv.toFixed(2)), cell(r, kind, 'volume', 'volume_burst', r[kind].volume.toLocaleString('en-IN'))];
  const rows = chain.rows.map(r => `<tr${r.strike === chain.atm ? ' class="atm"' : ''}>${leg(r, 'CE').join('')}<td class="k">${r.strike}</td>${leg(r, 'PE').reverse().join('')}</tr>`).join('');
  return `<div class="scroll" tabindex="0" role="region" aria-label="Generated option chain"><table><caption class="sr">Generated chain for seed ${seed}. Calls left, puts right.</caption><thead><tr><th>Call OI</th><th>Call IV%</th><th>Call vol</th><th class="k">Strike</th><th>Put vol</th><th>Put IV%</th><th>Put OI</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

function renderLab() {
  const chain = Engine.optionChain(idx, seed, DATA.config), found = Engine.detect(chain, T), truth = Engine.planted(chain);
  const key = f => `${f.strike}|${f.kind}|${f.type}`, truthKeys = new Set(truth.map(key)), foundKeys = new Set(found.map(key));
  const marks = {};
  found.forEach(f => { marks[key(f)] = truthKeys.has(key(f)) ? 'hit' : 'false'; });
  const missed = truth.filter(t => !foundKeys.has(key(t)));
  missed.forEach(t => { marks[key(t)] = 'miss'; });
  const zOf = t => { const z = Engine.scores(chain, t.kind)[t.type][chain.rows.findIndex(r => r.strike === t.strike)]; return (z >= 0 ? '+' : '') + z.toFixed(2); };
  const hits = found.length - found.filter(f => marks[key(f)] === 'false').length, falses = found.length - hits;
  const cards = [['Planted', truth.length], ['Flagged', found.length], ['✓ Hits', hits], ['✕ False flags', falses], ['○ Missed', missed.length]];
  const rows = found.map(f => `<tr><td>${f.strike}</td><td class="l">${legChip(f.kind)}</td><td class="l">${TYPE[f.type]}</td><td>${f.z >= 0 ? '+' : ''}${f.z.toFixed(2)}</td><td>${f.type === 'iv_kink' ? '|z| &gt; ' : 'z &gt; '}${LIMIT[f.type]}</td><td class="l">${VERDICT[marks[key(f)]]}</td><td class="l">${f.why}</td></tr>`).concat(
    missed.map(t => `<tr><td>${t.strike}</td><td class="l">${legChip(t.kind)}</td><td class="l">${TYPE[t.type]}</td><td>${zOf(t)}</td><td>${t.type === 'iv_kink' ? '|z| &gt; ' : 'z &gt; '}${LIMIT[t.type]}</td><td class="l">${VERDICT.miss}</td><td class="l">Planted, but its z-score stayed under the threshold.</td></tr>`)).join('');
  $('lab-out').innerHTML = `<div class="grid">${cards.map(([a, b]) => `<div class="card"><span>${a}</span><b>${b}</b></div>`).join('')}</div>
<div class="panel"><h3>Why each point was or wasn't flagged</h3><p class="legend"><span class="leg"><i class="sw ce"></i>Call</span><span class="leg"><i class="sw pe"></i>Put</span><span class="leg"><i class="key-ring"></i>Flagged</span><span class="leg"><i class="key-ring miss"></i>Planted but missed</span></p>
<div class="charts">${Object.keys(TYPE).map(t => zChart(chain, t, marks)).join('')}</div></div>
<div class="panel"><h3>Findings, scored against the planted labels</h3><div class="scroll" tabindex="0" role="region" aria-label="Findings"><table><thead><tr><th>Strike</th><th class="l">Leg</th><th class="l">Type</th><th>Robust z</th><th>Threshold</th><th class="l">Verdict</th><th class="l">Explanation</th></tr></thead><tbody>${rows || '<tr><td colspan="7">Nothing flagged.</td></tr>'}</tbody></table></div></div>
<details class="panel"><summary>Show the generated chain (${chain.rows.length} strikes)</summary>${chainTable(chain, marks)}</details>`;
  $('lab-status').textContent = `${idx} seed ${seed} (${seedRange(seed)}): ${truth.length} planted, ${found.length} flagged, ${hits} hits, ${falses} false flags, ${missed.length} missed.`;
  $('seed').value = seed;
  const presets = DATA.presets[idx];
  document.querySelectorAll('[data-preset]').forEach(b => { b.dataset.seed = presets[b.dataset.preset]; b.hidden = presets[b.dataset.preset] === undefined; });
}

function show() {
  document.querySelectorAll('.view').forEach(v => { v.classList.toggle('on', v.dataset.tab === tab && (v.dataset.idx === idx || v.dataset.idx === 'all')); });
  document.querySelectorAll('.idx button').forEach(b => { const on = b.dataset.idx === idx; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on); });
  document.querySelectorAll('.tab button').forEach(b => { const on = b.dataset.tab === tab; b.classList.toggle('on', on); b.setAttribute('aria-selected', on); b.tabIndex = on ? 0 : -1; });
  if (tab === 'anomaly') renderLab();
  try { history.replaceState(null, '', `#idx=${idx}&tab=${tab}&seed=${seed}`); } catch (e) { /* some browsers refuse this on file:// pages */ }
}

function readHash() {
  const p = new URLSearchParams(location.hash.slice(1));
  if (INDICES.includes(p.get('idx'))) idx = p.get('idx');
  if (TABS.includes(p.get('tab'))) tab = p.get('tab');
  const s = Number(p.get('seed'));
  if (p.get('seed') && Number.isInteger(s) && s >= 0 && s <= MAX_SEED) seed = s;
  return p.has('idx') || p.has('tab') || p.has('seed');
}

document.querySelectorAll('.idx button').forEach(b => { b.onclick = () => { idx = b.dataset.idx; show(); }; });
const tabButtons = [...document.querySelectorAll('.tab button')];
tabButtons.forEach((b, i) => {
  b.onclick = () => { tab = b.dataset.tab; show(); };
  b.onkeydown = e => {
    const step = {ArrowRight: 1, ArrowLeft: -1}[e.key];
    if (!step) return;
    e.preventDefault();
    const next = tabButtons[(i + step + tabButtons.length) % tabButtons.length];
    tab = next.dataset.tab; show(); next.focus();
  };
});
$('lab-form').onsubmit = e => {
  e.preventDefault();
  const input = $('seed'), s = Number(input.value), ok = input.value !== '' && Number.isInteger(s) && s >= 0 && s <= MAX_SEED;
  input.setAttribute('aria-invalid', !ok);
  if (!ok) { $('lab-status').textContent = `Enter a whole number from 0 to ${MAX_SEED}.`; return; }
  seed = s; show();
};
$('seed-random').onclick = () => { seed = Math.floor(Math.random() * (MAX_SEED + 1)); show(); };
document.querySelectorAll('[data-preset]').forEach(b => { b.onclick = () => { seed = Number(b.dataset.seed); show(); }; });
window.addEventListener('hashchange', () => { readHash(); show(); });
document.querySelectorAll('a[href="#lab"]').forEach(a => { a.onclick = e => { e.preventDefault(); $('lab').scrollIntoView(); $('seed').focus({preventScroll: true}); }; });
const deepLink = readHash();
show();
if (deepLink) $('lab').scrollIntoView();
