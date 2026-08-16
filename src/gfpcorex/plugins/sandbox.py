"""
Plugin Sandbox and Security Validator for GFP CoreX.
Enforces static AST inspection and restricted execution environments for user plugins.
"""

import ast
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("gfpcorex.sandbox")

# Default set of forbidden modules that plugins should not import
FORBIDDEN_MODULES: Set[str] = {
    "os",
    "sys",
    "subprocess",
    "shutil",
    "socket",
    "ctypes",
    "threading",
    "multiprocessing",
    "pickle",
    "importlib",
    "builtins",
}

# Default set of forbidden builtin function calls
FORBIDDEN_BUILTINS: Set[str] = {
    "eval",
    "exec",
    "open",
    "__import__",
    "compile",
    "breakpoint",
    "input",
    "globals",
    "locals",
    "vars",
    "getattr",
    "setattr",
    "delattr",
}

# Names that must never be *referenced* at all — not merely called. This blocks
# indirection tricks such as aliasing (``e = eval``) or reaching the real
# interpreter builtins through ``__builtins__["eval"]``.
FORBIDDEN_NAMES: Set[str] = FORBIDDEN_BUILTINS | {
    "__builtins__",
    "__loader__",
    "__spec__",
}

# Safe builtins allowed in plugin execution scope
SAFE_BUILTINS: Dict[str, Any] = {
    "abs": abs,
    "all": all,
    "any": any,
    "bin": bin,
    "bool": bool,
    "bytes": bytes,
    "callable": callable,
    "chr": chr,
    "dict": dict,
    "divmod": divmod,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "format": format,
    "frozenset": frozenset,
    "hash": hash,
    "hex": hex,
    "id": id,
    "int": int,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "iter": iter,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "next": next,
    "oct": oct,
    "ord": ord,
    "pow": pow,
    "print": print,
    "range": range,
    "repr": repr,
    "reversed": reversed,
    "round": round,
    "set": set,
    "slice": slice,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "type": type,
    "zip": zip,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "Exception": Exception,
    "KeyError": KeyError,
    "AttributeError": AttributeError,
    "IndexError": IndexError,
}


class SecurityValidationError(ValueError):
    """Raised when a plugin fails security AST analysis."""
    pass


class PluginSecurityChecker(ast.NodeVisitor):
    """AST Inspector that detects unauthorized module imports and forbidden function calls."""

    def __init__(self, allowed_modules: Optional[Set[str]] = None):
        self.forbidden_modules = FORBIDDEN_MODULES
        self.forbidden_builtins = FORBIDDEN_BUILTINS
        self.forbidden_names = FORBIDDEN_NAMES
        self.errors: List[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            module_base = alias.name.split('.')[0]
            if module_base in self.forbidden_modules:
                self.errors.append(
                    f"Line {node.lineno}: Importing restricted module '{alias.name}' is not allowed."
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            module_base = node.module.split('.')[0]
            if module_base in self.forbidden_modules:
                self.errors.append(
                    f"Line {node.lineno}: Importing from restricted module '{node.module}' is not allowed."
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id in self.forbidden_builtins:
                self.errors.append(
                    f"Line {node.lineno}: Calling restricted builtin function '{node.func.id}()' is prohibited."
                )
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        # Catches bare references and subscript access (e.g. ``__builtins__[...]``)
        # that visit_Call alone would miss.
        if node.id in self.forbidden_names:
            self.errors.append(
                f"Line {node.lineno}: Reference to restricted name '{node.id}' is not allowed."
            )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr.startswith("__") and node.attr.endswith("__") and node.attr not in {"__name__", "__doc__"}:
            self.errors.append(
                f"Line {node.lineno}: Access to dunder attribute '{node.attr}' is restricted."
            )
        self.generic_visit(node)


class PluginSandbox:
    """Plugin Sandbox manager providing static verification and safe execution globals."""

    @staticmethod
    def validate_code(code: str) -> Tuple[bool, List[str]]:
        """
        Statically inspect plugin source code using AST.

        Returns:
            Tuple[bool, List[str]]: (is_safe, list_of_security_violations)
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, [f"Syntax Error in plugin code: {e}"]

        checker = PluginSecurityChecker()
        checker.visit(tree)

        if checker.errors:
            return False, checker.errors
        return True, []

    @staticmethod
    def get_safe_globals() -> Dict[str, Any]:
        """Generate safe globals dict for plugin execution."""
        return {
            "__builtins__": SAFE_BUILTINS,
            "__name__": "__sandbox__",
            "__doc__": "Sandboxed plugin execution scope",
        }
