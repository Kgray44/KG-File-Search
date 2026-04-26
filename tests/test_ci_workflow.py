from pathlib import Path

import yaml


def test_github_actions_ci_tests_all_supported_platforms_and_versions() -> None:
    workflow_path = Path(".github/workflows/ci.yml")

    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    matrix = workflow["jobs"]["tests"]["strategy"]["matrix"]
    steps = workflow["jobs"]["tests"]["steps"]
    commands = "\n".join(step.get("run", "") for step in steps)

    assert set(matrix["os"]) == {"windows-latest", "macos-latest", "ubuntu-latest"}
    assert set(matrix["python-version"]) == {"3.11", "3.12"}
    assert 'python -m pip install -e ".[dev]"' in commands
    assert "python -m pytest" in commands
    assert "python -m ruff check ." in commands
    assert "python -m ruff format --check ." in commands
    assert "python -m mypy" in commands
    assert "python scripts/check_docs_consistency.py" in commands


def test_github_actions_package_builds_windows_and_macos_artifacts() -> None:
    workflow_path = Path(".github/workflows/package.yml")

    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    matrix = workflow["jobs"]["package"]["strategy"]["matrix"]["include"]
    steps = workflow["jobs"]["package"]["steps"]
    commands = "\n".join(step.get("run", "") for step in steps)
    upload_steps = [step for step in steps if step.get("uses") == "actions/upload-artifact@v4"]

    assert {item["os"] for item in matrix} == {"windows-latest", "macos-latest"}
    assert workflow["on"]["push"]["tags"] == ["v*"]
    assert 'python -m pip install -e ".[dev,package]"' in commands
    assert "python -m pytest" in commands
    assert "python -m ruff check ." in commands
    assert "python -m ruff format --check ." in commands
    assert "python -m mypy" in commands
    assert "python scripts/check_docs_consistency.py" in commands
    assert "python scripts/build_package.py --clean --mode onedir" in commands
    assert "python scripts/smoke_test_packaged.py --package dist-packages/KGFS" in commands
    assert upload_steps
    assert "dist-packages/KGFS-${{ matrix.artifact-os }}-*.zip" in upload_steps[0]["with"]["path"]
    assert "dist-packages/SHA256SUMS.txt" in upload_steps[0]["with"]["path"]
    assert "github-release" in workflow["jobs"]
    release_job = workflow["jobs"]["github-release"]
    assert "startsWith(github.ref, 'refs/tags/v')" in release_job["if"]
    release_steps = "\n".join(str(step) for step in release_job["steps"])
    assert "SHA256SUMS.txt" in release_steps
    assert "softprops/action-gh-release" in release_steps
