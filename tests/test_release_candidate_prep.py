from __future__ import annotations

from pathlib import Path

import yaml


def test_generate_checksums_script_hashes_only_release_zips(tmp_path: Path) -> None:
    from scripts.generate_checksums import generate_checksums

    release_dir = tmp_path / "dist-packages"
    release_dir.mkdir()
    zip_path = release_dir / "KGFS-windows-x64.zip"
    zip_path.write_bytes(b"kgfs")
    (release_dir / "notes.txt").write_text("ignore me", encoding="utf-8")
    (release_dir / ".env").write_text("SECRET=ignore", encoding="utf-8")

    checksum_path = generate_checksums(release_dir)
    text = checksum_path.read_text(encoding="utf-8")

    assert "KGFS-windows-x64.zip" in text
    assert "notes.txt" not in text
    assert ".env" not in text
    assert "SECRET" not in text


def test_release_check_script_exposes_expected_release_commands() -> None:
    from scripts.release_check import release_check_commands

    commands = [" ".join(command) for command in release_check_commands()]

    assert "python -m pytest -q --basetemp .pytest-tmp" in commands
    assert "python -m ruff check ." in commands
    assert "python -m ruff format --check ." in commands
    assert "python -m mypy" in commands
    assert "python scripts/check_docs_consistency.py" in commands
    assert "python scripts/build_package.py --clean --mode onedir" in commands
    assert "python scripts/smoke_test_packaged.py --package dist-packages/KGFS" in commands
    assert "python scripts/generate_checksums.py dist-packages" in commands


def test_known_limitations_doc_and_optional_dependency_matrix_are_linked() -> None:
    docs_readme = Path("docs/README.md").read_text(encoding="utf-8")
    known = Path("docs/known-limitations.md")
    matrix = Path("docs/optional-dependencies.md")

    assert known.exists()
    assert matrix.exists()
    assert "[Known Limitations](known-limitations.md)" in docs_readme
    assert "[Optional Dependencies](optional-dependencies.md)" in docs_readme
    assert "Unsigned executables" in known.read_text(encoding="utf-8")
    assert "ocr-easyocr" in matrix.read_text(encoding="utf-8")


def test_issue_templates_cover_release_candidate_support_fields() -> None:
    template_dir = Path(".github/ISSUE_TEMPLATE")
    expected = {
        "bug_report.yml",
        "feature_request.yml",
        "packaging_install_issue.yml",
        "search_quality_issue.yml",
        "security_privacy_concern.yml",
        "optional_model_backend_issue.yml",
    }
    required_ids = {
        "os",
        "python_version",
        "kgfs_version",
        "install_type",
        "command",
        "doctor_output",
        "capabilities_output",
        "optional_dependencies",
    }

    assert expected <= {path.name for path in template_dir.glob("*.yml")}
    for template_name in expected:
        data = yaml.safe_load((template_dir / template_name).read_text(encoding="utf-8"))
        body_ids = {item.get("id") for item in data.get("body", [])}
        assert required_ids <= body_ids, template_name


def test_sample_corpus_has_release_candidate_examples_and_no_generated_artifacts() -> None:
    sample_dir = Path("examples/sample-corpus")
    all_files = [path for path in sample_dir.rglob("*") if path.is_file()]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in all_files)

    assert "motor torque" in combined.lower()
    assert "final" in combined.lower()
    assert any(path.read_bytes() == b"duplicate calibration note\n" for path in all_files)
    assert not any(path.suffix.lower() in {".sqlite", ".db", ".log", ".faiss", ".hnsw"} for path in all_files)
