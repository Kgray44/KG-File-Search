from pathlib import Path

from kgfs.ai import (
    AIError,
    build_ai_context,
    get_openai_api_key,
    redact_home_path,
    rerank_results_with_ai,
)
from kgfs.config import AISettings
from kgfs.models import SearchResult


class FakeAIClient:
    def __init__(self, output_text: str = "[2, 1]") -> None:
        self.output_text = output_text
        self.calls = []

    def create_response(self, *, model: str, input_text: str) -> str:
        self.calls.append({"model": model, "input_text": input_text})
        return self.output_text


def _result(result_id: int, path: Path, snippet: str) -> SearchResult:
    return SearchResult(
        result_id=result_id,
        file_id=result_id,
        file_name=path.name,
        path=path,
        extension=path.suffix,
        modified_time=1.0,
        score=0.5,
        snippet=snippet,
    )


def test_get_openai_api_key_requires_environment_variable(monkeypatch) -> None:
    settings = AISettings(enabled=True, api_key_env="OPENAI_API_KEY")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    try:
        get_openai_api_key(settings)
    except AIError as exc:
        assert "OPENAI_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected missing API key to raise")


def test_redact_home_path_handles_windows_and_macos_styles() -> None:
    text = (
        "C:\\Users\\Student Name\\Documents\\notes.md\n"
        "C:/Users/Student Name/Desktop/lab.md\n"
        "/Users/student/Documents/report.md"
    )

    redacted = redact_home_path(text, homes=["C:\\Users\\Student Name", "/Users/student"])

    assert "C:\\Users\\Student Name" not in redacted
    assert "C:/Users/Student Name" not in redacted
    assert "/Users/student" not in redacted
    assert "[HOME]" in redacted


def test_build_ai_context_omits_paths_and_full_text_by_default(tmp_path: Path) -> None:
    private_file = tmp_path / "private notes.md"
    private_file.write_text("FULL_FILE_SECRET motor torque calculations", encoding="utf-8")
    settings = AISettings(enabled=True)
    result = _result(1, private_file, "safe snippet about motor torque")

    context = build_ai_context("motor torque?", [result], settings, home=tmp_path)

    assert "safe snippet about motor torque" in context
    assert "FULL_FILE_SECRET" not in context
    assert str(private_file) not in context


def test_build_ai_context_includes_full_text_only_when_explicitly_enabled(tmp_path: Path) -> None:
    private_file = tmp_path / "lab.md"
    private_file.write_text("FULL_FILE_ALLOWED text", encoding="utf-8")
    result = _result(1, private_file, "snippet text")

    default_context = build_ai_context("lab?", [result], AISettings(enabled=True), home=tmp_path)
    explicit_context = build_ai_context(
        "lab?",
        [result],
        AISettings(enabled=True, send_full_file_text=True),
        home=tmp_path,
    )

    assert "FULL_FILE_ALLOWED" not in default_context
    assert "FULL_FILE_ALLOWED" in explicit_context


def test_build_ai_context_includes_redacted_paths_only_when_allowed(tmp_path: Path) -> None:
    file_path = tmp_path / "Folder With Spaces" / "Résumé.md"
    result = _result(1, file_path, "snippet")

    hidden_context = build_ai_context("query", [result], AISettings(enabled=True), home=tmp_path)
    visible_context = build_ai_context(
        "query",
        [result],
        AISettings(enabled=True, send_file_paths=True),
        home=tmp_path,
    )

    assert "Path:" not in hidden_context
    assert "Path:" in visible_context
    assert str(tmp_path) not in visible_context
    assert "[HOME]" in visible_context


def test_rerank_sends_only_allowed_snippets_to_ai(tmp_path: Path) -> None:
    file_path = tmp_path / "notes.md"
    file_path.write_text("FULL_FILE_SECRET should not be sent", encoding="utf-8")
    results = [
        _result(1, file_path, "snippet one"),
        _result(2, tmp_path / "other.md", "snippet two"),
    ]
    client = FakeAIClient("[2, 1]")

    reranked = rerank_results_with_ai("query", results, AISettings(enabled=True), client)

    sent = client.calls[0]["input_text"]
    assert [result.result_id for result in reranked] == [2, 1]
    assert "snippet one" in sent
    assert "snippet two" in sent
    assert "FULL_FILE_SECRET" not in sent
    assert str(file_path) not in sent


def test_ai_context_strips_terminal_highlight_markup(tmp_path: Path) -> None:
    result = _result(1, tmp_path / "notes.md", "[bold]motor[/bold] torque")

    context = build_ai_context("motor", [result], AISettings(enabled=True), home=tmp_path)

    assert "[bold]" not in context
    assert "motor torque" in context
