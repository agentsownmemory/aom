"""A static check on an agent's runtime before it runs on someone's machine.

The runtime is code written by an AI agent. It only needs plain Python data
handling, so anything that reaches files, the network, processes or the
interpreter's internals is refused before a single line executes:
imports outside a small allowlist, builtins like open/exec/eval/getattr, and
any dunder name or attribute (the usual road to __subclasses__ and friends).
"""
from __future__ import annotations

import ast

ALLOWED_IMPORTS = {
    "abc", "collections", "contextlib", "copy", "dataclasses", "enum",
    "functools", "itertools", "json", "math", "re", "string", "typing",
}
FORBIDDEN_NAMES = {
    "open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars",
    "getattr", "setattr", "delattr", "input", "breakpoint", "memoryview",
    "help", "exit", "quit", "license", "copyright", "credits",
}


def _dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


def check(source: str) -> str | None:
    """Return why the runtime is refused, or None when it may run."""
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return f"does not parse: {e.msg} (line {e.lineno})"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] not in ALLOWED_IMPORTS:
                    return f"imports {a.name} (line {node.lineno})"
        elif isinstance(node, ast.ImportFrom):
            if node.level or (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
                return f"imports from {node.module or '.'} (line {node.lineno})"
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES or (_dunder(node.id) and node.id != "__name__"):
                return f"uses {node.id} (line {node.lineno})"
        elif isinstance(node, ast.Attribute) and _dunder(node.attr):
            return f"touches .{node.attr} (line {node.lineno})"
    if not any(isinstance(n, ast.ClassDef) and n.name == "Runtime" for n in tree.body):
        return "has no class Runtime"
    return None
