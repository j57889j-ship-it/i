from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

from app.config import Settings
from app.database.models import Book, Question
from app.services.books import normalize_text

logger = logging.getLogger("sahifa_quiz.ai")


class AIQuizError(RuntimeError):
    pass


def _extract_content(payload: dict[str, Any]) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AIQuizError("AI javobining formati kutilganidek emas.") from exc
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        content = "".join(parts)
    if not isinstance(content, str) or not content.strip():
        raise AIQuizError("AI bo‘sh javob qaytardi.")
    return content.strip()


def _parse_json(content: str) -> list[dict[str, Any]]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end <= start:
            raise AIQuizError("AI JSON qaytarmadi.")
        try:
            data = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise AIQuizError("AI javobi JSON sifatida o‘qilmadi.") from exc
    questions = data.get("questions") if isinstance(data, dict) else data
    if not isinstance(questions, list):
        raise AIQuizError("AI savollar ro‘yxatini qaytarmadi.")
    return [item for item in questions if isinstance(item, dict)]


def _validate_questions(raw: list[dict[str, Any]], requested: int, forbidden: set[str] | None = None) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    forbidden = forbidden or set()
    for item in raw:
        question = str(item.get("question") or item.get("text") or "").strip()
        options = item.get("options")
        if not isinstance(options, dict):
            options = {k: item.get(k) for k in ("A", "B", "C", "D")}
        a, b, c, d = (str(options.get(k) or "").strip() for k in ("A", "B", "C", "D"))
        correct = str(item.get("correct") or item.get("correct_option") or "").strip().upper()
        explanation = str(item.get("explanation") or "").strip()
        if len(question) < 8 or any(len(v) < 1 for v in (a, b, c, d)):
            continue
        if correct not in {"A", "B", "C", "D"}:
            if correct in {"1", "2", "3", "4"}:
                correct = "ABCD"[int(correct) - 1]
            else:
                continue
        key = normalize_text(question)
        if key in seen or key in forbidden:
            continue
        seen.add(key)
        result.append(
            {
                "text": question[:4000],
                "option_a": a[:1500],
                "option_b": b[:1500],
                "option_c": c[:1500],
                "option_d": d[:1500],
                "correct_option": correct,
                "explanation": explanation[:3000],
            }
        )
        if len(result) >= requested:
            break
    if len(result) < requested:
        raise AIQuizError(f"AI faqat {len(result)} ta yaroqli savol qaytardi, {requested} ta kerak.")
    return result


def _prompt(book: Book, count: int, reference_questions: list[Question] | None = None) -> str:
    description = (book.description or "").strip()
    if not description:
        description = "Kitob tavsifi kiritilmagan; savollar faqat nom va muallif haqida aniq bo‘lgan ma’lumotlar bilan cheklanmasin, noma’lum syujet tafsilotlarini uydirmasin."
    description = description[:8000]
    reference_block = ""
    if reference_questions:
        examples = []
        for idx, item in enumerate(reference_questions[:10], 1):
            examples.append(
                f"{idx}) {item.text[:500]} | A: {item.option_a[:180]} | B: {item.option_b[:180]} | C: {item.option_c[:180]} | D: {item.option_d[:180]}"
            )
        reference_block = (
            "\nQuyidagi savollar faqat mavzu va qiyinlik darajasini tushunish uchun namuna. Ularni qayta yozmang, variantlarini ko‘chirmang va ulardan nusxa olmang:\n"
            + "\n".join(examples)
            + "\n"
        )
    return (
        "Siz professional adabiyot viktorina tuzuvchisiz. O‘zbek tilida quiz yarating.\n"
        f"Kitob: {book.title}\nMuallif: {book.author or 'Noma’lum'}\n"
        f"Tavsif: {description}\n"
        f"{reference_block}\n"
        f"Aynan {count} ta turli, mazmunli, bir-biridan mustaqil multiple-choice savol yarating. "
        "Har savolda faqat bitta aniq to‘g‘ri javob bo‘lsin. Uydirma syujet faktlarini kiritmang; berilgan ma’lumot yetarli bo‘lmasa, noma’lum voqealarni ixtiro qilmang. "
        "Savollarni o‘z so‘zlaringiz bilan yozing, uzun iqtiboslardan foydalanmang. Har bir variant o‘zaro mantiqan farqlansin. "
        "Javobni faqat JSON ko‘rinishida qaytaring:\n"
        '{"questions":[{"question":"...","options":{"A":"...","B":"...","C":"...","D":"..."},"correct":"A","explanation":"..."}]}\n'
        "Hech qanday markdown, izoh yoki qo‘shimcha matn yozmang."
    )


async def generate_ai_questions(
    settings: Settings,
    book: Book,
    count: int,
    reference_questions: list[Question] | None = None,
    forbidden_questions: set[str] | None = None,
) -> list[dict[str, str]]:
    if not settings.ai_enabled:
        raise AIQuizError("AI quiz hali yoqilmagan. Render’da AI_API_KEY sozlang.")
    count = max(5, min(count, settings.ai_quiz_max_questions))
    base = settings.ai_base_url.rstrip("/")
    endpoint = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.ai_api_key}",
        "Content-Type": "application/json",
        "X-Title": settings.app_name,
    }
    payload = {
        "model": settings.ai_model,
        "messages": [
            {"role": "system", "content": "You generate careful educational multiple-choice quizzes and must obey the requested JSON format."},
            {"role": "user", "content": _prompt(book, count, reference_questions)},
        ],
        "temperature": 0.35,
        "max_tokens": max(1800, count * 280),
    }
    last_status = None
    async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
        for attempt in range(2):
            try:
                response = await client.post(endpoint, headers=headers, json=payload)
            except httpx.TimeoutException as exc:
                if attempt == 0:
                    await asyncio.sleep(0.8)
                    continue
                raise AIQuizError("AI serverga ulanish vaqti tugadi. Qayta urinib ko‘ring.") from exc
            except httpx.HTTPError as exc:
                raise AIQuizError("AI serveriga ulanishda xato yuz berdi.") from exc
            last_status = response.status_code
            if response.status_code in {429, 500, 502, 503, 504} and attempt == 0:
                await asyncio.sleep(1.0)
                continue
            break
    if last_status is None or response.status_code >= 400:
        detail = response.text[:350].replace("\n", " ")
        logger.warning("AI provider HTTP %s: %s", response.status_code, detail)
        if response.status_code == 429:
            raise AIQuizError("AI limiti vaqtincha tugagan. Birozdan keyin urinib ko‘ring.")
        raise AIQuizError(f"AI server xatosi ({response.status_code}).")
    try:
        data = response.json()
    except ValueError as exc:
        raise AIQuizError("AI server noto‘g‘ri JSON qaytardi.") from exc
    raw = _parse_json(_extract_content(data))
    return _validate_questions(raw, count, forbidden=forbidden_questions)
