"""Router Agent implementation."""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate
import os

from .tools.transfer_tools import (
    transfer_to_helper,
    transfer_to_architecture,
    complete_and_respond,
    ask_user_for_input,
)


def load_system_prompt() -> str:
    """Load system prompt from file."""
    prompt_path = 'src/prompts/router_prompt.md'
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def create_router_agent(llm: ChatOpenAI, checkpointer):
    """Create the Router Agent with its tools.

    Args:
        llm: Language model instance
        checkpointer: Checkpointer for memory

    Returns:
        Configured ReAct agent
    """
    tools = [
        transfer_to_helper,
        transfer_to_architecture,
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

