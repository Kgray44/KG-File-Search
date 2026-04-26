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
    assert workflow["permissions"] == {"contents": "read"}
    assert 'python -m pip install -e ".[dev]"' in commands
    assert "python -m pytest -q" in commands
    assert "python -m ruff check ." in commands
    assert "python -m ruff format --check ." in commands
    assert "python -m mypy" in commands
    assert "python scripts/check_docs_consistency.py" in commands


def test_github_actions_package_builds_windows_and_macos_artifacts() -> None:
    workflow_path = Path(".github/workflows/package.yml")

    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    matrix = workflow["jobs"]["package"]["strategy"]["matrix"]["include"]
    package_job = workflow["jobs"]["package"]
    steps = workflow["jobs"]["package"]["steps"]
    commands = "\n".join(step.get("run", "") for step in steps)
    upload_steps = [step for step in steps if step.get("uses") == "actions/upload-artifact@v4"]

    assert matrix == [
        {"os": "windows-latest", "artifact_os": "windows", "arch": "x64"},
        {"os": "macos-latest", "artifact_os": "macos", "arch": "arm64"},
    ]
    assert workflow["on"]["push"]["tags"] == ["v*"]
    assert workflow["on"]["workflow_dispatch"]["inputs"]["release_tag"] == {
        "description": "Optional existing v* tag to create a draft release for.",
        "required": False,
        "type": "string",
    }
    assert "branches" not in workflow["on"]["push"]
    assert "pull_request" not in workflow["on"]
    assert workflow["permissions"] == {"contents": "read"}
    assert package_job["name"] == "Package (${{ matrix.os }}, ${{ matrix.arch }})"
    assert 'python -m pip install -e ".[dev,package]"' in commands
    assert "python -m pytest -q" in commands
    assert "python -m ruff check ." in commands
    assert "python -m ruff format --check ." in commands
    assert "python -m mypy" in commands
    assert "python scripts/check_docs_consistency.py" in commands
    assert "python scripts/build_package.py --clean --mode onedir" in commands
    assert "python scripts/generate_checksums.py dist-packages" in commands
    assert "python scripts/smoke_test_packaged.py --package dist-packages/KGFS" in commands
    assert upload_steps
    assert upload_steps[0]["with"]["name"] == "KGFS-${{ matrix.artifact_os }}-${{ matrix.arch }}"
    assert "dist-packages/*.zip" in upload_steps[0]["with"]["path"]
    assert "dist-packages/SHA256SUMS.txt" in upload_steps[0]["with"]["path"]
    assert "github-release" in workflow["jobs"]
    release_job = workflow["jobs"]["github-release"]
    assert "startsWith(github.ref, 'refs/tags/v')" in release_job["if"]
    assert "startsWith(github.event.inputs.release_tag, 'v')" in release_job["if"]
    assert release_job["permissions"] == {"contents": "write"}
    release_steps = "\n".join(str(step) for step in release_job["steps"])
    assert "SHA256SUMS.txt" in release_steps
    assert "python scripts/generate_checksums.py release-assets" in release_steps
    assert "softprops/action-gh-release" in release_steps
    assert "tag_name" in release_steps
