#!/usr/bin/env python3
"""Compute deploy-related change flags from the checked-out Git commit."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute whether Lambda artifacts or Terraform should deploy."
    )
    parser.add_argument(
        "--output",
        help="Optional path to write the computed context as JSON.",
    )
    return parser.parse_args()


def git_changed_files() -> list[str]:
    parent_result = subprocess.run(
        ["git", "rev-list", "--parents", "-n", "1", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    parts = parent_result.stdout.strip().split()
    head_sha = parts[0]
    parents = parts[1:]

    if not parents:
        diff_result = subprocess.run(
            ["git", "show", "--pretty=", "--name-only", head_sha],
            check=True,
            capture_output=True,
            text=True,
        )
    else:
        diff_result = subprocess.run(
            ["git", "diff", "--name-only", f"{parents[0]}..{head_sha}"],
            check=True,
            capture_output=True,
            text=True,
        )

    return [line for line in diff_result.stdout.splitlines() if line.strip()]


def build_context() -> dict[str, object]:
    changed_files = git_changed_files()
    should_publish = any(
        path.startswith("lambda/") or path == "tools/publish_lambda.py"
        for path in changed_files
    )
    should_apply = any(
        path.endswith(".tf")
        or path.startswith("lambda/")
        or path == "tools/publish_lambda.py"
        for path in changed_files
    )

    return {
        "head_sha": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "changed_files": changed_files,
        "should_publish": should_publish,
        "should_apply": should_apply,
    }


def main() -> int:
    args = parse_args()
    context = build_context()
    rendered = json.dumps(context, indent=2)
    print(rendered)

    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
