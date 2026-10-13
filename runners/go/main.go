// Command termwidth-go measures the vectors with each Go width library and
// prints which ones agree with the expected column count.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/clipperhouse/displaywidth"
	runewidth "github.com/mattn/go-runewidth"
	"github.com/rivo/uniseg"
)

type vector struct {
	ID         string   `json:"id"`
	Codepoints []string `json:"codepoints"`
	Width      int      `json:"width"`
	Category   string   `json:"category"`
	Why        string   `json:"why"`
}

type document struct {
	Vectors   []vector `json:"vectors"`
	Contested []struct {
		ID            string   `json:"id"`
		Codepoints    []string `json:"codepoints"`
		WidthNarrow   int      `json:"width_narrow"`
		WidthEastAsia int      `json:"width_east_asian"`
	} `json:"contested"`
}

func decode(codepoints []string) string {
	var b strings.Builder
	for _, hex := range codepoints {
		n, err := strconv.ParseInt(hex, 16, 32)
		if err != nil {
			panic(err)
		}
		b.WriteRune(rune(n))
	}
	return b.String()
}

// Summing per-rune widths is how several libraries are used in practice, so
// measure it as its own implementation rather than only the string APIs.
func runewidthPerRune(s string) int {
	total := 0
	for _, r := range s {
		total += runewidth.RuneWidth(r)
	}
	return total
}

func displaywidthPerRune(s string) int {
	total := 0
	var o displaywidth.Options
	for _, r := range s {
		total += o.Rune(r)
	}
	return total
}

func main() {
	path := flag.String("vectors", "../../vectors.json", "path to vectors.json")
	flag.Parse()

	raw, err := os.ReadFile(*path)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	var doc document
	if err := json.Unmarshal(raw, &doc); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}

	impls := []struct {
		name string
		fn   func(string) int
	}{
		{"uniseg.StringWidth", uniseg.StringWidth},
		{"displaywidth.String", displaywidth.String},
		{"runewidth.StringWidth", runewidth.StringWidth},
		{"runewidth per rune", runewidthPerRune},
		{"displaywidth per rune", displaywidthPerRune},
	}

	fails := make([]int, len(impls))
	fmt.Printf("%-32s %6s", "vector", "want")
	for _, impl := range impls {
		fmt.Printf(" %22s", impl.name)
	}
	fmt.Println()

	for _, v := range doc.Vectors {
		s := decode(v.Codepoints)
		fmt.Printf("%-32s %6d", v.ID, v.Width)
		for i, impl := range impls {
			got := impl.fn(s)
			mark := ""
			if got != v.Width {
				mark = " x"
				fails[i]++
			}
			fmt.Printf(" %20s", fmt.Sprintf("%d%s", got, mark))
		}
		fmt.Println()
	}

	fmt.Println()
	fmt.Printf("%-32s %6s", "failures", "")
	for i := range impls {
		fmt.Printf(" %20d", fails[i])
	}
	fmt.Printf("  of %d\n", len(doc.Vectors))

	fmt.Println("\ncontested (reported, not scored):")
	for _, c := range doc.Contested {
		s := decode(c.Codepoints)
		fmt.Printf("  %-30s narrow=%d eastasian=%d  ", c.ID, c.WidthNarrow, c.WidthEastAsia)
		for _, impl := range impls {
			fmt.Printf("%s=%d ", impl.name, impl.fn(s))
		}
		fmt.Println()
	}

	total := 0
	for _, f := range fails {
		total += f
	}
	if total == 0 {
		return
	}
}
