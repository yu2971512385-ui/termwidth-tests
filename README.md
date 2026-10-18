# termwidth-tests

Shared test vectors for *how many terminal columns does this string occupy*.

Every terminal program that draws a table, wraps a paragraph or truncates a
column has to answer that question, and the libraries that answer it do not
agree with each other. The disagreements are not exotic: a family emoji, a
flag, a heart followed by a variation selector. When two parts of one program
answer differently — one deciding a column is too wide, another cutting it —
the output comes out ragged.

This repository is the question written down: 23 strings with the number of
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

Seven more cases live in a separate `contested` list, because terminals and
libraries genuinely differ on them: the two East_Asian_Width=Ambiguous
characters, the keycap sequence, the soft hyphen, a C0 control, U+007F, and a
lone regional indicator. They are measured and printed, never scored. A project
that wants to pin its own answer can score them itself.

The control characters earned their place. `unicode-width` charges them one
column from `UnicodeWidthStr::width` and none from `UnicodeWidthChar::width`,
which looks like an inconsistency until you find that its maintainers have
settled the question deliberately and more than once
([#45](https://github.com/unicode-rs/unicode-width/issues/45),
[#87](https://github.com/unicode-rs/unicode-width/issues/87)); `uniseg` and
`wcwidth` charge nothing. There is no reading of the standard that decides it,
so scoring it would only have encoded a preference.

## What the libraries do

Each runner reads `vectors.json`, measures every case with the width functions
available in that language, and prints a table. Disagreement is the output, so
the runners report and exit 0.

```
cd runners/go     && go run .
cd runners/python && pip install rich wcwidth && python run.py
cd runners/node   && npm install && node run.mjs
cd runners/rust   && cargo run
```

Failures out of the 23 scored vectors, measured on 2026-10-18:

| implementation | version | failures |
| --- | --- | ---: |
| `uniseg.StringWidth` (Go) | rivo/uniseg 0.4.7 | **0** |
| `UnicodeWidthStr::width` (Rust) | unicode-width 0.2.2 | **0** |
| `displaywidth.String` (Go) | clipperhouse/displaywidth 0.10.0 | 1 |
| `string-width` (JS) | 7.2.0 | 2 |
| `rich.cell_len` (Python) | rich 15.0.0 | 2 |
| `wcwidth.wcswidth` (Python) | wcwidth 0.9.2 | 2 |
| `Intl.Segmenter` + East_Asian_Width (JS) | Node 26 | 2 |
| `runewidth.StringWidth` (Go) | mattn/go-runewidth 0.0.16 | 4 |
| summing `UnicodeWidthChar::width` per char | — | 6 |
| `wcwidth` (JS) | 1.0.1 | 8 |
| summing `runewidth.RuneWidth` per rune | — | 8 |
| summing `displaywidth.Rune` per rune | — | 9 |

Two things worth drawing out.

**Summing per character is the common mistake.** Three rows above are not
libraries, they are how libraries get used. `runewidth.StringWidth` fails four
vectors; walking the same string rune by rune and adding `RuneWidth` fails
eight, because every rune of a ZWJ sequence is counted separately. A four-person
family emoji comes out eight columns wide instead of two. The same gap appears
in Rust, where the string API fails nothing and the per-character one fails six.

**The rule travels, not the language.** The Rust runner includes a deliberate
reimplementation of go-runewidth's rule — walk grapheme clusters, charge each
the width of its first non-zero-width character — and it fails the same four
vectors in Rust that `runewidth.StringWidth` fails in Go: the two variation
selector sequences, the rainbow flag, and the regional indicator pair. Nothing
about Go caused those failures. Taking the first character's width is what
caused them, and any language will reproduce it.

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
