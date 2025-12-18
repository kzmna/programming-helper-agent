from future import annotations

from typing import Any, Dict, List, Optional, TypedDict, Literal


AgentTarget = Literal["router", "code_helper", "architect", "quiz", "end"]


class Handoff(TypedDict, total=False):
    """
    Standard handoff contract passed between agents via tools.

    Expected shape (recommended):
      {
        "handoff": {
            "target": "code_helper" | "architect" | "quiz",
            "context": "...",
            "reason": "..."
        }
      }
    """
    target: AgentTarget
    context: str
    reason: str


class State(TypedDict, total=False):
    """
    LangGraph State for multi-agent programming assistant.

    IMPORTANT: create_react_agent expects 'messages' in state.
    """
    # Chat history (LangChain message objects)
    messages: List[Any]

    # Latest handoff data (if any)
    handoff: Optional[Handoff]

    # Final output for outer app (optional)
    final_answer: Optional[str]

    # Optional meta
    route: Optional[str]