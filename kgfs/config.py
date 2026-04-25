"""YAML config models and generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from kgfs.path_utils import expand_user_path

DEFAULT_IGNORED_FOLDERS = [
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "build",
    "dist",
    "target",
    ".idea",
    ".vscode",
    "vendor",
    "Library",
    "AppData",
    "Windows",
    "Program Files",
    "Program Files (x86)",
    "$Recycle.Bin",
    "System Volume Information",
    "Applications",
    "System",
    "Steam",
    "SteamLibrary",
    "Epic Games",
    "XboxGames",
]

DEFAULT_INCLUDE_EXTENSIONS = [
    ".txt",
    ".md",
    ".py",
    ".js",
    ".ts",
    ".html",
    ".css",
    ".json",
    ".csv",
    ".docx",
    ".pdf",
]

DEFAULT_IGNORED_EXTENSIONS = [
    ".exe",
    ".dll",
    ".dylib",
    ".so",
    ".app",
    ".bin",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".tiff",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".mp3",
    ".wav",
    ".flac",
    ".zip",
    ".7z",
    ".rar",
    ".tar",
    ".gz",
]

DEFAULT_EXCLUDE_GLOBS = ["~$*", "*.tmp"]


class IndexingSettings(BaseModel):
    store_extracted_text: bool = True
    skip_unchanged_files: bool = True
    hash_files: bool = True


class ExtractionSettings(BaseModel):
    pdf_max_pages: int = 250


class SemanticSettings(BaseModel):
    enabled: bool = False
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size_chars: int = 1200
    chunk_overlap_chars: int = 200
    local_files_only: bool = True
    batch_size: int = 16


class KGFSConfig(BaseModel):
    indexed_folders: list[Path] = Field(default_factory=list)
    ignored_folders: list[str] = Field(default_factory=lambda: DEFAULT_IGNORED_FOLDERS.copy())
    include_extensions: list[str] = Field(default_factory=lambda: DEFAULT_INCLUDE_EXTENSIONS.copy())
    ignored_extensions: list[str] = Field(default_factory=lambda: DEFAULT_IGNORED_EXTENSIONS.copy())
    exclude_globs: list[str] = Field(default_factory=lambda: DEFAULT_EXCLUDE_GLOBS.copy())
    max_file_size_mb: int = 25
    follow_symlinks: bool = False
    database_path: Path | None = None
    indexing: IndexingSettings = Field(default_factory=IndexingSettings)
    extraction: ExtractionSettings = Field(default_factory=ExtractionSettings)
    semantic: SemanticSettings = Field(default_factory=SemanticSettings)

    @field_validator("indexed_folders", mode="before")
    @classmethod
    def _expand_indexed_folders(cls, value: Any) -> list[Path]:
        if value is None:
            return []
        return [_expand_path(item) for item in value]

    @field_validator("database_path", mode="before")
    @classmethod
    def _expand_database_path(cls, value: Any) -> Path | None:
        if value in (None, ""):
            return None
        return _expand_path(value)

    @field_validator("include_extensions", "ignored_extensions", mode="before")
    @classmethod
    def _normalize_extensions(cls, value: Any) -> list[str]:
        if value is None:
            return []
        extensions = []
        for item in value:
            text = str(item).strip().lower()
            if text and not text.startswith("."):
                text = f".{text}"
            if text:
                extensions.append(text)
        return extensions

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


def _expand_path(value: Any) -> Path:
    return expand_user_path(value)


DEFAULT_CONFIG_YAML = """# KG File Search config.
# Only folders listed here are indexed. KGFS will not scan your whole drive by default.
indexed_folders:
  - "~/Documents"
  - "~/Downloads"
  - "~/Desktop"

# Folder names skipped anywhere below indexed folders.
ignored_folders:
  - ".git"
  - ".svn"
  - ".hg"
  - "node_modules"
  - ".venv"
  - "venv"
  - "env"
  - "__pycache__"
  - ".pytest_cache"
  - ".mypy_cache"
  - "build"
  - "dist"
  - "target"
  - ".idea"
  - ".vscode"
  - "vendor"
  - "Library"
  - "AppData"
  - "Windows"
  - "Program Files"
  - "Program Files (x86)"
  - "$Recycle.Bin"
  - "System Volume Information"
  - "Applications"
  - "System"
  - "Steam"
  - "SteamLibrary"
  - "Epic Games"
  - "XboxGames"

# KGFS only indexes these text-like file types in the MVP.
include_extensions:
  - ".txt"
  - ".md"
  - ".py"
  - ".js"
  - ".ts"
  - ".html"
  - ".css"
  - ".json"
  - ".csv"
  - ".docx"
  - ".pdf"

# Binary, media, archive, and app files skipped by default.
ignored_extensions:
  - ".exe"
  - ".dll"
  - ".dylib"
  - ".so"
  - ".app"
  - ".bin"
  - ".png"
  - ".jpg"
  - ".jpeg"
  - ".gif"
  - ".bmp"
  - ".tiff"
  - ".mp4"
  - ".mov"
  - ".avi"
  - ".mkv"
  - ".mp3"
  - ".wav"
  - ".flac"
  - ".zip"
  - ".7z"
  - ".rar"
  - ".tar"
  - ".gz"

# Extra filename patterns to skip.
exclude_globs:
  - "~$*"
  - "*.tmp"

# Files larger than this are skipped.
max_file_size_mb: 25

# Symlinks are not followed by default to avoid accidental broad scans.
follow_symlinks: false

# Optional database path. Leave null to use your platform app-data folder.
database_path: null

indexing:
  store_extracted_text: true
  skip_unchanged_files: true
  hash_files: true

extraction:
  pdf_max_pages: 250

semantic:
  enabled: false
  model_name: "sentence-transformers/all-MiniLM-L6-v2"
  chunk_size_chars: 1200
  chunk_overlap_chars: 200
  local_files_only: true
  batch_size: 16
"""


def create_default_config_file(config_path: Path) -> bool:
    """Create a commented default config file unless it already exists."""

    config_path = config_path.expanduser()
    if config_path.exists():
        return False
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(DEFAULT_CONFIG_YAML, encoding="utf-8")
    return True


def load_config(config_path: Path) -> KGFSConfig:
    """Load and validate a KGFS YAML config."""

    config_path = config_path.expanduser()
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return KGFSConfig.model_validate(data)
