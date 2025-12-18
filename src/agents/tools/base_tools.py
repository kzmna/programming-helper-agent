"""
Tools for a Multi-Agent Programming Assistant.

These tools are designed for:
- simple safe calculations,
- reading/writing files strictly inside workspace/,
- lightweight long-term memory stored in JSON (memory/notes.json),
- searching notes,
- running a basic linter check for Python files.

All tools return JSON strings for consistent downstream parsing/logging.
"""

from future import annotations

from langchain_core.tools import tool

import ast
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ----------------------------
# Paths / configuration
# ----------------------------

def _project_root() -> Path:
    # tools.py is expected in src/
    return Path(file).resolve().parent.parent


def _workspace_dir() -> Path:
    root = _project_root()
    ws = os.getenv("WORKSPACE_DIR", "workspace")
    return (root / ws).resolve()


def _memory_path() -> Path:
    root = _project_root()
    mem = os.getenv("MEMORY_PATH", "memory/notes.json")
    return (root / mem).resolve()


def _safe_path_under(base: Path, user_path: str) -> Path:
    """
    Build a safe resolved path under base. Prevents absolute paths and traversal (..).
    """
    if not isinstance(user_path, str) or not user_path.strip():
        raise ValueError("path must be a non-empty string")

    p = Path(user_path)

    if p.is_absolute():
        raise ValueError("absolute paths are not allowed")

    candidate = (base / p).resolve()

    try:
        candidate.relative_to(base)
    except ValueError as e:
        raise ValueError("path traversal detected (must stay inside workspace)") from e

    return candidate


# ----------------------------
# calc (safe arithmetic)
# ----------------------------

_ALLOWED_BINOPS = {
    ast.Add: (lambda a, b: a + b),
    ast.Sub: (lambda a, b: a - b),
    ast.Mult: (lambda a, b: a * b),
    ast.Div: (lambda a, b: a / b),
    ast.FloorDiv: (lambda a, b: a // b),
    ast.Mod: (lambda a, b: a % b),
    ast.Pow: (lambda a, b: a ** b),
}

_ALLOWED_UNARYOPS = {
    ast.UAdd: (lambda a: +a),
    ast.USub: (lambda a: -a),
}


def _safe_eval_arithmetic(expression: str) -> float | int:
    tree = ast.parse(expression, mode="eval")

    def _eval(node: ast.AST) -> float | int:
        if isinstance(node, ast.Expression):
            return _eval(node.body)

        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value

        # compatibility with older AST forms
        if isinstance(node, ast.Num) and isinstance(node.n, (int, float)):
            return node.n

        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
            left = _eval(node.left)
            right = _eval(node.right)
            return _ALLOWED_BINOPS[type(node.op)](left, right)

        if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
            val = _eval(node.operand)
            return _ALLOWED_UNARYOPS[type(node.op)](val)

        raise ValueError("expression contains unsupported operations")

    return _eval(tree)


@tool
def calc(expression: str) -> str:
    """Safely evaluate a simple arithmetic expression.

    This tool supports only basic arithmetic operations:
    +, -, *, /, //, %, , parentheses, and unary +/-. It blocks any other
    Python syntax to avoid unsafe execution (no names, calls, imports, etc.).

    Args:
        expression: Arithmetic expression string (e.g., "2*(3+4) - 5**2")

    Returns:
        JSON string with the computed result or an error.

    Example:
        calc("10 / 4")
    """
    try:
        if not isinstance(expression, str) or not expression.strip():
            raise ValueError("expression must be a non-empty string")

        expr = expression.strip()
        result = _safe_eval_arithmetic(expr)
        return json.dumps(
            {"success": True, "expression": expr, "result": result},
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps(
            {"success": False, "error": f"Failed to calculate: {str(e)}"},
            ensure_ascii=False,
            indent=2,
        )


# ----------------------------
# workspace file tools
# ----------------------------

@tool
def read_file(path: str) -> str:
    """Read a text file from workspace/.

    This tool is restricted to the workspace directory to keep file operations safe.
    Absolute paths and path traversal (../) are blocked.

    Args:
        path: Relative file path inside workspace/ (e.g., "main.py", "src/utils.py")

    Returns:
        JSON string with file content (utf-8) or an error.

    Example:
        read_file("scratch/test.py")
    """
    try:
        base = _workspace_dir()
        base.mkdir(parents=True, exist_ok=True)

        target = _safe_path_under(base, path)

        if not target.exists():
            raise FileNotFoundError(f"file not found: {path}")
        if not target.is_file():
            raise ValueError(f"not a file: {path}")

        content = target.read_text(encoding="utf-8")

        return json.dumps(
            {
                "success": True,
                "path": str(Path(path)),
                "bytes": len(content.encode("utf-8")),
                "content": content,
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps(
            {"success": False, "error": f"Failed to read file: {str(e)}"},
            ensure_ascii=False,
            indent=2,
        )


@tool
def write_file(path: str, content: str) -> str:
    """Write a text file into workspace/.

    This tool is restricted to the workspace directory to keep file operations safe.
    It will create parent directories if needed. Absolute paths and path traversal (../)
    are blocked.

    Args:
        path: Relative file path inside workspace/ (e.g., "scratch/out.txt")
        content: Text to write (utf-8)

    Returns:
        JSON string with confirmation metadata or an error.

    Example:
        write_file("scratch/hello.py", "print('hello')")
    """
    try:
        base = _workspace_dir()
        base.mkdir(parents=True, exist_ok=True)

        target = _safe_path_under(base, path)
        target.parent.mkdir(parents=True, exist_ok=True)

        if content is None:
            content = ""

        target.write_text(str(content), encoding="utf-8")

        return json.dumps(
            {
                "success": True,
                "path": str(Path(path)),
                "written_bytes": len(str(content).encode("utf-8")),
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps(
            {"success": False, "error": f"Failed to write file: {str(e)}"},
            ensure_ascii=False,
            indent=2,
        )


# ----------------------------
# memory tools (memory/notes.json)
# ----------------------------

def _load_notes() -> List[Dict[str, Any]]:
    mem_path = _memory_path()
    mem_path.parent.mkdir(parents=True, exist_ok=True)

    if not mem_path.exists():
        return []

    raw = mem_path.read_text(encoding="utf-8").strip()
    if not raw:
        return []

    data = json.loads(raw)

    # normalize to list[dict]
    if isinstance(data, list):
        out: List[Dict[str, Any]] = []
        for item in data:
            if isinstance(item, dict):
                out.append(item)
            elif isinstance(item, str):
                out.append({"text": item})
        return out

    if isinstance(data, dict):
        return [data]

    if isinstance(data, str):
        return [{"text": data}]

    return []
def _save_notes(notes: List[Dict[str, Any]]) -> None:
    mem_path = _memory_path()
    mem_path.parent.mkdir(parents=True, exist_ok=True)
    mem_path.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@tool
def save_note(text: str) -> str:
    """Save a note into long-term memory (memory/notes.json).

    Notes are stored as a list of JSON objects. Each note contains:
    - text: the note body
    - ts: UTC timestamp in ISO format

    Args:
        text: The note to save (e.g., "Bug fix: handle None in parse_config()")

    Returns:
        JSON string with confirmation and note metadata.

    Example:
        save_note("Remember: use TypedDict for State in LangGraph")
    """
    try:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be a non-empty string")

        notes = _load_notes()

        note = {"text": text.strip(), "ts": _utc_now_iso()}
        notes.append(note)

        _save_notes(notes)

        return json.dumps(
            {"success": True, "saved": True, "note": note, "total_notes": len(notes)},
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps(
            {"success": False, "error": f"Failed to save note: {str(e)}"},
            ensure_ascii=False,
            indent=2,
        )


@tool
def search_notes(query: str, limit: int = 10) -> str:
    """Search notes in memory/notes.json by substring match (case-insensitive).

    This is a lightweight memory retrieval tool (mini-RAG over notes).
    It returns the most recent matches up to the specified limit.

    Args:
        query: Search query (substring match)
        limit: Maximum number of results to return (default: 10, max: 50)

    Returns:
        JSON string with matching notes and basic stats.

    Example:
        search_notes("langgraph", limit=5)
    """
    try:
        if not isinstance(query, str) or not query.strip():
            return json.dumps(
                {"success": True, "query": query, "total_matches": 0, "matches": []},
                ensure_ascii=False,
                indent=2,
            )

        limit = max(1, min(int(limit), 50))
        q = query.strip().lower()

        notes = _load_notes()
        # newest first if ts exists
        notes_sorted = sorted(
            notes,
            key=lambda n: n.get("ts", ""),
            reverse=True,
        )

        matches: List[Dict[str, Any]] = []
        for n in notes_sorted:
            text = str(n.get("text", ""))
            if q in text.lower():
                matches.append(n)
            if len(matches) >= limit:
                break

        return json.dumps(
            {
                "success": True,
                "query": query,
                "limit": limit,
                "total_notes": len(notes),
                "total_matches": len(matches),
                "matches": matches,
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps(
            {"success": False, "error": f"Failed to search notes: {str(e)}"},
            ensure_ascii=False,
            indent=2,
        )


# ----------------------------
# linter (basic python checks)
# ----------------------------

def _lint_python_source(source: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Minimal linter:
    - syntax check (ast.parse)
    - simple style warnings:
      * trailing whitespace
      * tab indentation
      * lines > 120 chars
      * TODO/FIXME markers

    Returns: (ok, issues)
    """
    issues: List[Dict[str, Any]] = []
# 1) Syntax
    try:
        ast.parse(source)
    except SyntaxError as e:
        issues.append(
            {
                "type": "syntax_error",
                "line": e.lineno,
                "col": e.offset,
                "message": e.msg,
            }
        )
        # if syntax error, still continue to gather basic line warnings

    lines = source.splitlines()

    # 2) Simple style checks
    for i, line in enumerate(lines, start=1):
        if line.rstrip("\n\r") != line.rstrip("\n\r").rstrip(" \t"):
            issues.append(
                {"type": "style", "line": i, "message": "Trailing whitespace"}
            )

        if "\t" in line:
            issues.append(
                {"type": "style", "line": i, "message": "Tab character found (prefer spaces)"}
            )

        if len(line) > 120:
            issues.append(
                {"type": "style", "line": i, "message": f"Line too long ({len(line)} > 120)"}
            )

        if "TODO" in line or "FIXME" in line:
            issues.append({"type": "note", "line": i, "message": "Contains TODO/FIXME"})

    ok = not any(it["type"] == "syntax_error" for it in issues)
    return ok, issues


@tool
def linter(path: str) -> str:
    """Run a basic linter for a Python file inside workspace/.

    This tool is designed to be lightweight and dependency-free:
    - checks Python syntax via ast.parse
    - reports simple style warnings (trailing whitespace, tabs, long lines, TODO/FIXME)

    It is intentionally minimal so it works in restricted environments and fits
    the lab requirements for "tool calling" without relying on external binaries.

    Args:
        path: Relative path to a .py file inside workspace/ (e.g., "scratch/app.py")

    Returns:
        JSON string containing lint results (ok + issues) or an error.

    Example:
        linter("scratch/test.py")
    """
    try:
        base = _workspace_dir()
        base.mkdir(parents=True, exist_ok=True)

        target = _safe_path_under(base, path)

        if not target.exists():
            raise FileNotFoundError(f"file not found: {path}")
        if not target.is_file():
            raise ValueError(f"not a file: {path}")
        if target.suffix.lower() != ".py":
            raise ValueError("linter supports only .py files")

        source = target.read_text(encoding="utf-8")

        ok, issues = _lint_python_source(source)

        return json.dumps(
            {
                "success": True,
                "path": str(Path(path)),
                "ok": ok,
                "issue_count": len(issues),
                "issues": issues[:200],  # safety cap
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps(
            {"success": False, "error": f"Failed to lint file: {str(e)}"},
            ensure_ascii=False,
            indent=2,
        )