from pathlib import Path

from kgfs.path_utils import expand_user_path


def test_expand_user_path_handles_posix_tilde_with_spaces_and_unicode(tmp_path: Path) -> None:
    home = tmp_path / "Home Folder" / "Zoë"

    expanded = expand_user_path("~/Documents/Circuits Notes", home=home)

    assert expanded == home / "Documents" / "Circuits Notes"


def test_expand_user_path_handles_windows_tilde_separator_on_any_host(tmp_path: Path) -> None:
    home = tmp_path / "Users" / "Student Name"

    expanded = expand_user_path("~\\Documents\\Résumé (final).md", home=home)

    assert expanded == home / "Documents" / "Résumé (final).md"

