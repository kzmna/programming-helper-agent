"""
Tools for generating, storing, and grading programming quizzes (JSON-based).

These tools are designed for the Quiz Agent:
- Create a quiz on a user-chosen topic
- Persist quizzes in JSON storage (memory/quizzes.json by default)
- Retrieve and list stored quizzes
- Grade user answers deterministically (for MCQ) and semi-structured (for short answers)

All tools return JSON strings for consistent logging/parsing in LangGraph.
"""

from future import annotations

from langchain_core.tools import tool

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ----------------------------
# Storage helpers
# ----------------------------

def _project_root() -> Path:
    # quiz_tools.py expected in tools/
    return Path(file).resolve().parent.parent


def _quiz_path() -> Path:
    """
    Where quizzes are stored.
    Default: memory/quizzes.json
    Override: QUIZ_PATH env var
    """
    root = _project_root()
    qp = os.getenv("QUIZ_PATH", "memory/quizzes.json")
    return (root / qp).resolve()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_quizzes() -> List[Dict[str, Any]]:
    path = _quiz_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        return []

    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []

    data = json.loads(raw)

    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _save_quizzes(items: List[Dict[str, Any]]) -> None:
    path = _quiz_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_topic(topic: str) -> str:
    return re.sub(r"\s+", " ", topic.strip())


def _cap_int(x: int, lo: int, hi: int) -> int:
    return max(lo, min(int(x), hi))


# ----------------------------
# Quiz schema helpers
# ----------------------------

def _new_quiz_id() -> str:
    return uuid.uuid4().hex


def _make_mcq_question(
    qid: str,
    prompt: str,
    options: List[str],
    correct_index: int,
    explanation: str = "",
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "id": qid,
        "type": "mcq",
        "prompt": prompt,
        "options": options,
        "answer": correct_index,  # integer index into options
        "explanation": explanation,
        "tags": tags or [],
    }


def _make_short_question(
    qid: str,
    prompt: str,
    rubric: str,
    sample_answer: str = "",
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "id": qid,
        "type": "short",
        "prompt": prompt,
        "rubric": rubric,
        "sample_answer": sample_answer,
        "tags": tags or [],
    }


# ----------------------------
# Tools
# ----------------------------

@tool
def create_quiz(topic: str, num_questions: int = 5, difficulty: str = "mixed") -> str:
    """Create a programming quiz on the given topic and save it to JSON storage.

    The tool creates a quiz container and a *draft* set of questions. The Quiz Agent
    may refine the questions in its own reasoning before returning them to the user,
    but this tool ensures the quiz is persisted and has a stable quiz_id.

    Notes:
    - This tool does NOT call external APIs and does not require a database.
    - It produces a balanced template: MCQ + short-answer depending on count.
    - The agent can later update by overwriting via save_quiz tool if you add it.

    Args:
        topic: Programming topic (e.g., "Python списки и словари", "SQL JOIN", "Git rebase")
        num_questions: Number of questions (default: 5, max: 20)
        difficulty: "easy" | "medium" | "hard" | "mixed"

    Returns:
        JSON string with quiz_id, topic, difficulty, and the generated questions.

        Example:
        create_quiz("Python exceptions", num_questions=6, difficulty="medium")
    """
    try:
        if not isinstance(topic, str) or not topic.strip():
            raise ValueError("topic must be a non-empty string")

        topic_n = _normalize_topic(topic)
        n = _cap_int(num_questions, 1, 20)
        diff = (difficulty or "mixed").strip().lower()
        if diff not in {"easy", "medium", "hard", "mixed"}:
            diff = "mixed"

        quiz_id = _new_quiz_id()

        # Simple template generation:
        # - ~70% MCQ, remaining short
        mcq_count = max(1, round(n * 0.7)) if n > 1 else 1
        short_count = n - mcq_count

        questions: List[Dict[str, Any]] = []

        # Generic MCQ skeletons (agent can edit later)
        for i in range(mcq_count):
            qid = f"q{i+1}"
            questions.append(
                _make_mcq_question(
                    qid=qid,
                    prompt=f"[{topic_n}] Вопрос (MCQ) #{i+1}: сформулируй проверку понимания ключевой идеи.",
                    options=["Вариант A", "Вариант B", "Вариант C", "Вариант D"],
                    correct_index=0,
                    explanation="Краткое объяснение правильного ответа.",
                    tags=[topic_n, diff, "mcq"],
                )
            )

        for j in range(short_count):
            qid = f"q{mcq_count + j + 1}"
            questions.append(
                _make_short_question(
                    qid=qid,
                    prompt=f"[{topic_n}] Вопрос (short) #{j+1}: попроси объяснить концепцию или написать небольшой фрагмент кода.",
                    rubric="Оценка: упоминание ключевых пунктов, корректность, ясность.",
                    sample_answer="Пример ожидаемого ответа (1–3 предложения или код).",
                    tags=[topic_n, diff, "short"],
                )
            )

        quiz = {
            "quiz_id": quiz_id,
            "topic": topic_n,
            "difficulty": diff,
            "created_at": _utc_now_iso(),
            "questions": questions,
        }

        quizzes = _load_quizzes()
        quizzes.append(quiz)
        _save_quizzes(quizzes)

        return json.dumps(
            {"success": True, "quiz": quiz, "total_quizzes": len(quizzes)},
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        return json.dumps(
            {"success": False, "error": f"Failed to create quiz: {str(e)}"},
            ensure_ascii=False,
            indent=2,
        )


@tool
def list_quizzes(limit: int = 10) -> str:
    """List saved quizzes from JSON storage.

    Retrieves quizzes ordered by creation time (newest first).

    Args:
        limit: Maximum number of quizzes to return (default: 10, max: 50)

    Returns:
        JSON string with a list of quizzes (quiz_id, topic, difficulty, created_at, question_count).

    Example:
        list_quizzes(limit=5)
    """
    try:
        lim = _cap_int(limit, 1, 50)
        quizzes = _load_quizzes()

        quizzes_sorted = sorted(quizzes, key=lambda q: q.get("created_at", ""), reverse=True)

        out = []
        for q in quizzes_sorted[:lim]:
            out.append(
                {
                    "quiz_id": q.get("quiz_id"),
                    "topic": q.get("topic"),
                    "difficulty": q.get("difficulty"),
                    "created_at": q.get("created_at"),
                    "question_count": len(q.get("questions", []) or []),
                }
            )

        return json.dumps(
            {"success": True, "limit": lim, "total_quizzes": len(quizzes), "quizzes": out},
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps(
            {"success": False, "error": f"Failed to list quizzes: {str(e)}"},
            ensure_ascii=False,
            indent=2,
        )


@tool
def load_quiz(quiz_id: str) -> str:
    """Load a quiz by quiz_id from JSON storage.

    Args:
        quiz_id: Quiz identifier returned by create_quiz
        Returns:
        JSON string with the quiz object (including questions) or an error.

    Example:
        load_quiz("a1b2c3...")
    """
    try:
        if not isinstance(quiz_id, str) or not quiz_id.strip():
            raise ValueError("quiz_id must be a non-empty string")

        quizzes = _load_quizzes()
        for q in quizzes:
            if q.get("quiz_id") == quiz_id.strip():
                return json.dumps({"success": True, "quiz": q}, ensure_ascii=False, indent=2)

        return json.dumps(
            {"success": False, "error": "Quiz not found"},
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps(
            {"success": False, "error": f"Failed to load quiz: {str(e)}"},
            ensure_ascii=False,
            indent=2,
        )


@tool
def grade_quiz(quiz_id: str, answers_json: str) -> str:
    """Grade a quiz attempt.

    Expected answers format (JSON string):
      {
        "q1": 2,
        "q2": 0,
        "q3": "your free-form answer",
        ...
      }

    Scoring:
    - MCQ: exact match with correct option index => +1
    - Short: heuristic check (keyword-based) is NOT reliable here without LLM;
      so we mark short answers as "needs_review" and do not auto-score them.

    Args:
        quiz_id: Quiz identifier
        answers_json: JSON string mapping question_id -> answer

    Returns:
        JSON string with:
        - auto_score (MCQ-only),
        - max_auto_score,
        - per-question results,
        - list of short answers that need manual/LLM review.

    Example:
        grade_quiz("a1b2...", "{\"q1\": 1, \"q2\": \"explain...\"}")
    """
    try:
        if not isinstance(quiz_id, str) or not quiz_id.strip():
            raise ValueError("quiz_id must be a non-empty string")
        if not isinstance(answers_json, str) or not answers_json.strip():
            raise ValueError("answers_json must be a non-empty JSON string")

        answers = json.loads(answers_json)
        if not isinstance(answers, dict):
            raise ValueError("answers_json must decode to an object/dict")

        quizzes = _load_quizzes()
        quiz = next((q for q in quizzes if q.get("quiz_id") == quiz_id.strip()), None)
        if not quiz:
            return json.dumps({"success": False, "error": "Quiz not found"}, ensure_ascii=False, indent=2)

        results = []
        auto_score = 0
        max_auto = 0
        needs_review = []

        for q in (quiz.get("questions") or []):
            qid = q.get("id")
            qtype = q.get("type")
            user_ans = answers.get(qid)

            if qtype == "mcq":
                max_auto += 1
                correct = q.get("answer")
                ok = (user_ans == correct)
                if ok:
                    auto_score += 1
                results.append(
                    {
                        "id": qid,
                        "type": qtype,
                        "user_answer": user_ans,
                        "correct_answer": correct,
                        "is_correct": ok,
                        "explanation": q.get("explanation", ""),
                    }
                )
            elif qtype == "short":
                needs_review.append({"id": qid, "user_answer": user_ans, "rubric": q.get("rubric", "")})
                results.append(
                    {
                        "id": qid,
                        "type": qtype,
                        "user_answer": user_ans,
                        "status": "needs_review",
                        "rubric": q.get("rubric", ""),
                        "sample_answer": q.get("sample_answer", ""),
                    }
                )
            else:
                results.append({"id": qid, "type": qtype, "status": "unknown_question_type"})
                return json.dumps(
            {
                "success": True,
                "quiz_id": quiz_id.strip(),
                "auto_score": auto_score,
                "max_auto_score": max_auto,
                "results": results,
                "short_answers_needing_review": needs_review,
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        return json.dumps(
            {"success": False, "error": f"Failed to grade quiz: {str(e)}"},
            ensure_ascii=False,
            indent=2,
        )