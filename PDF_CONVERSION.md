# Converting these docs to PDF

This repository doesn't ship an automated PDF pipeline. If you'd like PDF
copies of the Markdown docs here, you can generate them yourself with
[Pandoc](https://pandoc.org/) and a LaTeX distribution.

## Requirements

- [Pandoc](https://pandoc.org/installing.html)
- A TeX distribution with `xelatex` — e.g. [TeX Live](https://tug.org/texlive/) or [MiKTeX](https://miktex.org/)

## Usage

Convert a single file:

```bash
pandoc README.md --pdf-engine=xelatex -o README.pdf
```

Convert every Markdown file in the repo, recursively, into a `docs-pdf/`
folder that mirrors the source layout (PowerShell):

```powershell
Get-ChildItem -Recurse -Filter *.md | Where-Object { $_.FullName -notmatch '\\node_modules\\|\\\.git\\' } | ForEach-Object {
    $rel = $_.FullName.Substring((Get-Location).Path.Length + 1)
    $out = Join-Path 'docs-pdf' ($rel -replace '\.md$', '.pdf')
    New-Item -ItemType Directory -Force -Path (Split-Path $out) | Out-Null
    pandoc $_.FullName --pdf-engine=xelatex -o $out
}
```

Or the equivalent in bash:

```bash
find . -name "*.md" -not -path "./node_modules/*" -not -path "./.git/*" | while read -r f; do
  out="docs-pdf/${f#./}"; out="${out%.md}.pdf"
  mkdir -p "$(dirname "$out")"
  pandoc "$f" --pdf-engine=xelatex -o "$out"
done
```

## Formatting tips

- Add `--toc` for a table of contents, `-V geometry:margin=1in` for
  margins, `-V papersize:letter` (or `a4`) for page size.
- If a table with long code spans or identifiers overflows the page, it's
  usually because `\texttt{}` (what Pandoc renders `` `inline code` `` as)
  doesn't break inside a single unbroken token. Breaking the token
  manually, or post-processing with a filter that inserts break points
  after separators like `_`, `-`, `.`, `/`, is the simplest fix.
- If Unicode characters (checkmarks, arrows, emoji) show up missing in the
  PDF, pass a font with broader glyph coverage, e.g.
  `-V mainfont="DejaVu Sans"`.
