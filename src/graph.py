# from future import annotations

import json
from typing import Any, Dict, Optional, Tuple

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import BaseMessage, ToolMessage
from langchain_openai import ChatOpenAI
from config import Config

from src.state import State

# ----------------------------
# Helpers: parse handoff / completion from tool outputs
# ----------------------------

def _try_parse_json(text: str) -> Optional[Dict[str, Any]]:
    text = (text or "").strip()
    if not text:
        return None
    if not (text.startswith("{") and text.endswith("}")):
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def _extract_control(messages: list) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[Dict[str, Any]]]:
    """
    Scan messages from the end and try to extract:
    - handoff dict ({"target": ..., "context": ..., "reason": ...})
    - final_answer string (if complete_and_respond stored it)
    - ask_user dict (if ask_user_for_input stored it)

    Supports both:
    - tool returns dict (some stacks keep dict-like content)
    - tool returns JSON string
    """
    handoff = None
    final_answer = None
    ask_user = None

    for m in reversed(messages or []):
        if not isinstance(m, ToolMessage):
            continue

        content = m.content

        # 1) dict-like content
        if isinstance(content, dict):
            data = content
        else:
            # 2) JSON string in content
            data = _try_parse_json(str(content))

        if not isinstance(data, dict):
            continue

        # Handoff contract
        if "handoff" in data and isinstance(data["handoff"], dict):
            handoff = data["handoff"]

        # Completion contract (recommended)
        if "final_answer" in data and isinstance(data["final_answer"], str):
            final_answer = data["final_answer"]

        # Ask user contract (optional)
        if "ask_user" in data and isinstance(data["ask_user"], dict):
            ask_user = data["ask_user"]

        # If we found something, we can stop early
        if handoff or final_answer or ask_user:
            break

    return handoff, final_answer, ask_user


def _route_from_state(state: State) -> str:
    """
    Decide next node after an agent run.

    Priority:
    1) If there's a parsed completion -> END
    2) If there's a handoff target -> route to that agent node
    3) Otherwise -> END
    """
    messages = state.get("messages", [])
    handoff, final_answer, ask_user = _extract_control(messages)
    print("DEBUG handoff =", handoff)

    if final_answer:
        return END

    if ask_user:
        # In most cases you stop the graph and wait for the user's next message
        return END

    if handoff and isinstance(handoff, dict):
        target = (handoff.get("target") or "").strip()
        if target in {"code_helper", "architect", "quiz", 'router'}:
            return target

    return END


def _merge_control_into_state(state: State) -> State:
    """
    After each agent invocation, extract handoff/final and put them into state fields
    for easier debugging and logging.
    """
    messages = state.get("messages", [])
    handoff, final_answer, ask_user = _extract_control(messages)

    if handoff:
        state["handoff"] = handoff  # type: ignore[assignment]

    if final_answer:
        state["final_answer"] = final_answer

    # If you want, you can also store ask_user in state:
    # if ask_user:
    #     state["ask_user"] = ask_user

    return state


# ----------------------------
# Graph builder
# ----------------------------

def build_graph(
    router_agent,
    code_helper_agent,
    architecture_agent,
    quiz_agent,
):
    """
    Build and compile the LangGraph multi-agent workflow.
Args:
        router_agent: ReAct agent created via create_router_agent(...)
        code_helper_agent: ReAct agent created via create_code_helper_agent(...)
        architecture_agent: ReAct agent created via create_architecture_agent(...)
        quiz_agent: ReAct agent created via create_quiz_agent(...)

    Returns:
        compiled LangGraph app
    """

    # checkpointer = MemorySaver()
    # llm = ChatOpenAI(
    #     base_url=Config.OPENAI_API_BASE,
    #     api_key=Config.OPENAI_API_KEY,
    #     model=Config.MODEL_NAME,
    #     temperature=Config.TEMPERATURE,
    #     max_tokens=Config.MAX_TOKENS,
    #     )

    graph = StateGraph(State)

    # --- Node wrappers (agents expect and return {"messages": [...]}) ---

    def router_node(state: State) -> State:
        # print("DEBUG router_agent =", router_agent, type(router_agent))
        out = router_agent.invoke(state)
        state.update(out)
        return _merge_control_into_state(state)

    def code_helper_node(state: State) -> State:
        out = code_helper_agent.invoke(state)
        state.update(out)
        return _merge_control_into_state(state)

    def architect_node(state: State) -> State:
        out = architecture_agent.invoke(state)
        state.update(out)
        return _merge_control_into_state(state)

    def quiz_node(state: State) -> State:
        out = quiz_agent.invoke(state)
        state.update(out)
        return _merge_control_into_state(state)

    # --- Register nodes ---
    graph.add_node("router", router_node)
    graph.add_node("code_helper", code_helper_node)
    graph.add_node("architect", architect_node)
    graph.add_node("quiz", quiz_node)

    # --- Entry point ---
    graph.set_entry_point("router")

    # --- Conditional routing after each agent ---
    # Router can route to helper / architect / quiz (or end)
    graph.add_conditional_edges(
        "router",
        _route_from_state,
        {
            "code_helper": "code_helper",
            "architect": "architect",
            "quiz": "quiz",
            END: END,
        },
    )

    # Helper may handoff to architect, or finish
    graph.add_conditional_edges(
        "code_helper",
        _route_from_state,
        {
            "architect": "architect",
            "quiz": "quiz",
            END: END,
        },
    )

    # Architect may handoff to helper, or finish
    graph.add_conditional_edges(
        "architect",
        _route_from_state,
        {
            "code_helper": "code_helper",
            "quiz": "quiz",
            END: END,
        },
    )

    # Quiz may handoff to helper/architect (explanations), or finish
    graph.add_conditional_edges(
        "quiz",
        _route_from_state,
        {
            "code_helper": "code_helper",
            "architect": "architect",
            END: END,
        },
    )

    return graph.compile(
        # checkpointer=checkpointer, llm=llm
        )