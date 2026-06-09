#!/usr/bin/env python3
"""Batch run a PDF conversion command.

The command after `--` is treated as the base converter command. For every PDF,
this script appends:

  <pdf-path> -o <output-md-path>

and tees merged stdout/stderr to `<output-md-path>.log`.

Examples:
  pixi run -e default python scripts/batch_pdf_convert.py pdf -o md -- pixi run -e default python agent/paper_xyz_ref.py --concurrency 8
  pixi run -e default python scripts/batch_pdf_convert.py --dry_run pdf -- pixi run -e default python agent/paper_xyz_ref.py --concurrency 8
  pixi run -e default python scripts/batch_pdf_convert.py --recursive --preserve_dirs pdf -- pixi run -e default python agent/paper_xyz_ref.py --concurrency 8
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

HELP_EPILOG = "\n".join((__doc__ or "").strip().splitlines()[2:]).strip()


@dataclass(frozen=True, slots=True)
class ConversionTask:
    pdf_path: Path
    output_path: Path

    @property
    def log_path(self) -> Path:
        return Path(f"{self.output_path}.log")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    raw_args = sys.argv[1:] if argv is None else argv

    parser = argparse.ArgumentParser(
        usage="%(prog)s [options] input_path -- command ...",
        description="Run one converter command for each PDF under a path.",
        epilog=HELP_EPILOG or None,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input_path",
        help="PDF file or directory containing PDF files. Example: pdf.",
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        default="md",
        help="Directory for generated Markdown files. Default: md.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Find PDF files recursively under input directories.",
    )
    parser.add_argument(
        "--preserve_dirs",
        action="store_true",
        help=(
            "When used with a directory input, preserve relative subdirectories "
            "under --output_dir."
        ),
    )
    parser.add_argument(
        "--skip_existing",
        action="store_true",
        help="Skip PDFs whose output Markdown file already exists.",
    )
    parser.add_argument(
        "--fail_fast",
        action="store_true",
        help="Stop after the first failed converter command.",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Print planned commands without running them.",
    )

    try:
        separator_index = raw_args.index("--")
    except ValueError:
        batch_args = raw_args
        command: list[str] = []
    else:
        batch_args = raw_args[:separator_index]
        command = raw_args[separator_index + 1 :]

    args = parser.parse_args(batch_args)
    args.command = command
    if not command:
        parser.error("Provide a converter command after --.")
    return args


def normalize_command(command: list[str]) -> list[str]:
    if len(command) == 1:
        return shlex.split(command[0])
    return command


def find_pdf_files(input_path: Path, *, recursive: bool) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() != ".pdf":
            raise SystemExit(f"Input file is not a PDF: {input_path}")
        return [input_path]

    if not input_path.exists():
        raise SystemExit(f"Input path does not exist: {input_path}")

    if not input_path.is_dir():
        raise SystemExit(f"Input path is neither a file nor a directory: {input_path}")

    if recursive:
        candidates = (path for path in input_path.rglob("*") if path.is_file())
    else:
        candidates = (path for path in input_path.iterdir() if path.is_file())

    pdf_paths = [path for path in candidates if path.suffix.lower() == ".pdf"]
    return sorted(pdf_paths, key=lambda path: str(path).lower())


def output_path_for(
    pdf_path: Path,
    *,
    input_path: Path,
    output_dir: Path,
    preserve_dirs: bool,
) -> Path:
    if preserve_dirs and input_path.is_dir():
        return output_dir / pdf_path.relative_to(input_path).with_suffix(".md")
    return output_dir / f"{pdf_path.stem}.md"


def build_tasks(
    pdf_paths: list[Path],
    *,
    input_path: Path,
    output_dir: Path,
    preserve_dirs: bool,
    skip_existing: bool,
) -> list[ConversionTask]:
    tasks = [
        ConversionTask(
            pdf_path=pdf_path,
            output_path=output_path_for(
                pdf_path,
                input_path=input_path,
                output_dir=output_dir,
                preserve_dirs=preserve_dirs,
            ),
        )
        for pdf_path in pdf_paths
    ]

    outputs_seen: dict[Path, Path] = {}
    collisions: list[tuple[Path, Path, Path]] = []
    for task in tasks:
        previous_pdf = outputs_seen.get(task.output_path)
        if previous_pdf is not None:
            collisions.append((task.output_path, previous_pdf, task.pdf_path))
        else:
            outputs_seen[task.output_path] = task.pdf_path

    if collisions:
        lines = [
            "Multiple PDFs would write to the same Markdown output. "
            "Use --preserve_dirs or rename inputs."
        ]
        for output_path, first_pdf, second_pdf in collisions[:10]:
            lines.append(f"  {output_path}: {first_pdf} and {second_pdf}")
        if len(collisions) > 10:
            lines.append(f"  ... and {len(collisions) - 10} more")
        raise SystemExit("\n".join(lines))

    if skip_existing:
        tasks = [task for task in tasks if not task.output_path.exists()]

    return tasks


def command_for_task(base_command: list[str], task: ConversionTask) -> list[str]:
    return [*base_command, str(task.pdf_path), "-o", str(task.output_path)]


def print_task_header(index: int, total: int, task: ConversionTask) -> None:
    print(f"\n[{index}/{total}] PDF: {task.pdf_path}", flush=True)
    print(f"[{index}/{total}] Output: {task.output_path}", flush=True)
    print(f"[{index}/{total}] Log: {task.log_path}", flush=True)


def run_with_tee(argv: list[str], log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("wb") as log_file:
        process = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )
        if process.stdout is None:
            raise RuntimeError("Expected subprocess stdout pipe.")

        try:
            for chunk in iter(lambda: process.stdout.read(8192), b""):
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
                log_file.write(chunk)
                log_file.flush()
            return process.wait()
        except KeyboardInterrupt:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            raise


def main() -> int:
    args = parse_args()
    input_path = Path(args.input_path)
    output_dir = Path(args.output_dir)
    base_command = normalize_command(args.command)

    pdf_paths = find_pdf_files(input_path, recursive=args.recursive)
    if not pdf_paths:
        print(f"No PDF files found under {input_path}.", file=sys.stderr)
        return 1

    tasks = build_tasks(
        pdf_paths,
        input_path=input_path,
        output_dir=output_dir,
        preserve_dirs=args.preserve_dirs,
        skip_existing=args.skip_existing,
    )
    if not tasks:
        print("No PDFs to process after applying filters.", file=sys.stderr)
        return 0

    failures: list[tuple[ConversionTask, int]] = []
    total = len(tasks)

    for index, task in enumerate(tasks, start=1):
        argv = command_for_task(base_command, task)
        print_task_header(index, total, task)
        print(f"[{index}/{total}] Command: {shlex.join(argv)}", flush=True)

        if args.dry_run:
            continue

        task.output_path.parent.mkdir(parents=True, exist_ok=True)
        returncode = run_with_tee(argv, task.log_path)
        if returncode == 0:
            print(f"[{index}/{total}] Done.", flush=True)
            continue

        failures.append((task, returncode))
        print(
            f"[{index}/{total}] Failed with exit code {returncode}: {task.pdf_path}",
            file=sys.stderr,
            flush=True,
        )
        if args.fail_fast:
            break

    if args.dry_run:
        print(f"\nDry run complete. Planned {total} command(s).", flush=True)
        return 0

    if failures:
        print("\nFailures:", file=sys.stderr)
        for task, returncode in failures:
            print(
                f"  exit {returncode}: {task.pdf_path} (log: {task.log_path})",
                file=sys.stderr,
            )
        return 1

    print(f"\nAll {total} PDF(s) processed successfully.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
