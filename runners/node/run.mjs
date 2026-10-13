#!/usr/bin/env node
// Measure the vectors with each JavaScript width implementation.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const vectorsPath =
  process.argv[2] ?? path.join(here, "..", "..", "vectors.json");
const doc = JSON.parse(fs.readFileSync(vectorsPath, "utf8"));

const textOf = (vector) =>
  vector.codepoints.map((cp) => String.fromCodePoint(parseInt(cp, 16))).join("");

const implementations = {};

try {
  const { default: stringWidth } = await import("string-width");
  implementations["string-width"] = stringWidth;
} catch {}

try {
  const { default: wcwidth } = await import("wcwidth");
  implementations["wcwidth"] = wcwidth;
} catch {}

// Intl.Segmenter is in the standard library, so a width function built on it
// is what someone would write without reaching for a dependency.
if (typeof Intl !== "undefined" && Intl.Segmenter) {
  const segmenter = new Intl.Segmenter("en", { granularity: "grapheme" });
  const wide =
    /^[ᄀ-ᅟ⺀-〾ぁ-㏿㐀-䶿一-鿿ꀀ-꓏가-힣豈-﫿︰-﹯＀-｠￠-￦]|^[\u{1F300}-\u{1FAFF}\u{20000}-\u{3FFFD}]/u;
  implementations["Intl.Segmenter + EAW"] = (s) => {
    let total = 0;
    for (const { segment } of segmenter.segment(s)) {
      const stripped = segment.replace(/[\p{Mn}\p{Me}\p{Cf}\p{Cc}]/gu, "");
      if (stripped === "") continue;
      total += wide.test(stripped) || /️/.test(segment) ? 2 : 1;
    }
    return total;
  };
}

const names = Object.keys(implementations);
if (names.length === 0) {
  console.error("no width library installed; npm install string-width wcwidth");
  process.exit(2);
}

const pad = (s, n) => String(s).padStart(n);
const failures = Object.fromEntries(names.map((n) => [n, 0]));

console.log(
  "vector".padEnd(32) + pad("want", 6) + names.map((n) => pad(n, 24)).join(""),
);
for (const vector of doc.vectors) {
  const text = textOf(vector);
  let row = vector.id.padEnd(32) + pad(vector.width, 6);
  for (const name of names) {
    const got = implementations[name](text);
    if (got !== vector.width) {
      failures[name] += 1;
      row += pad(`${got} x`, 24);
    } else {
      row += pad(got, 24);
    }
  }
  console.log(row);
}

console.log();
console.log(
  "failures".padEnd(32) +
    pad("", 6) +
    names.map((n) => pad(failures[n], 24)).join("") +
    `  of ${doc.vectors.length}`,
);

console.log("\ncontested (reported, not scored):");
for (const c of doc.contested) {
  const text = textOf(c);
  const measured = names
    .map((n) => `${n}=${implementations[n](text)}`)
    .join(" ");
  console.log(
    `  ${c.id.padEnd(30)} narrow=${c.width_narrow} eastasian=${c.width_east_asian}  ${measured}`,
  );
}
