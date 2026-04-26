"""Smoke test a packaged KGFS executable against a temporary local corpus."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def find_executable(package_path: Path) -> Path:
    candidate = package_path.expanduser().resolve()
    if candidate.is_file():
        return candidate
    names = ["kgfs.exe", "kgfs"]
    for name in names:
        direct = candidate / name
        if direct.exists():
            return direct
    for path in candidate.rglob("*"):
        if path.name in names and path.is_file():
            return path
    raise FileNotFoundError(f"Could not find packaged kgfs executable under {candidate}")


def run_command(executable: Path, args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    command = [str(executable), *args]
    env = os.environ.copy()
    env["KGFS_PROJECT_LOCAL"] = "1"
    env["COLUMNS"] = "160"
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    print(f"$ {' '.join(command)}")
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {' '.join(command)}")
    return result


def smoke_test(executable: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="kgfs-package-smoke-") as temp_name:
        workspace = Path(temp_name)
        corpus = workspace / "tiny corpus"
        corpus.mkdir()
        note = corpus / "qfv.md"
        note.write_text("Tiny test note about quantum folder vibrations.", encoding="utf-8")

        run_command(executable, ["--help"], cwd=workspace)
        run_command(executable, ["--version"], cwd=workspace)
        for args in (
            ["version"],
            ["quickstart"],
            ["profile", "--help"],
            ["capabilities", "--help"],
            ["db", "--help"],
            ["save-search", "--help"],
            ["collection", "--help"],
            ["tag", "--help"],
            ["note", "--help"],
            ["assignment", "--help"],
            ["project", "--help"],
            ["duplicates", "--help"],
            ["versions", "--help"],
            ["graph", "--help"],
            ["graph-export", "--help"],
            ["health", "--help"],
            ["metadata", "--help"],
            ["tui", "--help"],
            ["serve", "--help"],
            ["integrations", "--help"],
            ["tray", "--help"],
            ["media", "--help"],
            ["ocr", "advanced-status", "--project-local"],
        ):
            run_command(executable, args, cwd=workspace)
        run_command(executable, ["doctor", "--project-local"], cwd=workspace)
        run_command(executable, ["init", "--project-local"], cwd=workspace)
        run_command(executable, ["config", "--project-local"], cwd=workspace)
        run_command(executable, ["add-folder", str(corpus), "--project-local"], cwd=workspace)
        run_command(executable, ["index", "--project-local"], cwd=workspace)
        run_command(executable, ["capabilities", "--project-local"], cwd=workspace)
        run_command(executable, ["db", "check", "--project-local"], cwd=workspace)
        result = run_command(executable, ["search", "quantum folder vibrations", "--project-local"], cwd=workspace)
        if "qfv.md" not in result.stdout:
            raise RuntimeError("Packaged search did not return the temporary test file.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke test a packaged KGFS executable.")
    parser.add_argument(
        "--package",
        type=Path,
        default=Path("dist-packages") / "KGFS",
        help="Path to packaged executable or onedir folder.",
    )
    args = parser.parse_args(argv)
    executable = find_executable(args.package)
    smoke_test(executable)
    print("Packaged KGFS smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
