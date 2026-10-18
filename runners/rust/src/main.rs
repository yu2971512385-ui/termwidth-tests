//! Measure the vectors with each Rust width implementation and print which
//! ones agree with the expected column count.

use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::path::PathBuf;

use serde::Deserialize;
use unicode_segmentation::UnicodeSegmentation;
use unicode_width::{UnicodeWidthChar, UnicodeWidthStr};

#[derive(Deserialize)]
struct Vector {
    id: String,
    codepoints: Vec<String>,
    width: usize,
}

#[derive(Deserialize)]
struct Contested {
    id: String,
    codepoints: Vec<String>,
    width_narrow: usize,
    width_east_asian: usize,
}

#[derive(Deserialize)]
struct Document {
    vectors: Vec<Vector>,
    contested: Vec<Contested>,
}

fn decode(codepoints: &[String]) -> String {
    codepoints
        .iter()
        .filter_map(|hex| u32::from_str_radix(hex, 16).ok())
        .filter_map(char::from_u32)
        .collect()
}

/// `UnicodeWidthStr::width`, which is what most of the ecosystem calls.
fn str_width(text: &str) -> usize {
    UnicodeWidthStr::width(text)
}

/// The same crate used per character, which is how a hand-written loop over a
/// string ends up measuring it.
fn char_width(text: &str) -> usize {
    text.chars().map(|c| UnicodeWidthChar::width(c).unwrap_or(0)).sum()
}

/// Per grapheme cluster, taking the width of the cluster as a whole. Closer to
/// what a terminal draws, and what a careful caller writes.
fn grapheme_width(text: &str) -> usize {
    text.graphemes(true).map(UnicodeWidthStr::width).sum()
}

/// Per cluster, but charging the cluster the width of its first non-zero-width
/// character -- the rule go-runewidth follows.
fn grapheme_first_width(text: &str) -> usize {
    text.graphemes(true)
        .map(|cluster| {
            cluster
                .chars()
                .find_map(|c| match UnicodeWidthChar::width(c) {
                    Some(w) if w > 0 => Some(w),
                    _ => None,
                })
                .unwrap_or(0)
        })
        .sum()
}

type Implementation = (&'static str, fn(&str) -> usize);

const IMPLEMENTATIONS: &[Implementation] = &[
    ("UnicodeWidthStr::width", str_width),
    ("per grapheme cluster", grapheme_width),
    ("cluster, first width", grapheme_first_width),
    ("UnicodeWidthChar sum", char_width),
];

fn main() {
    let path = env::args()
        .nth(1)
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("../../vectors.json"));
    let raw = match fs::read_to_string(&path) {
        Ok(raw) => raw,
        Err(error) => {
            eprintln!("{}: {error}", path.display());
            std::process::exit(2);
        }
    };
    let document: Document = serde_json::from_str(&raw).expect("vectors.json is not valid JSON");

    print!("{:<32}{:>6}", "vector", "want");
    for (name, _) in IMPLEMENTATIONS {
        print!("{name:>24}");
    }
    println!();

    let mut failures: BTreeMap<&str, usize> = BTreeMap::new();
    for vector in &document.vectors {
        let text = decode(&vector.codepoints);
        print!("{:<32}{:>6}", vector.id, vector.width);
        for (name, measure) in IMPLEMENTATIONS {
            let got = measure(&text);
            if got == vector.width {
                print!("{got:>24}");
            } else {
                *failures.entry(name).or_default() += 1;
                print!("{:>24}", format!("{got} x"));
            }
        }
        println!();
    }

    println!();
    print!("{:<32}{:>6}", "failures", "");
    for (name, _) in IMPLEMENTATIONS {
        print!("{:>24}", failures.get(name).copied().unwrap_or(0));
    }
    println!("  of {}", document.vectors.len());

    println!("\ncontested (reported, not scored):");
    for case in &document.contested {
        let text = decode(&case.codepoints);
        let measured: Vec<String> = IMPLEMENTATIONS
            .iter()
            .map(|(name, measure)| format!("{name}={}", measure(&text)))
            .collect();
        println!(
            "  {:<30} narrow={} eastasian={}  {}",
            case.id,
            case.width_narrow,
            case.width_east_asian,
            measured.join(" ")
        );
    }
}
