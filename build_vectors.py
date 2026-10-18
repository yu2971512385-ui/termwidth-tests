#!/usr/bin/env python3
"""Generate vectors.json from the table below.

Each vector names its code points explicitly. A literal string in a data file
is ambiguous -- "é" may be one code point or two, a flag looks like a flag
either way -- and a file holding one cannot carry a NUL at all. The generated
JSON therefore carries `codepoints`, which is authoritative, and `text`, which
is the same thing spelled out for a human reading the file.
"""

import json
import pathlib

# (id, [code points], expected width, category, why)
VECTORS = [
    ("ascii-empty", [], 0, "ascii", "Nothing to draw."),
    ("ascii-word", [0x68, 0x65, 0x6C, 0x6C, 0x6F], 5, "ascii",
     "One column per printable ASCII character."),
    ("latin1-precomposed", [0x63, 0x61, 0x66, 0xE9], 4, "latin",
     "U+00E9 is a single Narrow character."),
    ("latin1-combining", [0x63, 0x61, 0x66, 0x65, 0x301], 4, "combining",
     "U+0301 joins the preceding cluster and adds no column."),
    ("combining-stacked", [0x65, 0x301, 0x302, 0x303], 1, "combining",
     "Any number of combining marks still render over one base character."),
    ("cjk-han", [0x65E5, 0x672C, 0x8A9E], 6, "east-asian",
     "East_Asian_Width=Wide, two columns each."),
    ("cjk-hangul-syllables", [0xD55C, 0xAD6D, 0xC5B4], 6, "east-asian",
     "Precomposed Hangul syllables are Wide."),
    ("cjk-fullwidth-latin", [0xFF46, 0xFF57], 4, "east-asian",
     "East_Asian_Width=Fullwidth."),
    ("cjk-halfwidth-kana", [0xFF76, 0xFF9E], 1, "east-asian",
     "U+FF9E is Grapheme_Extend, so it joins the halfwidth katakana before it "
     "into one cluster; that cluster starts Halfwidth, so one column."),
    ("hangul-jamo-composing", [0x1100, 0x1161, 0x11A8], 2, "east-asian",
     "The leading jamo is Wide; the medial and trailing jamo compose onto it."),
    ("emoji-presentation-default", [0x1F4A1], 2, "emoji",
     "U+1F4A1 has Emoji_Presentation=Yes, so it is an emoji without a selector."),
    ("emoji-text-default-bare", [0x2764], 1, "emoji",
     "U+2764 has Emoji_Presentation=No: on its own it is the text dingbat."),
    ("emoji-text-default-vs16", [0x2764, 0xFE0F], 2, "emoji",
     "VS16 requests emoji presentation (UTS #51), drawn in two columns."),
    ("emoji-warning-vs16", [0x26A0, 0xFE0F], 2, "emoji",
     "Same rule as U+2764: the selector makes it an emoji."),
    ("emoji-vs15-text", [0x2764, 0xFE0E], 1, "emoji",
     "VS15 requests text presentation, which stays one column."),
    ("emoji-zwj-family", [0x1F468, 0x200D, 0x1F469, 0x200D, 0x1F467, 0x200D, 0x1F466], 2, "emoji",
     "A ZWJ sequence is one grapheme cluster and one glyph, however many "
     "people it joins."),
    ("emoji-zwj-rainbow-flag", [0x1F3F3, 0xFE0F, 0x200D, 0x1F308], 2, "emoji",
     "A ZWJ sequence carrying a variation selector is still one glyph."),
    ("emoji-skin-tone", [0x1F44D, 0x1F3FD], 2, "emoji",
     "A skin tone modifier joins the preceding emoji rather than adding a glyph."),
    ("emoji-regional-indicator-pair", [0x1F1EF, 0x1F1F5], 2, "emoji",
     "Two regional indicators form one flag; UTS #51 gives the pair emoji "
     "presentation."),
    ("emoji-in-sentence",
     [0x61, 0x1F468, 0x200D, 0x1F469, 0x200D, 0x1F467, 0x200D, 0x1F466, 0x62], 4, "emoji",
     "1 + 2 + 1: the cluster does not change the width of its neighbours."),
    ("zwj-between-letters", [0x61, 0x200D, 0x62], 2, "control",
     "A zero width joiner between two non-emoji letters adds no column."),
    ("zero-width-space", [0x61, 0x200B, 0x62], 2, "control",
     "U+200B is zero width."),
    ("variation-selector-on-letter", [0x61, 0xFE0F], 1, "control",
     "A selector after a character with no emoji form changes nothing."),
]

# Cases where terminals legitimately differ. Reported, never scored.
CONTESTED = [
    ("ambiguous-arrow", [0x2192], 1, 2, "ambiguous",
     "East_Asian_Width=Ambiguous: one column in a Western locale, two in a "
     "CJK one."),
    ("ambiguous-circled-digit", [0x2460], 1, 2, "ambiguous",
     "Ambiguous, same as above."),
    ("keycap-sequence", [0x31, 0xFE0F, 0x20E3], 1, 2, "ambiguous",
     "One cluster, but terminals disagree on whether the tile is one column "
     "or two."),
    ("soft-hyphen", [0x61, 0xAD, 0x62], 2, 3, "ambiguous",
     "U+00AD is a format character that most terminals do not draw, but it is "
     "East_Asian_Width=Ambiguous rather than zero width, so implementations "
     "split between giving it no column and one."),
    ("c0-control", [0x61, 0x00, 0x62], 2, 3, "ambiguous",
     "A terminal may draw nothing for a C0 control or may draw a placeholder. "
     "unicode-width charges one column from its string API and none from its "
     "character API, a split its maintainers have settled on deliberately "
     "(unicode-rs/unicode-width#45, #87); uniseg and wcwidth charge none."),
    ("del", [0x61, 0x7F, 0x62], 2, 3, "ambiguous",
     "U+007F splits the same way as the C0 controls."),
    ("emoji-regional-indicator-lone", [0x1F1EF], 1, 2, "ambiguous",
     "UTS #51 pairs regional indicators into a flag; alone, one is drawn as a "
     "letter tile by some terminals and as a narrow glyph by others, and the "
     "libraries split evenly."),
]

RULE = (
    "Measure in grapheme clusters (UAX #29). A cluster is 2 columns if it is "
    "an emoji presentation sequence (UTS #51), a regional indicator, or begins "
    "with an East_Asian_Width of Wide or Fullwidth (UAX #11); 0 if it consists "
    "only of zero-width characters; 1 otherwise."
)


def main() -> None:
    doc = {
        "version": 1,
        "unicode_version": "16.0",
        "rule": RULE,
        "vectors": [
            {
                "id": vid,
                "codepoints": [f"{c:04X}" for c in cps],
                "text": "".join(chr(c) for c in cps) if all(c >= 0x20 and c != 0x7F for c in cps) else None,
                "width": width,
                "category": category,
                "why": why,
            }
            for vid, cps, width, category, why in VECTORS
        ],
        "contested": [
            {
                "id": vid,
                "codepoints": [f"{c:04X}" for c in cps],
                "text": "".join(chr(c) for c in cps),
                "width_narrow": narrow,
                "width_east_asian": wide,
                "category": category,
                "why": why,
            }
            for vid, cps, narrow, wide, category, why in CONTESTED
        ],
    }
    path = pathlib.Path(__file__).with_name("vectors.json")
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(VECTORS)} vectors and {len(CONTESTED)} contested cases to {path.name}")


if __name__ == "__main__":
    main()
