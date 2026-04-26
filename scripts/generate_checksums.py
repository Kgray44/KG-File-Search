"""Generate SHA256SUMS.txt for KGFS release zip artifacts."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_checksums(dist_dir: Path, *, output_name: str = "SHA256SUMS.txt") -> Path:
    """Write checksums for KGFS release zips under dist_dir."""

    root = dist_dir.expanduser().resolve()
    artifacts = sorted(path for path in root.glob("KGFS-*.zip") if path.is_file())
    if not artifacts:
        raise FileNotFoundError(f"No KGFS-*.zip artifacts found under {root}")
    lines = [f"{sha256_file(path)}  {path.name}" for path in artifacts]
    output_path = root / output_name
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate SHA256SUMS.txt for KGFS release zip artifacts.")
    parser.add_argument("dist_dir", type=Path, nargs="?", default=Path("dist-packages"), help="Release output folder.")
    args = parser.parse_args(argv)
    checksum_path = generate_checksums(args.dist_dir)
    print(f"SHA256 checksums: {checksum_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
