import re


def test_scene_separator_regex():
    separator = re.compile(r'^(?:\*{3,}|-{3,}|_{3,}|#{3,})$')

    assert separator.fullmatch("***")
    assert separator.fullmatch("-----")
    assert separator.fullmatch("___")
    assert separator.fullmatch("###")
    assert not separator.fullmatch("real paragraph")
