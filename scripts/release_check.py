"""Run KGFS v0.1 release-candidate checks."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def release_check_commands(*, include_package: bool = True) -> list[list[str]]:
    commands = [
        ["python", "-m", "pytest", "-q", "--basetemp", ".pytest-tmp"],
        ["python", "-m", "ruff", "check", "."],
        ["python", "-m", "ruff", "format", "--check", "."],
        ["python", "-m", "mypy"],
        ["python", "scripts/check_docs_consistency.py"],
        ["python", "-m", "pytest", "--cov=kgfs", "--cov-report=term-missing", "--basetemp", ".pytest-tmp"],
    ]
    if include_package:
        commands.extend(
            [
                ["python", "scripts/build_package.py", "--clean", "--mode", "onedir"],
                ["python", "scripts/smoke_test_packaged.py", "--package", "dist-packages/KGFS"],
                ["python", "scripts/generate_checksums.py", "dist-packages"],
            ]
        )
    return commands


def worktree_status(cwd: Path) -> str:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip() or "clean"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run or print KGFS release-candidate checks.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running them.")
    parser.add_argument("--skip-package", action="store_true", help="Skip package build/smoke/checksum commands.")
    args = parser.parse_args(argv)

    cwd = Path.cwd()
    print(f"Worktree status: {worktree_status(cwd)}")
    commands = release_check_commands(include_package=not args.skip_package)
    for command in commands:
        print("$ " + " ".join(command))
        if not args.dry_run:
            result = subprocess.run(command, cwd=cwd, check=False)
            if result.returncode != 0:
                return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
