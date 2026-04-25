from pathlib import Path

from kgfs.safety import find_risky_index_roots, is_risky_index_root, risk_warning


def test_risky_root_detection_flags_filesystem_root() -> None:
    assert is_risky_index_root(Path("/"))
    assert "root" in risk_warning(Path("/")).lower()


def test_risky_root_detection_flags_windows_drive_roots() -> None:
    assert is_risky_index_root("C:\\")
    assert is_risky_index_root("D:/")


def test_risky_root_detection_flags_user_home(tmp_path: Path) -> None:
    home = tmp_path / "User Home"
    home.mkdir()

    assert is_risky_index_root(home, home=home)
    assert not is_risky_index_root(home / "Documents", home=home)


def test_risky_root_detection_flags_obvious_system_roots() -> None:
    assert is_risky_index_root("/System")
    assert is_risky_index_root("/Applications")
    assert is_risky_index_root("C:\\Windows")
    assert is_risky_index_root("C:\\Program Files")


def test_find_risky_index_roots_returns_only_dangerous_paths(tmp_path: Path) -> None:
    safe = tmp_path / "course notes"
    risky = tmp_path

    results = find_risky_index_roots([safe, risky], home=risky)

    assert results == [risky]
