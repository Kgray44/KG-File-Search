import subprocess
from pathlib import Path

from kgfs.platform_utils import normalize_path, open_file, platform_diagnostics, reveal_file, risk_warning


def test_normalize_path_preserves_original_but_normalizes_for_lookup(tmp_path: Path) -> None:
    raw = tmp_path / "Folder With Spaces" / "Résumé (final).txt"
    original, normalized = normalize_path(raw)

    assert original == raw
    assert isinstance(normalized, str)
    assert "Résumé (final).txt" in normalized


def test_open_file_uses_platform_specific_api(tmp_path: Path, mocker) -> None:
    file_path = tmp_path / "file with spaces.txt"
    file_path.write_text("hello", encoding="utf-8")
    mocker.patch("kgfs.platform_utils.platform.system", return_value="Windows")
    mocked = mocker.patch("os.startfile", create=True)

    open_file(file_path)

    mocked.assert_called_once_with(str(file_path))


def test_open_file_uses_macos_open_command(tmp_path: Path, mocker) -> None:
    file_path = tmp_path / "Résumé (final).txt"
    file_path.write_text("hello", encoding="utf-8")
    mocker.patch("kgfs.platform_utils.platform.system", return_value="Darwin")
    mocked = mocker.patch("subprocess.run")

    open_file(file_path)

    mocked.assert_called_once_with(["open", str(file_path)], check=False)


def test_reveal_file_uses_platform_specific_api(tmp_path: Path, mocker) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("hello", encoding="utf-8")
    mocker.patch("kgfs.platform_utils.platform.system", return_value="Windows")
    mocked = mocker.patch("subprocess.run")

    reveal_file(file_path)

    args = mocked.call_args.args[0]
    assert args == ["explorer", f"/select,{file_path}"]


def test_reveal_file_uses_macos_reveal_for_existing_file(tmp_path: Path, mocker) -> None:
    file_path = tmp_path / "Lab Report (final).md"
    file_path.write_text("hello", encoding="utf-8")
    mocker.patch("kgfs.platform_utils.platform.system", return_value="Darwin")
    mocked = mocker.patch("subprocess.run")

    reveal_file(file_path)

    mocked.assert_called_once_with(["open", "-R", str(file_path)], check=False)


def test_reveal_file_falls_back_to_parent_when_file_is_missing(tmp_path: Path, mocker) -> None:
    file_path = tmp_path / "missing file.txt"
    mocker.patch("kgfs.platform_utils.platform.system", return_value="Darwin")
    mocked = mocker.patch("subprocess.run")

    reveal_file(file_path)

    mocked.assert_called_once_with(["open", str(tmp_path)], check=False)


def test_platform_diagnostics_reports_open_and_reveal_strategy(mocker) -> None:
    mocker.patch("kgfs.platform_utils.platform.system", return_value="Darwin")

    diagnostics = platform_diagnostics()

    assert diagnostics["open_files"] == "open"
    assert diagnostics["reveal_files"] == "Finder open -R with folder fallback"


def test_risk_warning_identifies_roots_without_cli_platform_logic(mocker) -> None:
    mocker.patch("kgfs.platform_utils.platform.system", return_value="Windows")

    assert "root" in risk_warning(Path("C:/")).lower()
