from pathlib import Path


def test_platform_system_checks_are_isolated_to_platform_utils() -> None:
    project_root = Path(__file__).resolve().parents[1]
    offenders = []

    for path in (project_root / "kgfs").rglob("*.py"):
        if path.name == "platform_utils.py":
            continue
        text = path.read_text(encoding="utf-8")
        if "platform.system(" in text:
            offenders.append(path.relative_to(project_root).as_posix())

    assert offenders == []
