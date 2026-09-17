from app.protocol import DEVELOPER_FAST


def test_prompt_demands_material_event_completeness():
    prompt = DEVELOPER_FAST.lower()
    assert "ev completeness" in prompt
    assert "several ev lines" in prompt
    assert "final substantive paragraph" in prompt


def test_prompt_distinguishes_document_text_from_speech():
    prompt = DEVELOPER_FAST.lower()
    assert "document is not say" in prompt or "document text is not say" in prompt
    assert "note, letter, sign, message, or document" in prompt


def test_prompt_allows_unknown_end_location():
    prompt = DEVELOPER_FAST.lower()
    assert "leave the value empty" in prompt
    assert "loc=" in prompt
