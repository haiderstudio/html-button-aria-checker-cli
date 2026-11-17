#!/usr/bin/env python3
"""Check every <button> in HTML files has an accessible name.

Run: python3 src/html_button_aria_checker.py page.html
     python3 src/html_button_aria_checker.py site/
     python3 src/html_button_aria_checker.py --stdin < page.html

An icon-only button with no label is silent to a
screen reader — the user hears "button" and nothing
else, and cannot tell what it does. This tool reads
each HTML file, finds every <button>, and reports
each one with no accessible name — no visible text,
and no aria-label or aria-labelledby — with the file
and the line number. It exits 1 when any button
lacks a name, so it can fail a CI run. A file whose
buttons all carry a name exits 0.

A button counts as named when any of these is true:
it holds visible text (anything but blank space,
including text inside a nested element such as a
<span>), or it carries a non-empty aria-label, or a
non-empty aria-labelledby. A label that is only
spaces does not count, and neither does an empty
attribute. An <img> alt inside the button does not
count — the check follows the plain rule above, so
a button that relies on image alt text is reported
and the author can give it a real label instead.

A file given directly on the command line is always
checked, whatever its name. A folder is walked for
files ending in .html or .htm only, recursively by
default (--no-recursive stops at the top level).
.git folders are never walked, and directory links
are never followed.

Buttons inside HTML comments are not buttons — the
parser skips them. Markup inside <script> and
<style> blocks is not parsed as HTML either, so a
"<button>" written in a JavaScript string is left
alone. Tag and attribute names are matched without
regard to case, as HTML requires.

It never rewrites a file, never touches the network,
and reads only the files and folders you point it at.
"""

import argparse
import fnmatch
import json
import os
import sys
from html.parser import HTMLParser
from pathlib import Path

__version__ = "1.0.0"

HTML_SUFFIXES = (".html", ".htm")


class ButtonAriaParser(HTMLParser):
    """Collect every <button> with no accessible name.

    HTMLParser already treats <script> and <style>
    content as character data, so markup written
    inside those blocks never reaches handle_starttag.
    Comments never reach it either.

    One frame holds the open button: its line, its
    aria-label and aria-labelledby values, and the
    text seen inside it. A second <button> opening
    while one is open judges the first one as
    unclosed, the way a browser would. An unclosed
    button is judged when the document ends.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.findings = []
        self.current = None

    def _finish(self):
        frame = self.current
        self.current = None
        if frame is None:
            return
        named = (frame["text"].strip() != ""
                 or frame["aria_label"].strip() != ""
                 or frame["aria_labelledby"].strip() != "")
        if not named:
            self.findings.append({
                "line": frame["line"],
                "reason": "has no accessible name",
            })

    def handle_starttag(self, tag, attrs):
        if tag == "button":
            if self.current is not None:
                self._finish()
            line, _offset = self.getpos()
            values = dict(attrs)
            self.current = {
                "line": line,
                "aria_label": values.get("aria-label") or "",
                "aria_labelledby": values.get("aria-labelledby") or "",
                "text": "",
            }
    def handle_data(self, data):
        if self.current is not None:
            self.current["text"] += data

    def handle_endtag(self, tag):
        if tag == "button" and self.current is not None:
            self._finish()

    def close(self):
        super().close()
        self._finish()
        self.findings.sort(key=lambda item: item["line"])


def check_text(text):
    """Check one document's text.

    Returns a list of findings, each {"line": int,
    "reason": str}, in document order.
    """
    parser = ButtonAriaParser()
    parser.feed(text)
    parser.close()
    return parser.findings


def check_file(path):
    """Check one file. Returns (findings, error)."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [], "not valid UTF-8"
    except OSError as exc:
        return [], str(exc)
    try:
        return check_text(text), None
    except Exception as exc:  # malformed markup the parser rejects
        return [], "could not be parsed: %s" % exc


def _is_html_file(path):
    return Path(path).name.lower().endswith(HTML_SUFFIXES)


def collect_files(paths, recursive=True, exclude=None):
    """Expand CLI paths into a sorted list of HTML files.

    A file given directly is always checked, whatever its
    name. A folder is walked for files ending in .html
    or .htm only. .git folders are never walked, and
    directory links are never followed.
    """
    exclude = exclude or []
    found = []
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            found.append(str(path))
        elif path.is_dir():
            for dirpath, dirs, files in os.walk(path, followlinks=False):
                dirs[:] = [
                    d for d in dirs
                    if d != ".git"
                    and not any(fnmatch.fnmatch(d, pat) for pat in exclude)
                ]
                for name in files:
                    candidate = Path(dirpath) / name
                    if not _is_html_file(candidate):
                        continue
                    if any(
                        fnmatch.fnmatch(str(candidate), pat)
                        or fnmatch.fnmatch(name, pat)
                        for pat in exclude
                    ):
                        continue
                    found.append(str(candidate))
                if not recursive:
                    break
        else:
            raise FileNotFoundError("no such file or folder: %s" % raw)
    seen = set()
    unique = []
    for item in found:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return sorted(unique)


def format_finding(path, finding):
    """One human-readable line for one button with no name."""
    return ("FAIL %s: <button> line %d %s"
            % (path, finding["line"], finding["reason"]))


def run(paths, recursive=True, exclude=None, as_json=False):
    """Check paths, print the report, return the exit code."""
    try:
        files = collect_files(paths, recursive=recursive, exclude=exclude)
    except FileNotFoundError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    if not files:
        print("error: no HTML files found", file=sys.stderr)
        return 2
    results = []
    findings = 0
    files_with_findings = 0
    for path in files:
        bad, error = check_file(path)
        count = len(bad) + (1 if error else 0)
        if count:
            findings += count
            files_with_findings += 1
        results.append({"path": path, "findings": bad, "error": error})
    if as_json:
        print(json.dumps(
            {"files": results, "checked": len(files),
             "findings": findings},
            indent=2))
    else:
        for result in results:
            if result["error"]:
                print("FAIL %s: %s" % (result["path"], result["error"]))
            for finding in result["findings"]:
                print(format_finding(result["path"], finding))
        if findings:
            print("Checked %d file(s), %d button(s) without a name "
                  "in %d file(s)." % (len(files), findings,
                                      files_with_findings))
        else:
            print("OK — %d file(s) checked, every button carries "
                  "a name." % len(files))
    return 1 if findings else 0


def run_stdin(as_json=False):
    """Check one HTML document read from standard input."""
    text = sys.stdin.read()
    bad = check_text(text)
    findings = len(bad)
    if as_json:
        print(json.dumps(
            {"files": [{"path": "<stdin>", "findings": bad,
                        "error": None}],
             "checked": 1, "findings": findings},
            indent=2))
    else:
        for finding in bad:
            print(format_finding("<stdin>", finding))
        if findings:
            print("Checked 1 file(s), %d button(s) without a name "
                  "in 1 file(s)." % findings)
        else:
            print("OK — 1 file(s) checked, every button carries "
                  "a name.")
    return 1 if findings else 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="html_button_aria_checker",
        description="Check every <button> in HTML files has "
                    "an accessible name, fail CI when one does "
                    "not.")
    parser.add_argument("paths", nargs="*",
                        help="HTML files or folders to walk")
    parser.add_argument("--no-recursive", action="store_true",
                        help="do not walk into subfolders")
    parser.add_argument("--exclude", action="append", default=[],
                        help="skip files or folders matching this pattern "
                             "(repeatable)")
    parser.add_argument("--json", action="store_true",
                        help="print the result as JSON")
    parser.add_argument("--stdin", action="store_true",
                        help="check one HTML document from standard input")
    parser.add_argument("--version", action="version",
                        version="%(prog)s " + __version__)
    args = parser.parse_args(argv)
    if args.stdin:
        if args.paths:
            parser.error("--stdin takes no file or folder arguments")
        return run_stdin(as_json=args.json)
    if not args.paths:
        parser.error("give at least one HTML file or folder")
    return run(args.paths, recursive=not args.no_recursive,
               exclude=args.exclude, as_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
