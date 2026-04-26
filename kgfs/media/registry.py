"""Tiny registry helpers for implemented media scaffold names."""

from __future__ import annotations

CAPTION_BACKENDS = ("none",)
AUDIO_BACKENDS = ("none",)
VISUAL_BACKENDS = ("none",)


def list_caption_backends() -> list[str]:
    return list(CAPTION_BACKENDS)


def list_audio_backends() -> list[str]:
    return list(AUDIO_BACKENDS)


def list_visual_backends() -> list[str]:
    return list(VISUAL_BACKENDS)
