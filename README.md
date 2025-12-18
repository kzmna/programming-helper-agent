# Multi-Agent Programming Assistant
Система для помощи в программировании. Система помогает анализировать код, объяснять ошибки, предлагать исправлен. Маршрутизатор решает кому передатьуправление.

## System Overview
### Агенты
1) **Router Agent (маршрутизатор)**
- Классифицирует запрос: *код / архитектура / план / смешанный*.
- Решает, какому агенту передать управление.

2) **Code Helper Agent (помощник по коду)**
- Разбирает ошибки, предлагает исправления, пишет/рефакторит функции.
- При необходимости вызывает инструменты: линтер/простая проверка.

3) **Architecture Agent (проектировщик)**
 - Отвечает за проектирование архитектуры.
 - Предлагает структуру модулей, классов, API.
 - После проектирования передаёт управление Code Helper Agent для реализации

 ---
## Паттерн мультиагентной системы
Используемый паттерн:
- **Router + специализированные агенты**
- **Условный переход по графу (conditional routing)**
- **Handoff между агентами**
---
## Диаграмма работы системы
ТУТ ФОТКА

 ### Тулы 
 Агенты могут вызывать Python-инструменты:
- **calc(expression: str)** - простые вычисления.
- **read_file(path)** - чтение файлов из папки workspace/ .
- **write_file(path, content)** - запись файлов.
- **save_note(text)** - сохранение заметки в память.
- **search_notes(query)** - поиск по памяти.
- **transfer_to_helper** - передача Code Helper Agent
- **transfer_to_architecture** - передача rchitecture Agent

Инструменты вызываются только при необходимости и интегрированы через LangChain tools.

### Хранимые данные
- history — история диалога в рамках сессии.
- user_profile — предпочтения пользователя (язык, стек, стиль).
- notes — полезные заметки и решения

### Реализация
- Память хранится в memory/notes.json .
- Агенты могут добавлять и извлекать записи.
- Память влияет на последующие ответы.

## Quick Start

### 1. Зависимости
```bash
curl -sSL https://install.python-poetry.org | python3 -
poetry install
```
### 2. Конфигурация Env
```bash
cp example.env .env
```
Редактирование .env:
```ini
OPENAI_API_BASE=http://localhost:8000/v1
OPENAI_API_KEY=EMPTY
MODEL_NAME=qwen-7b
TEMPERATURE=0.3
MAX_TOKENS=2048
MAX_RECURSION_LIMIT=30
MEMORY_PATH=memory/notes.json
WORKSPACE_DIR=workspace
```
### 3. Запуск
Интерактивный режим
```bash
poetry run python demo_autonomous.py
```
Демонстрационные эксперименты
```bash
poetry run python main.py
```
---
## Примеры использования
### 1 — анализ ошибки
```python
from src.main import ProgrammingAssistantSystem
system = ProgrammingAssistantSystem()
answer, trace = system.run(
 "У меня возникает TypeError при вызове функции. Вот traceback..."
)
print(answer)
print(trace)
```
### 2 - архитектурный запрос
```python
User: Спроектируй архитектуру REST API для сервиса заметок.
System:
 Router → Architecture Agent → Code Helper Agent
```

## Структура проекта
```
programming_assistant/
├── src/
│ ├── main.py
│ ├── graph.py
│ ├── state.py
│ ├── agents/
│ │ ├── router.py
│ │ ├── code_helper.py
│ │ └── architect.py
│ └── tools.py
├── docs/
│ ├── architecture.md
│ └── reflection.md
├── memory/
│ └── notes.json
├── workspace/
├── demo_experiments.py
├── pyproject.toml
└── README.md
```






