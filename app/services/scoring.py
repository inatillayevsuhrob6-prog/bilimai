"""Local scoring fallback and helpers, used when AI evaluation is unavailable."""
from difflib import SequenceMatcher


def _norm(s: str) -> str:
    return (s or "").strip().lower().replace("ё", "е")


def simple_match(user_answer: str, correct_answer: str) -> bool:
    a, b = _norm(user_answer), _norm(correct_answer)
    if not a:
        return False
    if a == b:
        return True
    return SequenceMatcher(None, a, b).ratio() >= 0.85


def local_evaluate(questions: list[dict], user_answers: dict[int, str]) -> dict:
    per_q = []
    correct = 0
    for q in questions:
        idx = q["order_index"]
        ua = user_answers.get(idx, "")
        ok = simple_match(ua, q["correct_answer"])
        if ok:
            correct += 1
        per_q.append({"order_index": idx, "is_correct": ok, "feedback": q.get("explanation", "")})
    total = len(questions) or 1
    return {
        "score": correct,
        "total": total,
        "percentage": round(correct / total * 100, 1),
        "per_question": per_q,
        "weak_concepts": [],
        "strong_concepts": [],
        "recommendations": "",
        "overall_analysis": "",
    }
