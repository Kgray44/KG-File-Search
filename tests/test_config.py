from pathlib import Path

import yaml

from kgfs.config import KGFSConfig, create_default_config_file, load_config


def test_load_config_expands_indexed_folders_and_defaults(tmp_path: Path) -> None:
    docs = tmp_path / "Documents"
    docs.mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "indexed_folders": [str(docs)],
                "max_file_size_mb": 5,
                "follow_symlinks": False,
            }
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.indexed_folders == [docs]
    assert ".git" in config.ignored_folders
    assert ".pdf" in config.include_extensions
    assert config.max_file_size_bytes == 5 * 1024 * 1024
    assert config.indexing.hash_files is True
    assert config.semantic.enabled is False


def test_load_config_expands_windows_style_tilde_paths(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "User Home"
    home.mkdir()
    monkeypatch.setattr("kgfs.path_utils.Path.home", lambda: home)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump({"indexed_folders": ["~\\Documents\\Résumé Notes"]}),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.indexed_folders == [home / "Documents" / "Résumé Notes"]


def test_create_default_config_file_does_not_overwrite(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("indexed_folders: []\n", encoding="utf-8")

    created = create_default_config_file(config_path)

    assert created is False
    assert config_path.read_text(encoding="utf-8") == "indexed_folders: []\n"


def test_default_config_serializes_valid_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"

    assert create_default_config_file(config_path) is True
    text = config_path.read_text(encoding="utf-8")
    loaded = KGFSConfig.model_validate(yaml.safe_load(text))

    assert loaded.indexed_folders == []
    assert loaded.follow_symlinks is False
    assert loaded.max_file_size_mb == 25
    assert loaded.semantic.enabled is False
    assert loaded.semantic.model_name == "sentence-transformers/all-MiniLM-L6-v2"
    assert loaded.search.default_mode == "auto"
    assert loaded.search.default_limit == 10
    assert loaded.search.highlight_matches is True
    assert loaded.search.save_latest_results is True
    assert loaded.hybrid.keyword_weight == 0.35
    assert loaded.hybrid.semantic_weight == 0.45
    assert loaded.hybrid.filename_weight == 0.15
    assert loaded.hybrid.path_weight == 0.05
    assert loaded.hybrid.exact_phrase_weight == 0.10
    assert loaded.hybrid.recency_weight == 0.05
    assert loaded.hybrid.candidate_limit_multiplier == 5
    assert loaded.vectors.backend == "sqlite_scan"
    assert loaded.vectors.shard_strategy == "none"
    assert loaded.vectors.sqlite_vec.enabled is False
    assert loaded.vectors.sqlite_vec.experimental is True
    assert loaded.vectors.hnsw.enabled is False
    assert loaded.vectors.hnsw.space == "cosine"
    assert loaded.vectors.hnsw.m == 16
    assert loaded.vectors.hnsw.ef_construction == 200
    assert loaded.vectors.hnsw.ef_search == 50
    assert loaded.vectors.faiss.enabled is False
    assert loaded.vectors.faiss.index_type == "flat"
    assert loaded.vectors.faiss.use_gpu is False
    assert loaded.deep_search.enabled is True
    assert loaded.deep_search.max_passes == 3
    assert loaded.deep_search.max_candidates == 50
    assert loaded.research.max_files == 12
    assert loaded.research.max_chunks == 20
    assert loaded.similar.default_limit == 10
    assert loaded.timeline.default_limit == 50
    assert loaded.assignment.default_limit == 20
    assert ".pdf" in loaded.assignment.include_extensions
    assert loaded.projects.default_limit == 20
    assert loaded.projects.infer_from_folders is False
    assert loaded.intelligence.duplicate_min_semantic_score == 0.92
    assert loaded.intelligence.version_min_similarity == 0.72
    assert loaded.intelligence.project_min_score == 0.55
    assert loaded.intelligence.graph_max_nodes == 40
    assert loaded.metadata.auto_backup_before_reset is True
    assert loaded.metadata.export_format == "json"
    assert loaded.ai.enabled is False
    assert loaded.ai.api_key_env == "OPENAI_API_KEY"
    assert loaded.ai.send_file_paths is False
    assert loaded.ai.send_full_file_text is False
    assert '#  - "~/Documents"' in text
    assert '#  - "~/Downloads"' in text
    assert '#  - "~/Desktop"' in text


def test_vector_config_validates_bad_optional_backend_values() -> None:
    config = KGFSConfig.model_validate(
        {
            "vectors": {
                "hnsw": {"m": -5, "ef_construction": 0, "ef_search": "bad"},
                "faiss": {"index_type": "unknown"},
            }
        }
    )

    assert config.vectors.hnsw.m == 16
    assert config.vectors.hnsw.ef_construction == 200
    assert config.vectors.hnsw.ef_search == 50
    assert config.vectors.faiss.index_type == "flat"


def test_existing_config_without_hybrid_section_uses_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("indexed_folders: []\n", encoding="utf-8")

    config = load_config(config_path)

    assert config.hybrid.keyword_weight == 0.35
    assert config.hybrid.semantic_weight == 0.45
    assert config.hybrid.candidate_limit_multiplier == 5
    assert config.deep_search.enabled is True
    assert config.research.max_files == 12
    assert config.similar.default_limit == 10
    assert config.timeline.default_limit == 50
    assert config.assignment.default_limit == 20
    assert config.projects.default_limit == 20
    assert config.intelligence.graph_max_edges == 120
    assert config.metadata.auto_backup_before_reset is True
