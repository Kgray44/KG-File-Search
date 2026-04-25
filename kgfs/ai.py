"""Optional OpenAI AI Assist layer.

This module is intentionally downstream of local search. It prepares a small,
redacted context from KGFS result snippets and calls OpenAI only when AI Assist
is enabled and the CLI asks it to.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from kgfs.core.config import AISettings
from kgfs.core.models import SearchResult


class AIError(RuntimeError):
    """Raised when AI Assist is unavailable or disabled."""


class AIClient(Protocol):
    def create_response(self, *, model: str, input_text: str) -> str:
        """Create a response and return output text."""


@dataclass(frozen=True)
class AIResult:
    text: str
    context: str


class OpenAIResponsesClient:
    def __init__(self, settings: AISettings) -> None:
        api_key = get_openai_api_key(settings)
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AIError('OpenAI SDK is not installed. Install with: python -m pip install -e ".[openai]"') from exc
        self._client = OpenAI(api_key=api_key)

    def create_response(self, *, model: str, input_text: str) -> str:
        response = self._client.responses.create(model=model, input=input_text)
        return getattr(response, "output_text", str(response))


def get_openai_client(settings: AISettings) -> AIClient:
    return OpenAIResponsesClient(settings)


def ensure_ai_enabled(settings: AISettings) -> None:
    if not settings.enabled:
        raise AIError("AI Assist is disabled. Set ai.enabled: true in config.yaml to opt in.")
    if settings.provider != "openai":
        raise AIError(f"Unsupported AI provider: {settings.provider}")


def get_openai_api_key(settings: AISettings) -> str:
    value = os.environ.get(settings.api_key_env, "").strip()
    if not value:
        raise AIError(f"Missing API key. Set the {settings.api_key_env} environment variable.")
    return value


def build_ai_context(
    question: str,
    results: list[SearchResult],
    settings: AISettings,
    *,
    home: Path | None = None,
) -> str:
    """Build the exact context that may be sent to OpenAI."""

    limited_results = results[: settings.max_results_sent]
    parts = [
        "KG File Search AI Assist Context",
        f"Question: {question}",
        "Only use the local result snippets below. Cite KGFS result IDs.",
        "",
    ]
    total_chars = sum(len(part) for part in parts)

    for result in limited_results:
        block = _result_context_block(result, settings)
        if settings.redact_home_path:
            block = redact_home_path(block, homes=[home or Path.home()])
        block = block[: settings.max_chars_per_result]
        if total_chars + len(block) > settings.max_total_chars_sent:
            remaining = settings.max_total_chars_sent - total_chars
            if remaining <= 0:
                break
            block = block[:remaining]
        parts.append(block)
        parts.append("")
        total_chars += len(block)

    context = "\n".join(parts)
    if settings.redact_home_path:
        context = redact_home_path(context, homes=[home or Path.home()])
    return context[: settings.max_total_chars_sent]


def answer_question_with_ai(
    question: str,
    results: list[SearchResult],
    settings: AISettings,
    client: AIClient,
) -> AIResult:
    ensure_ai_enabled(settings)
    context = build_ai_context(question, results, settings)
    prompt = (
        "Answer the user's question using only the KGFS local search context. "
        "Mention relevant KGFS result IDs. If the context is insufficient, say so.\n\n"
        f"{context}"
    )
    return AIResult(text=client.create_response(model=settings.model, input_text=prompt), context=context)


def rerank_results_with_ai(
    query: str,
    results: list[SearchResult],
    settings: AISettings,
    client: AIClient,
) -> list[SearchResult]:
    ensure_ai_enabled(settings)
    if not results:
        return []
    context = build_ai_context(query, results, settings)
    prompt = (
        "Return a JSON array of KGFS result IDs ordered from most to least relevant for the query. "
        "Use only the provided snippets and do not include explanations.\n\n"
        f"{context}"
    )
    output = client.create_response(model=settings.model, input_text=prompt)
    ordered_ids = _parse_result_id_order(output)
    by_id = {result.result_id: result for result in results}
    reranked = [by_id[result_id] for result_id in ordered_ids if result_id in by_id]
    reranked.extend(result for result in results if result.result_id not in set(ordered_ids))
    return reranked


def redact_home_path(text: str, *, homes: list[str | Path]) -> str:
    redacted = text
    for home in homes:
        raw = str(home)
        variants = {raw, raw.replace("\\", "/"), raw.replace("/", "\\")}
        for variant in sorted(variants, key=len, reverse=True):
            if variant:
                redacted = redacted.replace(variant, "[HOME]")
    return redacted


def _result_context_block(result: SearchResult, settings: AISettings) -> str:
    lines = [
        f"Result ID: {result.result_id}",
        f"File name: {result.file_name}",
        f"Score: {result.score:.3f}",
    ]
    if settings.send_file_paths:
        lines.append(f"Path: {result.path}")
    if settings.send_full_file_text:
        lines.append("Text:")
        lines.append(_read_limited_file_text(result.path, settings.max_chars_per_result))
    else:
        lines.append("Snippet:")
        lines.append(_strip_rich_markup(result.snippet))
    return "\n".join(lines)


def _read_limited_file_text(path: Path, max_chars: int) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except OSError:
        return ""


def _strip_rich_markup(text: str) -> str:
    return re.sub(r"\[/?bold\]", "", text)


def _parse_result_id_order(output: str) -> list[int]:
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        match = re.search(r"\[[^\]]*\]", output)
        if not match:
            return [int(value) for value in re.findall(r"\d+", output)]
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
    if not isinstance(parsed, list):
        return []
    return [int(item) for item in parsed if isinstance(item, int) or str(item).isdigit()]
