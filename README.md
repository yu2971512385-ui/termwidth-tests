# termwidth-tests

Shared test vectors for *how many terminal columns does this string occupy*.

Every terminal program that draws a table, wraps a paragraph or truncates a
column has to answer that question, and the libraries that answer it do not
agree with each other. The disagreements are not exotic: a family emoji, a
flag, a heart followed by a variation selector. When two parts of one program
answer differently — one deciding a column is too wide, another cutting it —
the output comes out ragged.

This repository is the question written down: 26 strings with the number of
columns each should occupy, and the reason, in a form any language can read.

## The vectors

`vectors.json` holds each case as an explicit list of code points. A literal
string in a data file is ambiguous — `é` may be one code point or two, a flag
looks like a flag either way — and a JSON string cannot carry a NUL at all, so
the code points are authoritative and the `text` field is only there to read.

```json
{
  "id": "emoji-zwj-family",
  "codepoints": ["1F468", "200D", "1F469", "200D", "1F467", "200D", "1F466"],
  "text": "👨‍👩‍👧‍👦",
  "width": 2,
  "category": "emoji",
  "why": "A ZWJ sequence is one grapheme cluster and one glyph, however many people it joins."
}
```

The rule the widths follow:

> Measure in grapheme clusters (UAX #29). A cluster is 2 columns if it is an
> emoji presentation sequence (UTS #51), a regional indicator, or begins with
> an East_Asian_Width of Wide or Fullwidth (UAX #11); 0 if it consists only of
> zero-width characters; 1 otherwise.

Four more cases live in a separate `contested` list, because terminals
genuinely differ on them: the two East_Asian_Width=Ambiguous characters, the
keycap sequence, and the soft hyphen. They are measured and printed, never
scored. A project that wants to pin its own answer can score them itself.

## What the libraries do

Each runner reads `vectors.json`, measures every case with the width functions
available in that language, and prints a table. Disagreement is the output, so
the runners report and exit 0.

```
cd runners/go     && go run .
cd runners/python && pip install rich wcwidth && python run.py
cd runners/node   && npm install && node run.mjs
```

Failures out of the 26 scored vectors, measured on 2026-10-13:

| implementation | version | failures |
| --- | --- | ---: |
| `uniseg.StringWidth` (Go) | rivo/uniseg 0.4.7 | **0** |
| `displaywidth.String` (Go) | clipperhouse/displaywidth 0.10.0 | 1 |
| `string-width` (JS) | 7.2.0 | 3 |
| `rich.cell_len` (Python) | rich 15.0.0 | 3 |
| `wcwidth.wcswidth` (Python) | wcwidth 0.9.2 | 3 |
| `runewidth.StringWidth` (Go) | mattn/go-runewidth 0.0.16 | 5 |
| `wcwidth` (JS) | 1.0.1 | 8 |
| summing `runewidth.RuneWidth` per rune | — | 9 |
| summing `displaywidth.Rune` per rune | — | 9 |

Two things worth drawing out.

**Summing per character is the common mistake.** The last two rows are not
libraries, they are how libraries get used. `runewidth.StringWidth` fails five
vectors; walking the same string rune by rune and adding `RuneWidth` fails
nine, because every rune of a ZWJ sequence is counted separately. A four-person
family emoji comes out eight columns wide instead of two.

**The selector matters in both directions.** `string-width` gives U+2764 two
columns whether or not a variation selector follows it, so `❤` and `❤️` measure
the same; `wcwidth` gives both one.

## Where this came from

The rule above is what I had to settle on to tell real bugs from
disagreements of taste while reporting these:

- [jedib0t/go-pretty](https://github.com/jedib0t/go-pretty) — table columns
  misaligned by emoji
- [cli/go-gh#314](https://github.com/cli/go-gh/pull/314) — `Truncate` measured
  with one width function and cut with another
- [olekukonko/tablewriter#339](https://github.com/olekukonko/tablewriter/pull/339)
  (merged) — widths summed per rune while the library's own dependency offered
  a cluster-aware API

In each case the argument took longer than the patch, because there was
nothing to point at. That is what this is for.

## Adding a vector

Edit the table in `build_vectors.py`, run it, and run `validate.py`. The
generator is the source of truth; `validate.py` fails if `vectors.json` has
been edited by hand, along with the other mistakes a data file invites.

A new vector needs a reason in `why` that cites the property it rests on, not
an appeal to what a particular terminal does. If implementations split and the
standard does not settle it, it belongs in `contested`.

## Licence

MIT.
