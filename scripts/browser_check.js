#!/usr/bin/env node
// Drives the built page in local headless Chrome and fails on overflow, script errors or any network request.
// With --screenshots it also refreshes screenshots/. Talks only to the Chrome it starts, over localhost.
// Set CHROME to the browser binary if it is not in the default location.
"use strict";
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const PAGE = `file://${path.join(ROOT, "docs", "index.html")}`;
const CHROME = process.env.CHROME || ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"].find(p => fs.existsSync(p));
const TABS = ["anomaly", "chain", "iv", "oi", "signal", "backtest"];
const failures = [];
const check = (ok, what) => { console.log(`${ok ? "ok  " : "FAIL"} ${what}`); if (!ok) failures.push(what); };

async function main() {
  if (!CHROME) { console.log("SKIPPED: Chrome not found (set CHROME to its path)"); return; }
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "athena-chrome-"));
  const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    "--hide-scrollbars", "--remote-debugging-address=127.0.0.1", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "about:blank"],
    { stdio: ["ignore", "ignore", "pipe"] });
  try {
    const wsUrl = await new Promise((resolve, reject) => {
      let log = "";
      chrome.stderr.on("data", d => { log += d; const m = log.match(/ws:\/\/\S+/); if (m) resolve(m[0]); });
      chrome.on("exit", () => reject(new Error("Chrome exited early")));
    });
    await run(wsUrl);
  } finally {
    chrome.removeAllListeners("exit");
    chrome.kill();
    await new Promise(r => setTimeout(r, 300));
    fs.rmSync(profile, { recursive: true, force: true });
  }
}

async function run(wsUrl) {
  const ws = new WebSocket(wsUrl);
  await new Promise(r => { ws.onopen = r; });
  let nextId = 1, session;
  const pending = new Map(), requests = [], errors = [], waiters = [];
  ws.onmessage = e => {
    const m = JSON.parse(e.data);
    if (m.id) {
      const p = pending.get(m.id); pending.delete(m.id);
      if (m.error) p.reject(new Error(m.error.message)); else p.resolve(m.result);
      return;
    }
    if (m.method === "Network.requestWillBeSent") requests.push(m.params.request.url);
    if (m.method === "Runtime.exceptionThrown") errors.push(m.params.exceptionDetails.text);
    if (m.method === "Log.entryAdded" && m.params.entry.level === "error") errors.push(m.params.entry.text);
    if (m.method === "Page.loadEventFired") waiters.splice(0).forEach(r => r());
  };
  const send = (method, params = {}, top = false) => new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params, ...(top ? {} : { sessionId: session }) }));
  });
  const { targetId } = await send("Target.createTarget", { url: "about:blank" }, true);
  ({ sessionId: session } = await send("Target.attachToTarget", { targetId, flatten: true }, true));
  for (const domain of ["Page", "Runtime", "Network", "Log"]) await send(`${domain}.enable`);

  const js = async expression => {
    const r = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error(`${expression}: ${r.exceptionDetails.text}`);
    return r.result.value;
  };
  const viewport = (width, height, mobile) => send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: mobile ? 2 : 1, mobile });
  const load = async (hash = "") => {
    for (const url of ["about:blank", PAGE + hash]) {  // via a blank page, so a hash-only change still reloads
      const loaded = new Promise(r => waiters.push(r));
      await send("Page.navigate", { url });
      await loaded;
    }
  };
  const go = hash => js(`location.hash=${JSON.stringify(hash)};new Promise(r=>setTimeout(r,60))`);
  const status = () => js("document.getElementById('lab-status').textContent");
  const noOverflow = () => js("document.documentElement.scrollWidth<=window.innerWidth");
  const shot = async (name, selector) => {
    const box = selector ? await js(`(()=>{const b=document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect();return {x:0,y:b.top+scrollY,width:innerWidth,height:b.height}})()`) : null;
    const { data } = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: !!box, ...(box ? { clip: { ...box, scale: 1 } } : {}) });
    fs.writeFileSync(path.join(ROOT, "screenshots", `${name}.png`), Buffer.from(data, "base64"));
  };

  // Layout: nothing may push the page sideways, on a phone or a desktop
  for (const [width, height, mobile] of [[390, 844, true], [1300, 900, false]]) {
    await viewport(width, height, mobile);
    await load();
    for (const idx of ["NIFTY", "BANKNIFTY"]) {
      for (const tab of TABS) {
        await go(`idx=${idx}&tab=${tab}&seed=7`);
        check(await noOverflow(), `${width}px ${idx}/${tab}: no sideways page scroll`);
      }
    }
  }

  // Seed lab
  await viewport(1300, 900, false);
  await load("#idx=NIFTY&tab=anomaly&seed=1035");
  check(/NIFTY seed 1035/.test(await status()), "deep link selects index and seed");
  await js("document.querySelector('[data-preset=miss]').click()");
  check(/[1-9]\d* missed/.test(await status()), "'A miss' example shows a miss");
  await js("document.querySelector('[data-preset=false_flag]').click()");
  check(/[1-9]\d* false flags/.test(await status()), "'A false flag' example shows a false flag");
  await js("document.querySelector('[data-preset=clean]').click()");
  check(/3 planted, 3 flagged, 3 hits, 0 false flags, 0 missed/.test(await status()), "'All correct' example is all correct");
  await js("document.getElementById('seed').value='-4';document.getElementById('lab-form').requestSubmit()");
  check(/whole number/.test(await status()), "an invalid seed is refused with a message");
  const before = await js("location.hash");
  await js("document.getElementById('seed').value='4242';document.getElementById('lab-form').requestSubmit()");
  check(/seed 4242/.test(await status()) && (await js("location.hash")) !== before, "a typed seed regenerates the chain and updates the link");
  await js("document.querySelector('.idx button[data-idx=BANKNIFTY]').click()");
  check(/BANKNIFTY seed 4242/.test(await status()), "switching index keeps the seed");

  // No network, no errors, for everything exercised above
  const outside = requests.filter(u => !u.startsWith(PAGE.split("#")[0]) && u !== "about:blank");
  check(outside.length === 0, `no network requests (${outside.length}: ${outside.join(", ") || "none"})`);
  check(errors.length === 0, `no script or CSP errors (${errors.length}: ${errors.join(" | ") || "none"})`);

  if (process.argv.includes("--screenshots")) {
    await viewport(1300, 900, false);
    await load();
    await shot("hero");
    for (const [name, hash] of [["anomaly", "idx=NIFTY&tab=anomaly&seed=7"], ["anomaly_banknifty", "idx=BANKNIFTY&tab=anomaly&seed=7"],
      ["anomaly_miss", "idx=NIFTY&tab=anomaly&seed=1035"], ["chain", "idx=NIFTY&tab=chain"], ["iv", "idx=NIFTY&tab=iv"],
      ["oi", "idx=NIFTY&tab=oi"], ["signal", "idx=NIFTY&tab=signal"], ["backtest", "idx=NIFTY&tab=backtest"]]) {
      await go(hash);
      await shot(name, "#lab");
    }
    await go("idx=NIFTY&tab=anomaly&seed=7");
    await shot("evidence", "section.block:last-of-type");
    await viewport(390, 844, true);
    await load();
    await shot("mobile");
    await go("idx=NIFTY&tab=anomaly&seed=7");
    await shot("mobile_lab", "#lab");
    console.log("screenshots refreshed");
  }
  ws.close();
}

main().then(() => {
  console.log(failures.length ? `${failures.length} browser check(s) FAILED` : "browser checks passed");
  process.exit(failures.length ? 1 : 0);
}).catch(e => { console.error(e); process.exit(2); });
