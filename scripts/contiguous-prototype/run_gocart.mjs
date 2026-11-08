// Run go-cart-wasm 0.5.0 on the EPSG:5070-projected 50 states.
//
// Usage: node run_gocart.mjs [input.geojson] [output.geojson]
// Defaults: ./states50_5070.geojson -> ./contiguous_states_2020_gocart_5070.geojson
//
// API (per go-cart-wasm README):
//   import initGoCart from './npm/node_modules/go-cart-wasm/dist/go-cart.mjs';
//   initGoCart({ locateFile: () => '<abs path to cart.wasm>' })
//     .then(GoCart => GoCart.makeCartogram(geojson, fieldName))
// makeCartogram is synchronous once the WASM module is initialised.
// Input MUST be a projected equal-area CRS (EPSG:5070 here), NOT lon/lat.
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import initGoCart from './npm/node_modules/go-cart-wasm/dist/go-cart.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const inputPath = process.argv[2] || path.join(__dirname, 'states50_5070.geojson');
const outputPath = process.argv[3] || path.join(__dirname, 'contiguous_states_2020_gocart_5070.geojson');
const wasmPath = path.join(__dirname, 'npm', 'node_modules', 'go-cart-wasm', 'dist', 'cart.wasm');

const data = JSON.parse(readFileSync(inputPath, 'utf8'));
console.log(`input: ${data.features.length} features, field 'population'`);
console.log(`population total: ${data.features.reduce((s, f) => s + f.properties.population, 0).toLocaleString('en-US')}`);

const t0 = Date.now();
const GoCart = await initGoCart({ locateFile: () => wasmPath });
console.log(`WASM init: ${((Date.now() - t0) / 1000).toFixed(2)}s`);

const t1 = Date.now();
const result = GoCart.makeCartogram(data, 'population');
const secs = (Date.now() - t1) / 1000;
console.log(`makeCartogram: ${secs.toFixed(2)}s wall time`);

// makeCartogram may return an object or a JSON string; normalise.
const out = typeof result === 'string' ? JSON.parse(result) : result;
console.log(`output: ${out.features?.length} features, type ${out.type}`);
console.log(`output props sample: ${JSON.stringify(out.features[0].properties)}`);

writeFileSync(outputPath, JSON.stringify(out));
console.log(`wrote ${outputPath}`);
