from pathlib import Path


def test_support_folders_have_readmes_and_long_term_packages() -> None:
    assert Path("docs/README.md").exists()
    assert Path("docs/architecture.md").exists()
    assert Path("packaging/README.md").exists()
    assert Path("scripts/build_package.py").exists()
    assert Path(".github/workflows/ci.yml").exists()
    assert Path(".github/workflows/package.yml").exists()
    assert Path("kgfs/__main__.py").exists()
    assert Path("kgfs/cli/app.py").exists()
    assert Path("kgfs/core/config.py").exists()
    assert Path("kgfs/db/schema.py").exists()
    assert Path("kgfs/indexing/indexer.py").exists()
    assert Path("kgfs/search/keyword.py").exists()
    assert Path("kgfs/extractors/__init__.py").exists()
    assert Path("kgfs/web/__init__.py").exists()


def test_gitignore_blocks_generated_data_and_package_outputs() -> None:
    text = Path(".gitignore").read_text(encoding="utf-8")

    for pattern in [
        ".kgfs/",
        "data/*",
        "!data/.gitkeep",
        "*.sqlite3",
        "*.sqlite3-*",
        "*.db",
        "*.db-*",
        "cache/",
        "logs/",
        "*.log",
        "*.faiss",
        "*.npy",
        "build/",
        "dist/",
        "dist-packages/",
        "*.zip",
        "*.spec",
        "!packaging/pyinstaller/kgfs.spec",
    ]:
        assert pattern in text
