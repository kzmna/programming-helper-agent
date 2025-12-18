"""Architecture Agent implementation."""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate
import os

from tools.base_tools import (
    save_note,
    search_notes,
)

from tools.transfer_tools import (
    transfer_to_helper,
    complete_and_respond,
    ask_user_for_input,
)


def load_system_prompt() -> str:
    """Load system prompt from file."""
    prompt_path = os.path.join("prompts", "architecture_agent_prompt.md")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def create_architecture_agent(llm: ChatOpenAI, checkpointer):
    """Create the Architecture Agent with its tools.

    Args:
        llm: Language model instance
        checkpointer: Checkpointer for memory

    Returns:
        Configured ReAct agent
    """
    tools = [
        # memory tools are most useful here
        search_notes,
        save_note,
        # handoff / interaction tools
        transfer_to_helper,
        complete_and_respond,
        ask_user_for_input,
    ]

    system_prompt = load_system_prompt()

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("placeholder", "{messages}"),
    ])

    return create_react_agent(
        model=llm,
        tools=tools,
        checkpointer=checkpointer,
        state_modifier=prompt,
    )