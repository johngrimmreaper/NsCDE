#!/usr/bin/env python3
"""Extract compact, root-cause-oriented diagnostics from verbose build logs.

The script deliberately prefers compiler/linker diagnostics over recursive Make
failures.  It never fails the CI job itself: the caller remains responsible for
preserving the original build outcome in a final diagnostic gate.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")

# GCC/Clang-style diagnostics, including headers.  Keep these first because a
# recursive make failure is usually only a consequence of one of these lines.
COMPILER_ERROR_RE = re.compile(
    r"(?P<file>(?:[^:\s]|:(?!\d))+?):(?P<line>\d+)(?::(?P<col>\d+))?:\s*"
    r"(?:(?:fatal\s+)?error):",
    re.IGNORECASE,
)
COMPILER_WARNING_RE = re.compile(
    r"(?P<file>(?:[^:\s]|:(?!\d))+?):(?P<line>\d+)(?::(?P<col>\d+))?:\s*warning:",
    re.IGNORECASE,
)
LINKER_PATTERNS = (
    re.compile(r"undefined reference to", re.IGNORECASE),
    re.compile(r"collect2:\s*error:", re.IGNORECASE),
    re.compile(r"(?:^|\s)(?:ld|ld\.bfd|ld\.gold):.*(?:error:|cannot find|undefined)", re.IGNORECASE),
)
MAKE_FAILURE_RE = re.compile(r"make(?:\[\d+\])?:\s*\*\*", re.IGNORECASE)
GENERIC_ERROR_RE = re.compile(r"(?:fatal\s+)?error:|cannot compile|cannot find", re.IGNORECASE)
SOURCE_SUFFIX_RE = re.compile(
    r"(?P<file>(?:[A-Za-z0-9_./+~-]+)\.(?:c|cc|cpp|cxx|h|hh|hpp|hxx))(?::\d+)?",
    re.IGNORECASE,
)


def clean(line: str) -> str:
    return ANSI_RE.sub("", line.rstrip("\n"))


def matches_linker(line: str) -> bool:
    return any(pattern.search(line) for pattern in LINKER_PATTERNS)


def classify(lines: list[str]) -> tuple[list[int], list[int], list[int], list[int]]:
    compiler_errors: list[int] = []
    linker_errors: list[int] = []
    make_failures: list[int] = []
    warnings: list[int] = []

    for index, line in enumerate(lines):
        if COMPILER_ERROR_RE.search(line):
            compiler_errors.append(index)
        elif matches_linker(line):
            linker_errors.append(index)
        elif MAKE_FAILURE_RE.search(line):
            make_failures.append(index)
        elif GENERIC_ERROR_RE.search(line):
            # Useful fallback for generated tools that don't use GCC's form.
            linker_errors.append(index)

        if COMPILER_WARNING_RE.search(line) or re.search(r"\bwarning:", line, re.IGNORECASE):
            warnings.append(index)

    return compiler_errors, linker_errors, make_failures, warnings


def extract_files(lines: list[str], indexes: list[int]) -> list[str]:
    files: set[str] = set()
    for index in indexes:
        line = lines[index]
        compiler = COMPILER_ERROR_RE.search(line) or COMPILER_WARNING_RE.search(line)
        if compiler:
            files.add(compiler.group("file"))
            continue
        for match in SOURCE_SUFFIX_RE.finditer(line):
            files.add(match.group("file"))
    return sorted(files)


def numbered(lines: list[str], indexes: list[int]) -> str:
    if not indexes:
        return "(none)\n"
    return "".join(f"{index + 1}: {lines[index]}\n" for index in indexes)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--summary-file", type=Path)
    parser.add_argument("--before", type=int, default=25)
    parser.add_argument("--after", type=int, default=40)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if not args.log.is_file():
        message = f"No log file was produced: {args.log}\n"
        (args.output_dir / "first-failure.txt").write_text(message, encoding="utf-8")
        (args.output_dir / "errors.txt").write_text("(log unavailable)\n", encoding="utf-8")
        (args.output_dir / "warnings.txt").write_text("(log unavailable)\n", encoding="utf-8")
        markdown = f"### {args.label}\n\nLog unavailable: `{args.log}`\n"
        (args.output_dir / "summary.md").write_text(markdown, encoding="utf-8")
        if args.summary_file:
            with args.summary_file.open("a", encoding="utf-8") as stream:
                stream.write(markdown + "\n")
        print(message, end="")
        return 0

    raw_lines = args.log.read_text(encoding="utf-8", errors="replace").splitlines()
    lines = [clean(line) for line in raw_lines]
    compiler_errors, linker_errors, make_failures, warnings = classify(lines)
    root_candidates = compiler_errors + linker_errors
    root_index = min(root_candidates) if root_candidates else (make_failures[0] if make_failures else None)

    all_error_indexes = sorted(set(compiler_errors + linker_errors + make_failures))
    implicated_files = extract_files(lines, compiler_errors + linker_errors + warnings)

    (args.output_dir / "errors.txt").write_text(
        numbered(lines, all_error_indexes), encoding="utf-8"
    )
    (args.output_dir / "warnings.txt").write_text(
        numbered(lines, warnings), encoding="utf-8"
    )
    (args.output_dir / "implicated-files.txt").write_text(
        ("\n".join(implicated_files) + "\n") if implicated_files else "(none)\n",
        encoding="utf-8",
    )

    if root_index is None:
        first_failure = "No compiler, linker, generic error, or Make failure was detected.\n"
        context_start = context_end = None
    else:
        context_start = max(0, root_index - args.before)
        context_end = min(len(lines), root_index + args.after + 1)
        category = (
            "compiler"
            if root_index in compiler_errors
            else "linker/generic"
            if root_index in linker_errors
            else "Make fallback"
        )
        context = "\n".join(
            f"{index + 1:8d} | {lines[index]}"
            for index in range(context_start, context_end)
        )
        first_failure = (
            f"Root diagnostic category: {category}\n"
            f"Root diagnostic line: {root_index + 1}\n"
            f"Root diagnostic: {lines[root_index]}\n\n"
            f"Context ({context_start + 1}-{context_end}):\n{context}\n"
        )

    (args.output_dir / "first-failure.txt").write_text(first_failure, encoding="utf-8")

    markdown_lines = [
        f"### {args.label}",
        "",
        f"- Compiler errors: **{len(compiler_errors)}**",
        f"- Linker/generic errors: **{len(linker_errors)}**",
        f"- Recursive Make failures: **{len(make_failures)}**",
        f"- Warnings: **{len(warnings)}**",
        f"- Implicated source/header files: **{len(implicated_files)}**",
        "",
    ]
    if implicated_files:
        markdown_lines.extend(["Implicated files:", ""])
        markdown_lines.extend(f"- `{path}`" for path in implicated_files[:40])
        if len(implicated_files) > 40:
            markdown_lines.append(f"- …and {len(implicated_files) - 40} more")
        markdown_lines.append("")

    if root_index is None:
        markdown_lines.append("No root diagnostic pattern was detected in the captured log.")
    else:
        category = (
            "compiler"
            if root_index in compiler_errors
            else "linker/generic"
            if root_index in linker_errors
            else "Make fallback"
        )
        markdown_lines.extend(
            [
                f"First root diagnostic ({category}, log line {root_index + 1}):",
                "",
                "```text",
                lines[root_index][:2000],
                "```",
                "",
                f"Full ±context is saved in `{args.output_dir.name}/first-failure.txt`.",
            ]
        )

    markdown = "\n".join(markdown_lines) + "\n"
    (args.output_dir / "summary.md").write_text(markdown, encoding="utf-8")
    if args.summary_file:
        with args.summary_file.open("a", encoding="utf-8") as stream:
            stream.write(markdown + "\n")

    print(f"=== {args.label} structured diagnostics ===")
    print(f"compiler errors: {len(compiler_errors)}")
    print(f"linker/generic errors: {len(linker_errors)}")
    print(f"make failures: {len(make_failures)}")
    print(f"warnings: {len(warnings)}")
    print(f"implicated files: {len(implicated_files)}")
    print("=== first root failure and context ===")
    print(first_failure, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
