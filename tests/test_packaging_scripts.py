from pathlib import Path


def test_archive_name_includes_os_arch_and_extension() -> None:
    from scripts.build_package import archive_name

    assert archive_name("windows", "x64") == "KGFS-windows-x64.zip"
    assert archive_name("macos", "arm64") == "KGFS-macos-arm64.zip"


def test_build_command_uses_spec_and_dist_paths(tmp_path: Path) -> None:
    from scripts.build_package import build_pyinstaller_command

    command = build_pyinstaller_command(
        spec_path=tmp_path / "kgfs.spec",
        dist_dir=tmp_path / "dist-packages",
        work_dir=tmp_path / "build",
        clean=True,
    )

    assert command[:3] == ["pyinstaller", "--noconfirm", "--distpath"]
    assert str(tmp_path / "dist-packages") in command
    assert "--clean" in command
    assert str(tmp_path / "kgfs.spec") == command[-1]


def test_quickstart_uses_packaged_executable_name(tmp_path: Path) -> None:
    from scripts.build_package import write_quickstart

    quickstart = write_quickstart(tmp_path, executable_name="kgfs.exe")

    text = quickstart.read_text(encoding="utf-8")
    assert "kgfs.exe doctor" in text
    assert "config/data/cache" in text


def test_smoke_script_finds_executable_in_onedir(tmp_path: Path) -> None:
    from scripts.smoke_test_packaged import find_executable

    package = tmp_path / "KGFS"
    package.mkdir()
    executable = package / ("kgfs.exe")
    executable.write_text("", encoding="utf-8")

    assert find_executable(package) == executable
