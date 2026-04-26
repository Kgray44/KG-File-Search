from pathlib import Path

from kgfs.config import KGFSConfig
from kgfs.file_discovery import discover_files


def test_discover_files_ignores_noisy_folders_and_unsupported_files(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "notes.md").write_text("Thevenin equivalent", encoding="utf-8")
    (tmp_path / "docs" / "song.mp3").write_bytes(b"audio")
    (tmp_path / "docs" / ".git").mkdir()
    (tmp_path / "docs" / ".git" / "config").write_text("private", encoding="utf-8")
    config = KGFSConfig(indexed_folders=[tmp_path / "docs"])

    discovered = list(discover_files(config))

    assert discovered == [tmp_path / "docs" / "notes.md"]


def test_discover_files_does_not_follow_symlinks_by_default(tmp_path: Path) -> None:
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    (target_dir / "target.md").write_text("hidden via symlink", encoding="utf-8")
    root = tmp_path / "root"
    root.mkdir()
    (root / "real.md").write_text("visible", encoding="utf-8")
    link = root / "linked"
    try:
        link.symlink_to(target_dir, target_is_directory=True)
    except OSError:
        return

    config = KGFSConfig(indexed_folders=[root], follow_symlinks=False)

    assert list(discover_files(config)) == [root / "real.md"]
