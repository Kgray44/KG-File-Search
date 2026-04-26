"""YAML config models and generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from kgfs.core.path_utils import expand_user_path

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


class TesseractOCRSettings(BaseModel):
    command: str = "tesseract"
    language: str = "eng"


class EasyOCRSettings(BaseModel):
    enabled: bool = False
    languages: list[str] = Field(default_factory=lambda: ["en"])
    gpu: bool = False

    @field_validator("languages", mode="before")
    @classmethod
    def _languages(cls, value: Any) -> list[str]:
        if value is None:
            return ["en"]
        languages = [str(item).strip().lower() for item in value if str(item).strip()]
        return languages or ["en"]


class PaddleOCRSettings(BaseModel):
    enabled: bool = False
    language: str = "en"

    @field_validator("language", mode="before")
    @classmethod
    def _language(cls, value: Any) -> str:
        text = str(value or "en").strip().lower()
        return text or "en"


class CloudOCRFallbackSettings(BaseModel):
    enabled: bool = False
    provider: str | None = None
    require_confirmation: bool = True
    preview_before_upload: bool = True
    max_files_per_run: int = 5

    @field_validator("provider", mode="before")
    @classmethod
    def _provider(cls, value: Any) -> str | None:
        text = str(value or "").strip().lower()
        return text or None

    @field_validator("max_files_per_run", mode="before")
    @classmethod
    def _positive_limit(cls, value: Any) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return 5
        return number if number > 0 else 5


class OCRSettings(BaseModel):
    enabled: bool = False
    backend: str = "tesseract"
    include_extensions: list[str] = Field(default_factory=lambda: [".png", ".jpg", ".jpeg", ".tiff", ".bmp"])
    max_image_size_mb: float = 15
    cache_results: bool = True
    modify_source_files: bool = False
    min_pdf_text_chars: int = 20
    pdf_max_pages: int | None = None
    image_preprocessing: bool = True
    tesseract: TesseractOCRSettings = Field(default_factory=TesseractOCRSettings)
    easyocr: EasyOCRSettings = Field(default_factory=EasyOCRSettings)
    paddle: PaddleOCRSettings = Field(default_factory=PaddleOCRSettings)
    cloud_fallback: CloudOCRFallbackSettings = Field(default_factory=CloudOCRFallbackSettings)

    @field_validator("include_extensions", mode="before")
    @classmethod
    def _normalize_ocr_extensions(cls, value: Any) -> list[str]:
        if value is None:
            return []
        extensions: list[str] = []
        for item in value:
            text = str(item).strip().lower()
            if text and not text.startswith("."):
                text = f".{text}"
            if text:
                extensions.append(text)
        return extensions

    @field_validator("max_image_size_mb", mode="before")
    @classmethod
    def _positive_image_size(cls, value: Any) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 15
        return number if number > 0 else 15

    @field_validator("min_pdf_text_chars", mode="before")
    @classmethod
    def _nonnegative_pdf_threshold(cls, value: Any) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 20

    @field_validator("pdf_max_pages", mode="before")
    @classmethod
    def _optional_positive_pdf_pages(cls, value: Any) -> int | None:
        if value in (None, ""):
            return None
        try:
            number = int(value)
        except (TypeError, ValueError):
            return None
        return number if number > 0 else None

    @field_validator("modify_source_files", mode="before")
    @classmethod
    def _force_no_source_modification(cls, value: Any) -> bool:
        return False

    @property
    def max_image_size_bytes(self) -> int:
        return int(self.max_image_size_mb * 1024 * 1024)


def _normalize_extension_list(value: Any) -> list[str]:
    if value is None:
        return []
    extensions: list[str] = []
    for item in value:
        text = str(item).strip().lower()
        if text and not text.startswith("."):
            text = f".{text}"
        if text:
            extensions.append(text)
    return extensions


class PhotoSettings(BaseModel):
    enabled: bool = False
    index_exif: bool = True
    include_extensions: list[str] = Field(default_factory=lambda: [".jpg", ".jpeg", ".png", ".heic", ".tiff"])
    store_location_metadata: bool = False
    location_precision: str = "none"
    generate_captions: bool = False

    @field_validator("include_extensions", mode="before")
    @classmethod
    def _extensions(cls, value: Any) -> list[str]:
        return _normalize_extension_list(value)

    @model_validator(mode="after")
    def _location_safety(self):
        precision = str(self.location_precision or "none").strip().lower()
        if not self.store_location_metadata:
            self.location_precision = "none"
        elif precision not in {"none", "coarse", "exact"}:
            self.location_precision = "none"
        else:
            self.location_precision = precision
        return self


class CaptionSettings(BaseModel):
    enabled: bool = False
    backend: str = "none"
    model_name: str | None = None
    local_files_only: bool = True
    max_images_per_run: int = 50

    @field_validator("backend", mode="before")
    @classmethod
    def _backend(cls, value: Any) -> str:
        return str(value or "none").strip().lower() or "none"

    @field_validator("max_images_per_run", mode="before")
    @classmethod
    def _positive_limit(cls, value: Any) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return 50
        return number if number > 0 else 50


class AudioSettings(BaseModel):
    enabled: bool = False
    transcription_enabled: bool = False
    backend: str = "none"
    include_extensions: list[str] = Field(default_factory=lambda: [".m4a", ".mp3", ".wav", ".aac", ".flac"])
    model_name: str | None = None
    local_files_only: bool = True
    max_audio_minutes_per_file: int = 60

    @field_validator("backend", mode="before")
    @classmethod
    def _backend(cls, value: Any) -> str:
        return str(value or "none").strip().lower() or "none"

    @field_validator("include_extensions", mode="before")
    @classmethod
    def _extensions(cls, value: Any) -> list[str]:
        return _normalize_extension_list(value)

    @field_validator("max_audio_minutes_per_file", mode="before")
    @classmethod
    def _positive_minutes(cls, value: Any) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return 60
        return number if number > 0 else 60


class VisualSettings(BaseModel):
    enabled: bool = False
    backend: str = "none"
    model_name: str | None = None
    local_files_only: bool = True

    @field_validator("backend", mode="before")
    @classmethod
    def _backend(cls, value: Any) -> str:
        return str(value or "none").strip().lower() or "none"


class MediaSettings(BaseModel):
    enabled: bool = False
    cache_results: bool = True
    max_media_file_size_mb: float = 50
    photos: PhotoSettings = Field(default_factory=PhotoSettings)
    captions: CaptionSettings = Field(default_factory=CaptionSettings)
    audio: AudioSettings = Field(default_factory=AudioSettings)
    visual: VisualSettings = Field(default_factory=VisualSettings)

    @field_validator("max_media_file_size_mb", mode="before")
    @classmethod
    def _positive_size(cls, value: Any) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 50
        return number if number > 0 else 50

    @property
    def max_media_file_size_bytes(self) -> int:
        return int(self.max_media_file_size_mb * 1024 * 1024)


class SemanticSettings(BaseModel):
    enabled: bool = False
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size_chars: int = 1200
    chunk_overlap_chars: int = 200
    local_files_only: bool = True
    batch_size: int = 16


class SearchSettings(BaseModel):
    default_mode: str = "auto"
    default_limit: int = 10
    highlight_matches: bool = True
    save_latest_results: bool = True


class DeepSearchSettings(BaseModel):
    enabled: bool = True
    max_passes: int = 3
    max_candidates: int = 50
    rerank_top_n: int = 20
    query_expansion: bool = True
    suggest_followups: bool = True

    @field_validator("max_passes", "max_candidates", "rerank_top_n", mode="before")
    @classmethod
    def _positive_int(cls, value: Any, info) -> int:
        defaults = {"max_passes": 3, "max_candidates": 50, "rerank_top_n": 20}
        try:
            number = int(value)
        except (TypeError, ValueError):
            return defaults[info.field_name]
        return number if number > 0 else defaults[info.field_name]


class ResearchSettings(BaseModel):
    max_files: int = 12
    max_chunks: int = 20
    suggest_related_terms: bool = True

    @field_validator("max_files", "max_chunks", mode="before")
    @classmethod
    def _positive_int(cls, value: Any, info) -> int:
        defaults = {"max_files": 12, "max_chunks": 20}
        try:
            number = int(value)
        except (TypeError, ValueError):
            return defaults[info.field_name]
        return number if number > 0 else defaults[info.field_name]


class SimilarSettings(BaseModel):
    default_limit: int = 10
    min_score: float = 0.0

    @field_validator("default_limit", mode="before")
    @classmethod
    def _positive_limit(cls, value: Any) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return 10
        return number if number > 0 else 10

    @field_validator("min_score", mode="before")
    @classmethod
    def _nonnegative_score(cls, value: Any) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, number)


class TimelineSettings(BaseModel):
    default_limit: int = 50

    @field_validator("default_limit", mode="before")
    @classmethod
    def _positive_limit(cls, value: Any) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return 50
        return number if number > 0 else 50


class ProfilePresetSettings(BaseModel):
    folders: list[Path] = Field(default_factory=list)
    extensions: list[str] = Field(default_factory=list)
    default_mode: str = "hybrid"
    boost_terms: list[str] = Field(default_factory=list)

    @field_validator("folders", mode="before")
    @classmethod
    def _expand_folders(cls, value: Any) -> list[Path]:
        if value is None:
            return []
        return [_expand_path(item) for item in value]

    @field_validator("extensions", mode="before")
    @classmethod
    def _normalize_extensions(cls, value: Any) -> list[str]:
        if value is None:
            return []
        extensions: list[str] = []
        for item in value:
            text = str(item).strip().lower()
            if text and not text.startswith("."):
                text = f".{text}"
            if text:
                extensions.append(text)
        return extensions


class AssignmentSettings(BaseModel):
    default_limit: int = 20
    include_extensions: list[str] = Field(default_factory=lambda: [".pdf", ".docx", ".md", ".txt", ".csv", ".py"])

    @field_validator("default_limit", mode="before")
    @classmethod
    def _positive_limit(cls, value: Any) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return 20
        return number if number > 0 else 20

    @field_validator("include_extensions", mode="before")
    @classmethod
    def _normalize_extensions(cls, value: Any) -> list[str]:
        if value is None:
            return []
        extensions: list[str] = []
        for item in value:
            text = str(item).strip().lower()
            if text and not text.startswith("."):
                text = f".{text}"
            if text:
                extensions.append(text)
        return extensions


class ProjectsSettings(BaseModel):
    default_limit: int = 20
    infer_from_folders: bool = False

    @field_validator("default_limit", mode="before")
    @classmethod
    def _positive_limit(cls, value: Any) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return 20
        return number if number > 0 else 20


class IntelligenceSettings(BaseModel):
    duplicate_min_semantic_score: float = 0.92
    version_min_similarity: float = 0.72
    project_min_score: float = 0.55
    graph_max_nodes: int = 40
    graph_max_edges: int = 120
    health_check_limit: int = 100

    @field_validator("duplicate_min_semantic_score", "version_min_similarity", "project_min_score", mode="before")
    @classmethod
    def _score(cls, value: Any, info) -> float:
        defaults = {
            "duplicate_min_semantic_score": 0.92,
            "version_min_similarity": 0.72,
            "project_min_score": 0.55,
        }
        try:
            number = float(value)
        except (TypeError, ValueError):
            return defaults[info.field_name]
        return max(0.0, min(1.0, number))

    @field_validator("graph_max_nodes", "graph_max_edges", "health_check_limit", mode="before")
    @classmethod
    def _positive_int(cls, value: Any, info) -> int:
        defaults = {"graph_max_nodes": 40, "graph_max_edges": 120, "health_check_limit": 100}
        try:
            number = int(value)
        except (TypeError, ValueError):
            return defaults[info.field_name]
        return number if number > 0 else defaults[info.field_name]


class MetadataSettings(BaseModel):
    backup_dir: Path | None = None
    auto_backup_before_reset: bool = True
    export_format: str = "json"

    @field_validator("backup_dir", mode="before")
    @classmethod
    def _expand_backup_dir(cls, value: Any) -> Path | None:
        if value in (None, ""):
            return None
        return _expand_path(value)

    @field_validator("export_format", mode="before")
    @classmethod
    def _format(cls, value: Any) -> str:
        text = str(value or "json").strip().lower()
        return text if text in {"json"} else "json"


class UISettings(BaseModel):
    default_surface: str = "cli"
    tui_enabled: bool = True
    web_enabled: bool = True
    open_browser_on_web_start: bool = False

    @field_validator("default_surface", mode="before")
    @classmethod
    def _surface(cls, value: Any) -> str:
        text = str(value or "cli").strip().lower()
        return text if text in {"cli", "web", "tui"} else "cli"


class APISettings(BaseModel):
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 8766
    require_token: bool = True
    token_env: str = "KGFS_API_TOKEN"
    allow_file_actions: bool = False

    @field_validator("host", mode="before")
    @classmethod
    def _host(cls, value: Any) -> str:
        text = str(value or "127.0.0.1").strip()
        return text or "127.0.0.1"

    @field_validator("port", mode="before")
    @classmethod
    def _port(cls, value: Any) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return 8766
        return number if 0 < number < 65536 else 8766

    @field_validator("token_env", mode="before")
    @classmethod
    def _token_env(cls, value: Any) -> str:
        text = str(value or "KGFS_API_TOKEN").strip()
        return text or "KGFS_API_TOKEN"


class IntegrationSettings(BaseModel):
    enabled: bool = True
    raycast_enabled: bool = False
    alfred_enabled: bool = False
    powertoys_enabled: bool = False
    finder_enabled: bool = False
    explorer_enabled: bool = False
    tray_enabled: bool = False


class SqliteVecSettings(BaseModel):
    enabled: bool = False
    experimental: bool = True


class HnswSettings(BaseModel):
    enabled: bool = False
    space: str = "cosine"
    m: int = 16
    ef_construction: int = 200
    ef_search: int = 50

    @field_validator("m", "ef_construction", "ef_search", mode="before")
    @classmethod
    def _positive_int(cls, value: Any, info) -> int:
        defaults = {"m": 16, "ef_construction": 200, "ef_search": 50}
        try:
            number = int(value)
        except (TypeError, ValueError):
            return defaults[info.field_name]
        return number if number > 0 else defaults[info.field_name]

    @field_validator("space", mode="before")
    @classmethod
    def _normalize_space(cls, value: Any) -> str:
        text = str(value or "cosine").strip().lower()
        return text if text in {"cosine", "l2", "ip"} else "cosine"


class FaissSettings(BaseModel):
    enabled: bool = False
    index_type: str = "flat"
    use_gpu: bool = False

    @field_validator("index_type", mode="before")
    @classmethod
    def _normalize_index_type(cls, value: Any) -> str:
        text = str(value or "flat").strip().lower()
        return text if text in {"flat"} else "flat"


class VectorSettings(BaseModel):
    backend: str = "sqlite_scan"
    shard_strategy: str = "none"
    sqlite_vec: SqliteVecSettings = Field(default_factory=SqliteVecSettings)
    hnsw: HnswSettings = Field(default_factory=HnswSettings)
    faiss: FaissSettings = Field(default_factory=FaissSettings)


class HybridSettings(BaseModel):
    keyword_weight: float = 0.35
    semantic_weight: float = 0.45
    filename_weight: float = 0.15
    path_weight: float = 0.05
    exact_phrase_weight: float = 0.10
    recency_weight: float = 0.05
    candidate_limit_multiplier: int = 5

    @field_validator(
        "keyword_weight",
        "semantic_weight",
        "filename_weight",
        "path_weight",
        "exact_phrase_weight",
        "recency_weight",
        mode="before",
    )
    @classmethod
    def _coerce_weight(cls, value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @field_validator("candidate_limit_multiplier", mode="before")
    @classmethod
    def _coerce_candidate_limit_multiplier(cls, value: Any) -> int:
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return 5


class AISettings(BaseModel):
    enabled: bool = False
    provider: str = "openai"
    model: str = "gpt-5.4-nano"
    api_key_env: str = "OPENAI_API_KEY"
    require_confirmation: bool = True
    preview_context_before_send: bool = True
    send_file_paths: bool = False
    redact_home_path: bool = True
    send_full_file_text: bool = False
    max_results_sent: int = 12
    max_chars_per_result: int = 1500
    max_total_chars_sent: int = 12000
    allow_query_expansion: bool = True
    allow_rerank: bool = True
    allow_answer_synthesis: bool = True


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
    ocr: OCRSettings = Field(default_factory=OCRSettings)
    media: MediaSettings = Field(default_factory=MediaSettings)
    semantic: SemanticSettings = Field(default_factory=SemanticSettings)
    search: SearchSettings = Field(default_factory=SearchSettings)
    deep_search: DeepSearchSettings = Field(default_factory=DeepSearchSettings)
    research: ResearchSettings = Field(default_factory=ResearchSettings)
    similar: SimilarSettings = Field(default_factory=SimilarSettings)
    timeline: TimelineSettings = Field(default_factory=TimelineSettings)
    profiles: dict[str, ProfilePresetSettings] = Field(default_factory=dict)
    assignment: AssignmentSettings = Field(default_factory=AssignmentSettings)
    projects: ProjectsSettings = Field(default_factory=ProjectsSettings)
    intelligence: IntelligenceSettings = Field(default_factory=IntelligenceSettings)
    metadata: MetadataSettings = Field(default_factory=MetadataSettings)
    ui: UISettings = Field(default_factory=UISettings)
    api: APISettings = Field(default_factory=APISettings)
    integrations: IntegrationSettings = Field(default_factory=IntegrationSettings)
    vectors: VectorSettings = Field(default_factory=VectorSettings)
    hybrid: HybridSettings = Field(default_factory=HybridSettings)
    ai: AISettings = Field(default_factory=AISettings)

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

    @field_validator("profiles", mode="before")
    @classmethod
    def _empty_profiles_default(cls, value: Any) -> dict[str, Any]:
        return {} if value is None else value

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


def _expand_path(value: Any) -> Path:
    return expand_user_path(value)


DEFAULT_CONFIG_YAML = """# KG File Search config.
# Only folders listed here are indexed. KGFS will not scan anything until you
# explicitly add one or more folders.
indexed_folders: []
# Examples:
#  - "~/Documents"
#  - "~/Downloads"
#  - "~/Desktop"

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

ocr:
  # OCR is local-only and disabled by default. Enable only for folders you
  # explicitly configure above. KGFS never modifies images or PDFs.
  enabled: false
  backend: "tesseract"
  include_extensions:
    - ".png"
    - ".jpg"
    - ".jpeg"
    - ".tiff"
    - ".bmp"
  max_image_size_mb: 15
  cache_results: true
  modify_source_files: false
  min_pdf_text_chars: 20
  pdf_max_pages: null
  image_preprocessing: true
  tesseract:
    command: "tesseract"
    language: "eng"
  easyocr:
    enabled: false
    languages:
      - "en"
    gpu: false
  paddle:
    enabled: false
    language: "en"
  cloud_fallback:
    enabled: false
    provider: null
    require_confirmation: true
    preview_before_upload: true
    max_files_per_run: 5

media:
  enabled: false
  cache_results: true
  max_media_file_size_mb: 50
  photos:
    enabled: false
    index_exif: true
    include_extensions:
      - ".jpg"
      - ".jpeg"
      - ".png"
      - ".heic"
      - ".tiff"
    store_location_metadata: false
    location_precision: "none"
    generate_captions: false
  captions:
    enabled: false
    backend: "none"
    model_name: null
    local_files_only: true
    max_images_per_run: 50
  audio:
    enabled: false
    transcription_enabled: false
    backend: "none"
    include_extensions:
      - ".m4a"
      - ".mp3"
      - ".wav"
      - ".aac"
      - ".flac"
    model_name: null
    local_files_only: true
    max_audio_minutes_per_file: 60
  visual:
    enabled: false
    backend: "none"
    model_name: null
    local_files_only: true

semantic:
  enabled: false
  model_name: "sentence-transformers/all-MiniLM-L6-v2"
  chunk_size_chars: 1200
  chunk_overlap_chars: 200
  local_files_only: true
  batch_size: 16

search:
  default_mode: "auto"
  default_limit: 10
  highlight_matches: true
  save_latest_results: true

deep_search:
  enabled: true
  max_passes: 3
  max_candidates: 50
  rerank_top_n: 20
  query_expansion: true
  suggest_followups: true

research:
  max_files: 12
  max_chunks: 20
  suggest_related_terms: true

similar:
  default_limit: 10
  min_score: 0.0

timeline:
  default_limit: 50

profiles:
  # Optional named search presets. User-created workflow profiles are stored
  # in the KGFS database; config profiles are lightweight presets.
  # school:
  #   folders: []
  #   extensions:
  #     - ".pdf"
  #     - ".docx"
  #     - ".md"
  #   default_mode: "hybrid"
  #   boost_terms: []
  # audio:
  #   folders: []
  #   extensions: []
  #   default_mode: "hybrid"
  #   boost_terms:
  #     - "filter"
  #     - "crossover"
  #     - "op amp"
  #     - "frequency response"

assignment:
  default_limit: 20
  include_extensions:
    - ".pdf"
    - ".docx"
    - ".md"
    - ".txt"
    - ".csv"
    - ".py"

projects:
  default_limit: 20
  infer_from_folders: false

intelligence:
  duplicate_min_semantic_score: 0.92
  version_min_similarity: 0.72
  project_min_score: 0.55
  graph_max_nodes: 40
  graph_max_edges: 120
  health_check_limit: 100

metadata:
  backup_dir: null
  auto_backup_before_reset: true
  export_format: "json"

ui:
  default_surface: "cli"
  tui_enabled: true
  web_enabled: true
  open_browser_on_web_start: false

api:
  enabled: false
  host: "127.0.0.1"
  port: 8766
  require_token: true
  token_env: "KGFS_API_TOKEN"
  allow_file_actions: false

integrations:
  enabled: true
  raycast_enabled: false
  alfred_enabled: false
  powertoys_enabled: false
  finder_enabled: false
  explorer_enabled: false
  tray_enabled: false

vectors:
  backend: "sqlite_scan"
  shard_strategy: "none"
  sqlite_vec:
    enabled: false
    experimental: true
  hnsw:
    enabled: false
    space: "cosine"
    m: 16
    ef_construction: 200
    ef_search: 50
  faiss:
    enabled: false
    index_type: "flat"
    use_gpu: false

hybrid:
  keyword_weight: 0.35
  semantic_weight: 0.45
  filename_weight: 0.15
  path_weight: 0.05
  exact_phrase_weight: 0.10
  recency_weight: 0.05
  candidate_limit_multiplier: 5

ai:
  enabled: false
  provider: "openai"
  model: "gpt-5.4-nano"
  api_key_env: "OPENAI_API_KEY"
  require_confirmation: true
  preview_context_before_send: true
  send_file_paths: false
  redact_home_path: true
  send_full_file_text: false
  max_results_sent: 12
  max_chars_per_result: 1500
  max_total_chars_sent: 12000
  allow_query_expansion: true
  allow_rerank: true
  allow_answer_synthesis: true
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
