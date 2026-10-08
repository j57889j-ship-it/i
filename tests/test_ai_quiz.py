import json
from types import SimpleNamespace

from app.services.ai_quiz import _extract_content, _parse_json, _prompt, _validate_questions


def test_ai_json_parser_accepts_markdown_fence():
    payload = {
        "questions": [
            {
                "question": "Kitobning mavzusi nima?",
                "options": {"A": "A", "B": "B", "C": "C", "D": "D"},
                "correct": "B",
                "explanation": "Izoh",
            }
        ]
    }
    content = "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"
    parsed = _parse_json(content)
    result = _validate_questions(parsed, 1)
    assert result[0]["correct_option"] == "B"


def test_ai_validator_rejects_duplicates_and_supports_numeric_correct():
    raw = [
        {"question": "Bir xil savol 1?", "A": "1", "B": "2", "C": "3", "D": "4", "correct": "2"},
        {"question": "Bir xil savol 1?", "A": "1", "B": "2", "C": "3", "D": "4", "correct": "B"},
        {"question": "Ikkinchi savol?", "A": "1", "B": "2", "C": "3", "D": "4", "correct": "D"},
    ]
    result = _validate_questions(raw, 2)
    assert len(result) == 2
    assert result[0]["correct_option"] == "B"


def test_extract_content_from_openai_shape():
    payload = {"choices": [{"message": {"content": "{\\\"questions\\\": []}"}}]}
    assert _extract_content(payload).startswith("{")


def test_prompt_includes_reference_questions_without_copying_instruction():
    book = SimpleNamespace(title="Atomic Habits", author="James Clear", description="Odatlar haqida kitob")
    reference = [SimpleNamespace(text="Qanday odat shakllanadi?", option_a="A", option_b="B", option_c="C", option_d="D")]
    prompt = _prompt(book, 10, reference)
    assert "Qanday odat shakllanadi?" in prompt
    assert "qayta yozmang" in prompt
    assert '"questions"' in prompt
