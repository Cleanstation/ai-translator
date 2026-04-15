import pytest

from ai_translator import parse_translation_response


def test_parse_translations_accepts_raw_json():
    output = '{"電源板": "power-board"}'
    assert parse_translation_response(output) == {"電源板": "power-board"}


def test_parse_translations_accepts_fenced_json():
    output = '```json\n{"電源板": "power-board"}\n```'
    assert parse_translation_response(output) == {"電源板": "power-board"}


def test_parse_translations_accepts_embedded_json_object():
    output = 'Here is the result:\n{"電源板": "power-board"}\nThanks.'
    assert parse_translation_response(output) == {"電源板": "power-board"}


def test_parse_translations_raises_for_invalid_output():
    with pytest.raises(ValueError):
        parse_translation_response('not-json')


def test_parse_translations_raises_for_empty_output():
    with pytest.raises(ValueError, match="空的 LLM 回應"):
        parse_translation_response("   ")


def test_parse_translations_rejects_non_object_json():
    with pytest.raises(ValueError):
        parse_translation_response('["not", "an", "object"]')
