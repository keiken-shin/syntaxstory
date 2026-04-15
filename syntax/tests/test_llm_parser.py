import pytest
from app.llm.parser import parse_yaml_safely, extract_yaml_from_text, YamlParsingError

def test_extract_yaml_fenced():
    text = "Here is some text:\n```yaml\ntitle: Test\nvalue: 1\n```\nMore text."
    assert extract_yaml_from_text(text) == "title: Test\nvalue: 1"

def test_extract_yaml_fenced_no_lang():
    text = "```\ntitle: Test\n```"
    assert extract_yaml_from_text(text) == "title: Test"

def test_extract_yaml_unfenced():
    text = "title: Test\nvalue: 1"
    assert extract_yaml_from_text(text) == "title: Test\nvalue: 1"

def test_parse_yaml_safely_valid():
    text = "key: value\nnested:\n  a: 1"
    parsed = parse_yaml_safely(text)
    assert parsed["key"] == "value"
    assert parsed["nested"]["a"] == 1

def test_parse_yaml_safely_with_markdown():
    text = "Output:\n```yml\nversion: 1.0\n```"
    parsed = parse_yaml_safely(text)
    assert parsed["version"] == 1.0

def test_parse_yaml_safely_invalid_yaml():
    text = "key: \n- this: [is broken"
    with pytest.raises(YamlParsingError) as exc:
        parse_yaml_safely(text)
    assert "YAML parser error" in str(exc.value)

def test_parse_yaml_safely_not_dict_or_list():
    text = "```yaml\njust a string\n```"
    with pytest.raises(YamlParsingError) as exc:
        parse_yaml_safely(text)
    assert "YAML root must be a dictionary/object/list" in str(exc.value)

def test_parse_yaml_safely_empty():
    with pytest.raises(YamlParsingError) as exc:
        parse_yaml_safely("")
    assert "Provided text is empty" in str(exc.value)
