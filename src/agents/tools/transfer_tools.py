"""
Workflow / handoff tools for the multi-agent programming assistant.

These tools control the LangGraph flow:
- transfer_to_helper / transfer_to_architecture / transfer_to_quiz_agent
  -> create a structured "handoff" object for routing
- complete_and_respond
  -> ends the workflow by setting final_answer
- ask_user_for_input
  -> ends the current run and asks the user for missing details

IMPORTANT:
- All tools return JSON strings (consistent with the style of base_tools.py).
- graph.py extracts these JSON payloads from ToolMessage.content and routes accordingly.
"""

# from future import annotations

from langchain_core.tools import tool
import json
from typing import Dict, Any, Optional


def _ok(payload: Dict[str, Any]) -> str:
    return json.dumps({"success": True, **payload}, ensure_ascii=False, indent=2)


def _err(message: str) -> str:
    return json.dumps({"success": False, "error": message}, ensure_ascii=False, indent=2)


@tool
def transfer_to_helper(context: str, reason: str) -> str:
    """Transfer control to the Code Helper Agent (structured handoff).

    Use this when the user needs:
    - debugging, fixing errors, implementing code
    - refactoring, optimization, code explanation
    - working with files, running linter, etc.

    Args:
        context: Brief context about current state and what has been done
        reason: Why you're transferring and what the Code Helper Agent should do

    Returns:
        JSON string containing a "handoff" object with target="code_helper".

    Example:
        transfer_to_helper(
            context="Architecture is defined for a log parser",
            reason="Implement module structure and core parsing functions"
        )
    """
    try:
        if not context or not reason:
            raise ValueError("context and reason must be non-empty strings")

        return _ok({
            "handoff": {
                "target": "code_helper",
                "context": context,
                "reason": reason
            }
        })
    except Exception as e:
        return _err(f"Failed to transfer to helper: {str(e)}")


@tool
def transfer_to_architecture(context: str, reason: str) -> str:
    """Transfer control to the Architecture Agent (structured handoff).

    Use this when the user needs:
    - system/module architecture
    - decomposition, responsibilities, interfaces
    - design patterns and high-level plan

    Args:
        context: Brief context about current state and what's been done
        reason: Why you're transferring and what the Architecture Agent should do

    Returns:
        JSON string containing a "handoff" object with target="architect".

    Example:
        transfer_to_architecture(
            context="Need to implement a notes app",
            reason="Propose architecture, modules, and API endpoints"
        )
    """
    try:
        if not context or not reason:
            raise ValueError("context and reason must be non-empty strings")

        return _ok({
            "handoff": {
                "target": "architect",
                "context": context,
                "reason": reason
            }
        })
    except Exception as e:
        return _err(f"Failed to transfer to architecture: {str(e)}")


@tool
def transfer_to_quiz_agent(context: str, reason: str) -> str:
    """Transfer control to the Quiz Agent (structured handoff).

    Use this when the user wants:
    - a quiz on a programming topic
    - practice questions
    - grading their quiz attempt

    Args:
        context: Brief context about current state and what's been done
        reason: Why you're transferring and what the Quiz Agent should do

    Returns:
        JSON string containing a "handoff" object with target="quiz".

    Example:
        transfer_to_quiz_agent(
            context="User wants to practice Python",
            reason="Create a 10-question quiz on Python decorators"
        )
    """
    try:
        if not context or not reason:
            raise ValueError("context and reason must be non-empty strings")
        return _ok({
            "handoff": {
                "target": "quiz",
                "context": context,
                "reason": reason
            }
        })
    except Exception as e:
        return _err(f"Failed to transfer to quiz agent: {str(e)}")


@tool
def complete_and_respond(final_answer: str) -> str:
    """Complete the workflow and return final answer to the user.

    Use this when the current agent has finished the task and no further handoff is needed.

    Args:
        final_answer: Final response text to present to the user

    Returns:
        JSON string containing "final_answer", which graph.py uses as a stop condition.

    Example:
        complete_and_respond("Готово: я исправил ошибку и добавил тесты.")
    """
    try:
        if not isinstance(final_answer, str) or not final_answer.strip():
            raise ValueError("final_answer must be a non-empty string")

        return _ok({"final_answer": final_answer.strip()})
    except Exception as e:
        return _err(f"Failed to complete workflow: {str(e)}")


@tool
def ask_user_for_input(question: str, hints: Optional[str] = None) -> str:
    """Ask the user for missing info and stop the current workflow run.

    Use this if:
    - the user request is ambiguous
    - required details are missing (language, constraints, file paths, expected output)

    Args:
        question: The question to ask the user
        hints: Optional hints/examples to help the user answer

    Returns:
        JSON string containing an "ask_user" object.

    Example:
        ask_user_for_input(
            "Какой язык программирования используем?",
            hints="Например: Python / Java / C++"
        )
    """
    try:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must be a non-empty string")

        payload: Dict[str, Any] = {"question": question.strip()}
        if hints and isinstance(hints, str) and hints.strip():
            payload["hints"] = hints.strip()

        return _ok({"ask_user": payload})
    except Exception as e:
        return _err(f"Failed to ask user for input: {str(e)}")