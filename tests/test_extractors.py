from pathlib import Path

from kgfs.extractors import extract_text


def test_extract_text_file(tmp_path: Path) -> None:
    file_path = tmp_path / "notes.txt"
    file_path.write_text("motor torque lab report", encoding="utf-8")

    result = extract_text(file_path)

    assert result.status == "ok"
    assert "motor torque" in result.text


def test_extract_text_file_strips_utf8_bom(tmp_path: Path) -> None:
    file_path = tmp_path / "bom-notes.txt"
    file_path.write_text("motor torque lab report", encoding="utf-8-sig")

    result = extract_text(file_path)

    assert result.status == "ok"
    assert result.text.startswith("motor torque")
    assert "\ufeff" not in result.text


def test_extract_csv_file(tmp_path: Path) -> None:
    file_path = tmp_path / "data.csv"
    file_path.write_text("name,value\nop amp,5\n", encoding="utf-8")

    result = extract_text(file_path)

    assert result.status == "ok"
    assert "op amp" in result.text


def test_extract_unsupported_file_reports_skipped(tmp_path: Path) -> None:
    file_path = tmp_path / "image.png"
    file_path.write_bytes(b"png")

    result = extract_text(file_path)

    assert result.status == "skipped"
    assert result.text == ""
