"""
Main application entry point for the multi-agent programming assistant system.

This file mirrors the structure of the provided example:
- Initializes logging
- Creates the multi-agent LangGraph system
- Runs interactive CLI with thread continuity
- Supports sync and async invocation

Assumptions for your project:
- create_system() is defined in src/graph.py and returns a compiled graph
- Config is defined in config.py with MAX_RECURSION_LIMIT
- logger_config.py defines setup_logging(...) and log_system(...)
"""

import asyncio
import uuid
from typing import Optional, Tuple

from langchain_core.messages import HumanMessage, AIMessage

from src.graph import create_system
from config import Config
from logger_config import setup_logging, log_system


class ProgrammingAssistantSystem:
    """Main system class for the multi-agent programming assistant."""

    def init(self, enable_logging: bool = True, log_level: str = "INFO"):
        """Initialize the system.

        Args:
            enable_logging: Whether to enable comprehensive logging
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        print("Initializing Programming Assistant System...")

        # Setup logging
        if enable_logging:
            log_file = setup_logging(log_level=log_level)
            print(f"📝 Logging enabled: {log_file}")
            log_system("=" * 80)
            log_system("🚀 Starting Multi-Agent Programming Assistant System")
            log_system("=" * 80)

        # Create multi-agent system
        print("Creating multi-agent system...")
        log_system("🤖 Creating multi-agent system...")
        self.graph = create_system()
        log_system("✅ Multi-agent system ready")

        print("System ready!\n")

    def _extract_final_ai_response(self, result: dict) -> str:
        """
        Extract the final user-facing AI response from graph result.
        Preference:
        1) If your transfer_tools.complete_and_respond returns {"final_answer": "..."} into state, use that.
        2) Otherwise find the latest AIMessage that is not a tool-call message.
        """
        # 1) Structured final answer if present in state
        final_answer = result.get("final_answer")
        if isinstance(final_answer, str) and final_answer.strip():
            return final_answer.strip()

        # 2) Fallback to last AI message without tool calls
        response = ""
        for message in reversed(result.get("messages", [])):
            if isinstance(message, AIMessage) and not getattr(message, "tool_calls", None):
                response = message.content
                break

        return response

    def run_conversation(self, user_input: str, thread_id: Optional[str] = None) -> Tuple[str, str]:
        """Run a single conversation turn.

        Args:
            user_input: User's message
            thread_id: Thread ID for conversation continuity (creates new if None)

        Returns:
            Tuple of (response, thread_id)
        """
        if thread_id is None:
            thread_id = str(uuid.uuid4())
            log_system(f"📝 New conversation started: thread_id={thread_id}")
        else:
            log_system(f"📝 Continuing conversation: thread_id={thread_id}")

        log_system(f"💬 User input: {user_input[:200]}")

        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": Config.MAX_RECURSION_LIMIT,
        }

        # Invoke the graph
        log_system("🔄 Invoking multi-agent graph...")
        result = self.graph.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
        )

        response = self._extract_final_ai_response(result)

        log_system(f"✅ Response generated ({len(response)} chars)")
        log_system(f"📊 Total messages in thread: {len(result.get('messages', []))}")

        return response, thread_id

    async def run_conversation_async(self, user_input: str, thread_id: Optional[str] = None) -> Tuple[str, str]:
        """Async version of run_conversation.
        Args:
            user_input: User's message
            thread_id: Thread ID for conversation continuity (creates new if None)

        Returns:
            Tuple of (response, thread_id)
        """
        if thread_id is None:
            thread_id = str(uuid.uuid4())

        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": Config.MAX_RECURSION_LIMIT,
        }

        result = await self.graph.ainvoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
        )

        response = self._extract_final_ai_response(result)
        return response, thread_id

    def run_interactive(self):
        """Run an interactive CLI session."""
        print("=" * 70)
        print("Multi-Agent Programming Assistant - Interactive Mode")
        print("=" * 70)
        print("\nThis system has agents that can help you:")
        print("  • Router Agent: Understand request and route to the right agent")
        print("  • Code Helper Agent: Debug, write, refactor, lint, and work with files")
        print("  • Architecture Agent: Design structure, modules, and patterns")
        print("  • Quiz Agent: Create quizzes on programming topics and grade attempts")
        print("\nThe agents will collaborate and hand off tasks to each other as needed.")
        print("\nCommands:")
        print("  - Type 'quit' or 'exit' to end the session")
        print("  - Type 'new' to start a new conversation")
        print("  - Just type your message to continue the conversation")
        print("=" * 70)
        print()

        thread_id = None

        while True:
            try:
                user_input = input("\n🧑 You: ").strip()
                if not user_input:
                    continue

                if user_input.lower() in ["quit", "exit"]:
                    print("\nGoodbye! 👋")
                    break

                if user_input.lower() == "new":
                    thread_id = None
                    print("\n✨ Started new conversation")
                    continue

                print("\n🤖 Agent: ", end="", flush=True)
                response, thread_id = self.run_conversation(user_input, thread_id)
                print(response)

            except KeyboardInterrupt:
                print("\n\nInterrupted. Type 'quit' to exit or continue chatting.")
            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("The conversation will continue. Try rephrasing your request.")


def main():
    """Main entry point."""
    try:
        system = ProgrammingAssistantSystem()
        system.run_interactive()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        print("\nPlease check your configuration:")
        print("  1. Ensure .env file exists with proper settings")
        print("  2. Verify vLLM server is running and accessible")
        print("  3. Check that MODEL_NAME is set correctly")
        return 1

    return 0


if name == "main":
    raise SystemExit(main())