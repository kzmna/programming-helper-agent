"""
Simple demonstration of autonomous multi-agent workflow (Programming Assistant).

This script demonstrates how the system collaborates autonomously from user queries.
It runs 5+ demo prompts to satisfy typical lab "experiments" requirements:
- programming/debugging
- architecture/design
- quiz/learning
- theory/meta about agents
- everyday planning / checklist-style request

It prints the final response for each experiment and keeps a single thread_id
to show conversation continuity. You can reset thread_id between experiments
if you want isolated runs.

Run:
  poetry run python demo_experiments.py
"""

from src.main import ProgrammingAssistantSystem

print("=" * 80)
print("🤖 Autonomous Multi-Agent Workflow Demo (Programming Assistant)")
print("=" * 80)
print("\nThis demonstrates how the system works from user input.")
print("The agents will automatically:")
print("  1. Route the request (Router Agent)")
print("  2. Solve implementation/debugging tasks (Code Helper Agent)")
print("  3. Design architectures when needed (Architecture Agent)")
print("  4. Create and grade quizzes (Quiz Agent)")
print("\nAll from user input!\n")
print("=" * 80)

# Initialize system
print("\nInitializing system...")
system = ProgrammingAssistantSystem(enable_logging=True, log_level="INFO")

print("\n" + "=" * 80)
print("🧪 Running Experiments")
print("=" * 80)

experiments = [
    {
        "title": "1) Programming / Debugging",
        "query": (
            "У меня ошибка: TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'. "
            "Объясни причину и предложи исправление на Python. Дай пример кода."
        ),
    },
    {
        "title": "2) Architecture / Design",
        "query": (
            "Спроектируй архитектуру простого парсера логов: "
            "нужны модули, классы/функции, формат входа/выхода, и как тестировать."
        ),
    },
    {
        "title": "3) Quiz Creation",
        "query": (
            "Сделай квиз на 7 вопросов по теме Python decorators. "
            "Сложность: medium. Смешай варианты и короткие ответы."
        ),
    },
    {
        "title": "4) Theory / Multi-agent explanation",
        "query": (
            "Кратко объясни, что такое multi-agent system и зачем нужен handoff между агентами. "
            "Приведи пример на задаче программирования."
        ),
    },
    {
        "title": "5) Theory / Multi-agent explanation",
        "query": (
            "Мне нужно составить мультиагента, который будет отвечать на вопросы про фигурное катание. Составь его архитектуру, приведи примеры агентов и их код."
        ),
    },
]

thread_id = None

for exp in experiments:
    print("\n" + "-" * 80)
    print(f"🧾 {exp['title']}")
    print("-" * 80)
    user_query = exp["query"]
    print(f"\n📝 User Query:\n'{user_query}'\n")
    print("🚀 Starting autonomous workflow...\n")

    response, thread_id = system.run_conversation(user_query, thread_id)

    print("\n✅ Response:\n")
    print(response)
    print(f"\n🔗 Thread ID: {thread_id}")

print("\n" + "=" * 80)
print("✅ Experiments Complete!")
print("=" * 80)
print("\n📁 Check these locations (if used during runs):")
print("   - Workspace files: workspace/")
print("   - Memory (notes/quizzes): memory/")
print("   - Logs: logs/")
print("\n💡 Tip: If you want each experiment isolated, set thread_id=None before each run.")