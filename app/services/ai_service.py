"""AI service — robust JSON extraction, works with ANY chat model."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AIUnavailable(Exception):
    pass


LANG_INSTRUCTION = {
    "uz": "Javobni FAQAT o'zbek tilida yoz. Matematik va ilmiy atamalarni to'g'ri saqlab qol.",
    "ru": "Отвечай ТОЛЬКО на русском языке. Сохраняй корректную научную терминологию.",
    "en": "Answer ONLY in English. Keep scientific terminology accurate.",
}


def _client() -> httpx.Client:
    if not settings.AI_API_KEY:
        raise AIUnavailable("AI_API_KEY is not configured")
    return httpx.Client(
        base_url=settings.AI_BASE_URL,
        headers={
            "Authorization": f"Bearer {settings.AI_API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=settings.AI_TIMEOUT,
    )


def _chat(messages: list[dict], temperature: float = 0.4) -> str:
    """Plain chat completion. NO response_format — prompt asks for JSON."""
    payload: dict[str, Any] = {
        "model": settings.AI_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    try:
        with _client() as client:
            r = client.post("/chat/completions", json=payload)
            if r.status_code != 200:
                logger.error("AI HTTP %s: %s", r.status_code, r.text[:400])
                raise AIUnavailable(f"HTTP {r.status_code}: {r.text[:200]}")
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            if not content:
                raise AIUnavailable("Empty content from AI")
            return content
    except httpx.HTTPError as e:
        logger.error("AI HTTP error: %s", e)
        raise AIUnavailable(str(e))
    except (KeyError, ValueError) as e:
        logger.error("AI parse error: %s", e)
        raise AIUnavailable(str(e))


def _extract_json(text: str) -> dict:
    """Extract JSON from messy AI output — very forgiving."""
    if not text:
        raise AIUnavailable("Empty AI response")

    s = text.strip()

    # Remove markdown fences
    s = re.sub(r"^```(?:json|JSON)?\s*", "", s)
    s = re.sub(r"\s*```\s*$", "", s)
    s = s.strip()

    # Try direct
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # Find balanced outermost {...}
    start = s.find("{")
    if start == -1:
        raise AIUnavailable("No JSON object in response")

    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    candidate = s[start:i + 1]
                    # Try parse; if fails, fix trailing commas
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        fixed = re.sub(r",(\s*[}\]])", r"\1", candidate)
                        try:
                            return json.loads(fixed)
                        except json.JSONDecodeError as e:
                            logger.error("JSON parse failed: %s\nRaw: %s", e, candidate[:500])
                            raise AIUnavailable(f"JSON parse error: {e}")
    raise AIUnavailable("Unbalanced JSON in AI response")


# ============================================================
# Public API
# ============================================================

def analyze_lesson(subject: str, topic: str, content: str,
                   notes: str | None, lang: str) -> dict:
    sys = (f"Siz BilimAI ta'lim yordamchisisiz. {LANG_INSTRUCTION.get(lang, LANG_INSTRUCTION['uz'])} "
           "Faqat JSON formatda javob bering. Boshqa hech qanday matn yozmang. "
           "Faqat foydalanuvchi yozgan materialga tayanib tahlil qiling.")
    user = f"""Dars ma'lumotlari:
Fan: {subject}
Mavzu: {topic}
Bilganlari: {content}
Eslatmalar: {notes or "(yo'q)"}

Faqat shu ko'rinishdagi JSON qaytaring:
{{
  "summary": "2-3 gaplik xulosa",
  "topics": ["asosiy tushuncha 1", "asosiy tushuncha 2", "asosiy tushuncha 3"],
  "keywords": ["atama 1", "atama 2"]
}}"""
    raw = _chat([{"role": "system", "content": sys},
                 {"role": "user", "content": user}])
    return _extract_json(raw)


def generate_questions(subject: str, topic: str, content: str,
                       summary: str, lang: str) -> list[dict]:
    sys = (f"Siz BilimAI test generatorisiz. {LANG_INSTRUCTION.get(lang, LANG_INSTRUCTION['uz'])} "
           "Faqat JSON formatda javob bering. Boshqa hech qanday matn yozmang.")
    user = f"""Fan: {subject}
Mavzu: {topic}
Bilganlar: {content}
Xulosa: {summary}

AYNAN 10 TA savol tuzing. Turlari aralash:
- "mcq": 4 variantli savol
- "true_false": to'g'ri/noto'g'ri
- "short": qisqa javob
- "concept": tushunchani izohlash

Qiyinliklar: "easy", "medium", "hard" — aralash bo'lsin.

FAQAT shu JSON:
{{
  "questions": [
    {{"order_index": 1, "qtype": "mcq", "difficulty": "easy",
      "question_text": "...", "options": ["A","B","C","D"],
      "correct_answer": "A", "explanation": "..."}}
  ]
}}

"questions" massivida AYNAN 10 ta element bo'lishi SHART."""
    raw = _chat([{"role": "system", "content": sys},
                 {"role": "user", "content": user}], temperature=0.7)
    data = _extract_json(raw)
    qs = data.get("questions") or data.get("items") or []
    if not isinstance(qs, list):
        raise AIUnavailable("Questions is not a list")
    if len(qs) < 10:
        raise AIUnavailable(f"AI returned only {len(qs)} questions")
    # Normalize
    for i, q in enumerate(qs[:10], start=1):
        q.setdefault("order_index", i)
        q.setdefault("qtype", "mcq")
        q.setdefault("difficulty", "medium")
        q.setdefault("options", None)
        q.setdefault("explanation", "")
        if not q.get("question_text"):
            raise AIUnavailable("Question missing text")
        if not q.get("correct_answer"):
            raise AIUnavailable("Question missing correct_answer")
    return qs[:10]


def evaluate_answers(lesson_ctx: dict, questions: list[dict],
                     user_answers: dict[int, str], lang: str) -> dict:
    payload = {
        "subject": lesson_ctx.get("subject"),
        "topic": lesson_ctx.get("topic"),
        "questions": [
            {
                "order_index": q["order_index"],
                "question_text": q["question_text"],
                "correct_answer": q["correct_answer"],
                "user_answer": user_answers.get(q["order_index"], ""),
            }
            for q in questions
        ],
    }
    sys = (f"Siz BilimAI o'qituvchisisiz. {LANG_INSTRUCTION.get(lang, LANG_INSTRUCTION['uz'])} "
           "Xatolarni muloyim va rag'batlantiruvchi tarzda tahlil qiling. "
           "Faqat JSON formatda javob bering.")
    user = f"""Javoblarni baholang:
{json.dumps(payload, ensure_ascii=False, indent=2)}

FAQAT shu JSON:
{{
  "score": <to'g'ri javob soni>,
  "total": {len(questions)},
  "percentage": <0..100>,
  "per_question": [
    {{"order_index": 1, "is_correct": true, "feedback": "izoh"}}
  ],
  "weak_concepts": ["zaif mavzu"],
  "strong_concepts": ["kuchli mavzu"],
  "recommendations": "nimani takrorlash kerak",
  "overall_analysis": "umumiy xulosa"
}}"""
    raw = _chat([{"role": "system", "content": sys},
                 {"role": "user", "content": user}], temperature=0.3)
    return _extract_json(raw)


def ai_chat_reply(messages: list[dict], lesson_context: str | None, lang: str) -> str:
    """Plain text reply — no JSON needed."""
    sys = (f"Siz BilimAI — shaxsiy AI o'qituvchisiz. {LANG_INSTRUCTION.get(lang, LANG_INSTRUCTION['uz'])} "
           "Muloyim, aniq, qisqa javob bering. Markdown ishlating (ro'yxatlar, qalin matn). "
           "Agar javob foydalanuvchining saqlangan darsidan olingan bo'lsa — buni ayting. "
           "Aks holda umumiy ta'limiy tushuntirish ekanligini belgilang.")
    if lesson_context:
        sys += f"\n\nFoydalanuvchining saqlangan darsi:\n{lesson_context[:2000]}"
    full = [{"role": "system", "content": sys}] + messages[-12:]
    return _chat(full, temperature=0.6)
