// Reads {config, seeds, thresholds, text} on stdin and prints what the browser engine computes for them.
const Engine = require("../athena_demo/engine.js");
const input = JSON.parse(require("fs").readFileSync(0, "utf8"));
const chains = [];
for (const index of Object.keys(input.config.indices)) {
  for (const seed of input.seeds) {
    const chain = Engine.optionChain(index, seed, input.config);
    chains.push({ index, seed, chain, findings: Engine.detect(chain, input.thresholds), planted: Engine.planted(chain) });
  }
}
const rng = new Engine.PyRandom(input.text);
const stream = [];
for (let i = 0; i < 2000; i++) stream.push(i % 2 ? rng.gauss(0, 1) : rng.random());
const sha = Buffer.from(Engine.sha512(new TextEncoder().encode(input.text))).toString("hex");
console.log(JSON.stringify({ chains, stream, sha }));
