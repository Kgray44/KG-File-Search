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
