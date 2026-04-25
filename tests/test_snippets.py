from kgfs.snippets import make_snippet


def test_make_snippet_prefers_query_term_context() -> None:
    text = "Intro text. The lab report calculated motor torque using measured current and voltage."

    snippet = make_snippet(text, "motor torque", max_chars=50)

    assert "motor torque" in snippet.lower()
    assert len(snippet) <= 53


def test_make_snippet_handles_empty_text() -> None:
    assert make_snippet("", "query") == ""


def test_make_snippet_handles_multiline_unicode_and_punctuation() -> None:
    text = "Intro line\nRésumé notes discuss op-amps, Thevenin equivalents, and torque."

    snippet = make_snippet(text, '"op-amps?" résumé', max_chars=70)

    assert "\n" not in snippet
    assert "Résumé" in snippet
    assert "op-amps" in snippet


def test_make_snippet_can_highlight_matched_terms() -> None:
    snippet = make_snippet("Motor torque lab notes", "motor torque", highlight=True)

    assert "[bold]" in snippet


def test_make_snippet_prefers_exact_phrase_context() -> None:
    text = (
        "The first section only mentions op and gain separately. "
        "Later, the lab explains op amp gain with feedback and stability."
    )

    snippet = make_snippet(text, "op amp gain", max_chars=68)

    assert "op amp gain" in snippet.lower()


def test_make_snippet_no_match_fallback_is_clean() -> None:
    snippet = make_snippet("Short unrelated document with normal spacing.", "missing phrase", max_chars=24)

    assert snippet.strip() == snippet
    assert "\n" not in snippet
    assert len(snippet) <= 30


def test_make_snippet_highlighting_escapes_rich_markup_characters() -> None:
    snippet = make_snippet("Use [gain] brackets in op amp notes", "op amp", highlight=True)

    assert "\\[gain]" in snippet
    assert "[bold]op[/bold]" in snippet
