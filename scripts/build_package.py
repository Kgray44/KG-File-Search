"""Build PyInstaller release archives for KG File Search."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import zipfile
from pathlib import Path

from kgfs.quickstart import build_quickstart_text
from kgfs.version import __version__

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = PROJECT_ROOT / "packaging" / "pyinstaller" / "kgfs.spec"
EXCLUDED_RELEASE_NAMES = {
    ".env",
    ".kgfs",
    ".mypy_cache",
    ".pytest_cache",
    ".pytest-tmp",
    ".ruff_cache",
    "__pycache__",
    "cache",
    "logs",
}
EXCLUDED_RELEASE_SUFFIXES = {
    ".db",
    ".faiss",
    ".hnsw",
    ".log",
    ".npy",
    ".npz",
    ".sqlite",
    ".sqlite3",
}


def archive_name(os_tag: str, arch_tag: str) -> str:
    return f"KGFS-{os_tag}-{arch_tag}.zip"


def current_os_tag() -> str:
    system = platform.system()
    if system == "Windows":
        return "windows"
    if system == "Darwin":
        return "macos"
    return system.lower() or "unknown"


def current_arch_tag() -> str:
    machine = platform.machine().lower()
    if machine in {"amd64", "x86_64"}:
        return "x64"
    if machine in {"arm64", "aarch64"}:
        return "arm64"
    return machine.replace(" ", "-") or "unknown"


def build_pyinstaller_command(
    *,
    spec_path: Path,
    dist_dir: Path,
    work_dir: Path,
    clean: bool,
) -> list[str]:
    command = [
        "pyinstaller",
        "--noconfirm",
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(work_dir),
    ]
    if clean:
        command.append("--clean")
    command.append(str(spec_path))
    return command


def write_quickstart(output_dir: Path, *, executable_name: str, version: str = __version__) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    quickstart = output_dir / "QUICKSTART-KGFS.txt"
    quickstart.write_text(
        build_quickstart_text(executable_name=executable_name, packaged=True, version=version),
        encoding="utf-8",
    )
    return quickstart


def create_release_archive(
    *,
    build_output: Path,
    dist_dir: Path,
    os_tag: str,
    arch_tag: str,
    executable_name: str,
) -> Path:
    staging = dist_dir / "_archive_staging"
    _safe_rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    if build_output.is_dir():
        package_root = staging / build_output.name
        shutil.copytree(build_output, package_root)
        docs_dir = package_root
    else:
        docs_dir = staging
        shutil.copy2(build_output, staging / build_output.name)

    write_quickstart(docs_dir, executable_name=executable_name)
    _copy_if_exists(PROJECT_ROOT / "README.md", docs_dir / "README.md")
    _copy_if_exists(PROJECT_ROOT / "LICENSE", docs_dir / "LICENSE")
    _copy_if_exists(PROJECT_ROOT / "config.example.yaml", docs_dir / "config.example.yaml")
    sample_corpus = PROJECT_ROOT / "examples" / "sample-corpus"
    if sample_corpus.exists():
        shutil.copytree(sample_corpus, docs_dir / "examples" / "sample-corpus")

    archive_path = dist_dir / archive_name(os_tag, arch_tag)
    if archive_path.exists():
        archive_path.unlink()
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(staging.rglob("*")):
            if path.is_file() and should_include_release_file(path.relative_to(staging)):
                archive.write(path, path.relative_to(staging))
    _safe_rmtree(staging)
    return archive_path


def should_include_release_file(relative_path: Path) -> bool:
    """Return whether a staged file is safe to include in release archives."""

    parts = {part.lower() for part in relative_path.parts}
    if parts & EXCLUDED_RELEASE_NAMES:
        return False
    name = relative_path.name.lower()
    if name.endswith(".sqlite-wal") or name.endswith(".sqlite-shm") or name.endswith(".sqlite3-wal"):
        return False
    return relative_path.suffix.lower() not in EXCLUDED_RELEASE_SUFFIXES


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_sha256sums(artifacts: list[Path], output_path: Path) -> Path:
    lines = [f"{sha256_file(path)}  {path.name}" for path in sorted(artifacts)]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a KGFS PyInstaller package.")
    parser.add_argument("--clean", action="store_true", help="Remove old build/dist output before packaging.")
    parser.add_argument("--mode", choices=["onedir", "onefile"], default="onedir", help="PyInstaller output mode.")
    parser.add_argument("--name", default="KGFS", help="Packaged folder name for onedir builds.")
    parser.add_argument("--dist-dir", type=Path, default=PROJECT_ROOT / "dist-packages", help="Package output folder.")
    parser.add_argument(
        "--work-dir", type=Path, default=PROJECT_ROOT / "build" / "pyinstaller", help="PyInstaller work folder."
    )
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC, help="PyInstaller spec path.")
    args = parser.parse_args(argv)

    dist_dir = args.dist_dir.expanduser().resolve()
    work_dir = args.work_dir.expanduser().resolve()
    spec_path = args.spec.expanduser().resolve()

    if args.clean:
        _safe_rmtree(work_dir)
        _safe_rmtree(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["KGFS_PYINSTALLER_MODE"] = args.mode
    env["KGFS_PACKAGE_NAME"] = args.name
    command = build_pyinstaller_command(spec_path=spec_path, dist_dir=dist_dir, work_dir=work_dir, clean=args.clean)
    subprocess.run(command, cwd=PROJECT_ROOT, check=True, env=env)

    executable_name = "kgfs.exe" if platform.system() == "Windows" else "kgfs"
    build_output = dist_dir / (args.name if args.mode == "onedir" else executable_name)
    archive_path = create_release_archive(
        build_output=build_output,
        dist_dir=dist_dir,
        os_tag=current_os_tag(),
        arch_tag=current_arch_tag(),
        executable_name=executable_name,
    )
    checksum_path = write_sha256sums([archive_path], dist_dir / "SHA256SUMS.txt")
    print(f"Packaged artifact: {archive_path}")
    print(f"SHA256 checksums: {checksum_path}")
    return 0


def _copy_if_exists(source: Path, destination: Path) -> None:
    if source.exists():
        shutil.copy2(source, destination)


def _safe_rmtree(path: Path) -> None:
    path = path.resolve()
    root = PROJECT_ROOT.resolve()
    if path == root or root not in path.parents:
        raise ValueError(f"Refusing to remove path outside the project: {path}")
    if path.exists():
        shutil.rmtree(path)


if __name__ == "__main__":
    raise SystemExit(main())
