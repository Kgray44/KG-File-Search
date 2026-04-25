from pathlib import Path

from kgfs.config import KGFSConfig
from kgfs.file_filters import should_index_file, should_skip_dir


def test_file_filter_rejects_ignored_extensions_and_large_files(tmp_path: Path) -> None:
    config = KGFSConfig(indexed_folders=[tmp_path], max_file_size_mb=1)
    exe = tmp_path / "tool.exe"
    exe.write_text("not really exe", encoding="utf-8")
    huge = tmp_path / "huge.txt"
    huge.write_bytes(b"x" * (1024 * 1024 + 1))

    assert should_index_file(exe, config) is False
    assert should_index_file(huge, config) is False


def test_file_filter_accepts_supported_small_text_file(tmp_path: Path) -> None:
    config = KGFSConfig(indexed_folders=[tmp_path])
    note = tmp_path / "notes.md"
    note.write_text("# op-amps", encoding="utf-8")

    assert should_index_file(note, config) is True


def test_should_skip_default_noisy_directories(tmp_path: Path) -> None:
    config = KGFSConfig(indexed_folders=[tmp_path])

    assert should_skip_dir(tmp_path / ".git", config) is True
    assert should_skip_dir(tmp_path / "node_modules", config) is True
    assert should_skip_dir(tmp_path / "course_notes", config) is False

