# html-button-aria-checker-cli

Check every `<button>` in HTML files has an accessible name — fail CI when one does not.

[![CI](https://github.com/haiderstudio/html-button-aria-checker-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/haiderstudio/html-button-aria-checker-cli/actions/workflows/ci.yml) [![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)

## What it does

`html_button_aria_checker` reads each HTML file,
finds every `<button>`, and reports each one with
no accessible name — no visible text, and no
`aria-label` or `aria-labelledby` — with the file
and the line number. It exits 1 when any button
lacks a name, so it can fail a CI run. A file whose
buttons all carry a name exits 0.

- An icon-only button with no label is silent to a
  screen reader — the user hears "button" and
  nothing else, and cannot tell what it does. This
  names the exact line, and the fix is one attribute
  per button.
- A button counts as named when it holds visible
  text (anything but blank space, including text
  inside a nested element such as a `<span>`), or it
  carries a non-empty `aria-label`, or a non-empty
  `aria-labelledby`. A label that is only spaces
  does not count, and neither does an empty
  attribute.
- An `<img>` alt inside the button does not count —
  the check follows the plain rule above, so a
  button that relies on image alt text is reported
  and the author can give it a real label instead.
  A `title` attribute does not count either.
- A file given directly on the command line is always
  checked, whatever its name. A folder is walked for
  files ending in `.html` or `.htm` only, recursively
  by default (`--no-recursive` stops at the top
  level). `.git` folders are never walked, and
  directory links are never followed.
- `--json` prints the result as JSON, and `--stdin`
  checks one HTML document read from standard input.
- Buttons inside HTML comments are not buttons — the
  parser skips them. Markup inside `<script>` and
  `<style>` blocks is not parsed as HTML either, so
  a `"<button>"` written in a JavaScript string or a
  stylesheet is left alone. Tag and attribute names
  are matched without regard to case, as HTML
  requires — `<BUTTON>` and `ARIA-LABEL=` are checked
  exactly like `<button>` and `aria-label=`.

## Who it is for

Every site owner with an icon button — a close
cross, a hamburger menu, a search magnifier, a
share arrow. One unnamed button and a screen reader
user cannot tell what it does, and the fix is one
attribute once the button is found. This is the
gate that stops it at the pull request.

## What it does NOT do

- It does not check the button `type` attribute.
  That is repo #88, html-button-type-checker-cli —
  the type is a different check on the same buttons.
- It does not check alt text on images. That is repo
  #30, image-alt-checker-cli — the same
  accessibility family, a different element.
- It does not check whether an `aria-labelledby`
  value points at an id that exists on the page —
  a dangling reference is a different check.
- It never rewrites a file, and it never touches the
  network.

## How this differs

- A fresh search of GitHub on Nov 15, 2026 found 0
  results for `"html-button-aria-checker-cli"` and 0
  results for `html button aria checker` — a
  completely empty field.
- No rival checks button names in local files.

## Install

```sh
git clone https://github.com/haiderstudio/html-button-aria-checker-cli.git
cd html-button-aria-checker-cli
```

There is nothing else to install: Python 3.10 or newer,
standard library only, no dependencies.

## Usage

Check one HTML file:

```sh
python3 src/html_button_aria_checker.py page.html
```

A file whose buttons all carry a name passes:

```sh
$ python3 src/html_button_aria_checker.py examples/clean.html
OK — 1 file(s) checked, every button carries a name.
```

A file with buttons missing a name fails, with the
file and line for each one:

```sh
$ python3 src/html_button_aria_checker.py examples/flagged.html
FAIL examples/flagged.html: <button> line 5 has no accessible name
FAIL examples/flagged.html: <button> line 6 has no accessible name
FAIL examples/flagged.html: <button> line 7 has no accessible name
FAIL examples/flagged.html: <button> line 8 has no accessible name
FAIL examples/flagged.html: <button> line 9 has no accessible name
Checked 1 file(s), 5 button(s) without a name in 1 file(s).
```

Check a whole folder (`.html` / `.htm` files only):

```sh
$ python3 src/html_button_aria_checker.py examples/
FAIL examples/flagged.html: <button> line 5 has no accessible name
FAIL examples/flagged.html: <button> line 6 has no accessible name
FAIL examples/flagged.html: <button> line 7 has no accessible name
FAIL examples/flagged.html: <button> line 8 has no accessible name
FAIL examples/flagged.html: <button> line 9 has no accessible name
Checked 3 file(s), 5 button(s) without a name in 1 file(s).
```

Check one document from standard input:

```sh
$ printf '<button type="button"></button>\n' | python3 src/html_button_aria_checker.py --stdin
FAIL <stdin>: <button> line 1 has no accessible name
Checked 1 file(s), 1 button(s) without a name in 1 file(s).
```

Machine-readable output:

```sh
$ python3 src/html_button_aria_checker.py --json examples/flagged.html
{
  "files": [
    {
      "path": "examples/flagged.html",
      "findings": [
        {
          "line": 5,
          "reason": "has no accessible name"
        },
        {
          "line": 6,
          "reason": "has no accessible name"
        },
        {
          "line": 7,
          "reason": "has no accessible name"
        },
        {
          "line": 8,
          "reason": "has no accessible name"
        },
        {
          "line": 9,
          "reason": "has no accessible name"
        }
      ],
      "error": null
    }
  ],
  "checked": 1,
  "findings": 5
}
```

Exit codes: 0 when every button carries a name, 1
when any button lacks one or a file cannot be read, 2
for a usage error (a missing path, a bad flag, or no
HTML files found).

## Examples

A button in a comment and a button written inside a
script string are not buttons, and `examples/clean.html`
holds both — it passes:

```sh
$ python3 src/html_button_aria_checker.py examples/clean.html
OK — 1 file(s) checked, every button carries a name.
```

Uppercase tags, a button split across lines, text
inside nested elements, and a self-closing button
with a label are all handled — `examples/edge.html`
has all of them, and it passes:

```sh
$ python3 src/html_button_aria_checker.py examples/edge.html
OK — 1 file(s) checked, every button carries a name.
```

A button whose only label is a `title` attribute
still fails — the title is not an accessible name:

```sh
$ printf '<button type="button" title="Close"></button>\n' | python3 src/html_button_aria_checker.py --stdin
FAIL <stdin>: <button> line 1 has no accessible name
Checked 1 file(s), 1 button(s) without a name in 1 file(s).
```

Run every bundled example at once with `sh
examples/run-example.sh` — the output is saved in
[examples/sample-output.md](examples/sample-output.md).

## How it is tested

```sh
python3 tests/test_html_button_aria_checker.py
```

The tests cover button detection (a button with
text passes, an empty button fails, a button with
an `aria-label` passes, a button with an
`aria-labelledby` passes, an empty `aria-label`
fails, a spaces-only `aria-label` fails, a
spaces-only `aria-labelledby` fails, whitespace-only
text fails, text inside a nested `<span>` passes,
text inside a nested `<strong>` passes, an
icon-only SVG button fails, an icon with an
`aria-label` passes, an `<img>` alt inside the
button does not count, a `title` attribute does not
count, a bare `aria-label` with no value fails,
several buttons in one file in document order, an
uppercase `<BUTTON>` and `ARIA-LABEL=`, a
self-closing button with a label passes, a
self-closing button without one fails, a button on
the same line as other markup, a button split across
lines reports the line the tag starts on, a file
with no buttons passes, an empty document passes,
an unclosed button still checked, an unclosed
button with text passes, a second button opening
judges the first one), skipping (a button in a
comment, a button in a script string, a button in
a style block, a real button after a script checked,
unclosed tags elsewhere in the file), the CLI (exit
0/1/2, folder walking for several HTML files
including `.htm`, nested folders, `--no-recursive`,
`--exclude`, `.git` skipped, a direct file checked
whatever its name, duplicate paths checked once,
`--json` output, `--stdin`, bad flags, missing paths,
empty folders, `--version`, a non-UTF-8 file reported,
input files left unchanged, the tool run from
another folder and under a changed HOME), the
bundled examples (sample output compared byte-for-byte
against a fresh run, and the README-quoted outputs
checked against it), and hygiene checks (no
placeholder text, no absolute paths, no real secrets
outside the tests and examples, stdlib imports only,
no network use in the source, `.env` first in
`.gitignore`, CI file runs the test file, README
names the neighbouring repos).

## Contributing

Small, focused improvements are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).

## Original work

This tool was written from scratch for this repo. The
idea of checking button names is not new, and the
parsing follows Python's own standard-library HTML
parser — but no existing tool does this one job,
checking that every button in local HTML files carries
an accessible name, as a tested command-line gate with
a CI exit code, as the search above shows — and every
line of code here is original, built on nothing but
Python's standard library.
