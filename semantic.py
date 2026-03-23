"""
Phase 3 — Semantic Analyser for the Von language.

Responsibilities:
  - Build a symbol table (scoped)
  - Detect use of undefined variables
  - Detect return statements outside functions
  - Detect break/continue outside loops
  - Warn on unused variables (non-fatal)
"""
from __future__ import annotations
from typing import List, Optional, Set
from ast_nodes import (
    Program, Assignment, Identifier, BinaryOp, UnaryOp,
    FunctionCall, MethodCall, ListLiteral, IndexAccess, IndexAssign,
    AttributeAccess, AttributeAssign,
    Number, String, ReturnStmt, BreakStmt, ContinueStmt,
    IfStmt, WhileStmt, ForStmt, FuncDef, ClassDef,
)


class SemanticError(Exception):
    def __init__(self, msg: str, line: int = 0):
        super().__init__(f"[SemanticError] Line {line}: {msg}")
        self.line = line


class SymbolTable:
    """Scoped symbol table — each scope is a dict layer."""

    def __init__(self, parent: Optional[SymbolTable] = None, name: str = "<global>"):
        self._symbols: dict = {}
        self._used:    Set[str] = set()
        self.parent = parent
        self.name   = name

    def declare(self, name: str, line: int = 0):
        self._symbols[name] = line

    def resolve(self, name: str) -> bool:
        if name in self._symbols:
            self._used.add(name)
            return True
        if self.parent:
            return self.parent.resolve(name)
        return False

    def mark_used(self, name: str):
        if name in self._symbols:
            self._used.add(name)
        elif self.parent:
            self.parent.mark_used(name)

    def unused(self) -> List[str]:
        return [n for n in self._symbols if n not in self._used]


# Built-ins are always in scope
BUILTIN_NAMES = {
    "output", "print", "input", "num", "str", "sqrt", "abs", "pow",
    "floor", "ceil", "round", "max", "min",
    "sin", "cos", "tan", "log", "log2", "log10", "exp",
    "range", "len", "sum", "sort", "append", "pop",
    "pi", "e", "tau", "true", "false", "nil",
}


class SemanticAnalyser:
    def __init__(self):
        self._scope:       SymbolTable = SymbolTable(name="<global>")
        self._in_function: int = 0   # nesting depth
        self._in_loop:     int = 0
        self.warnings:     List[str] = []

        # Pre-declare all built-ins in global scope
        for name in BUILTIN_NAMES:
            self._scope.declare(name)

    def analyse(self, program: Program):
        for stmt in program.statements:
            self._check(stmt)

    # ------------------------------------------------------------------ dispatch

    def _check(self, node):
        t = type(node)

        if t is Assignment:
            self._check_expr(node.value)
            self._scope.declare(node.name, node.line)
            return

        if t is AttributeAssign:
            self._check_expr(node.obj)
            self._check_expr(node.value)
            return

        if t is IndexAssign:
            if not self._scope.resolve(node.name):
                raise SemanticError(f"Undefined variable '{node.name}'", node.line)
            self._check_expr(node.index)
            self._check_expr(node.value)
            return

        if t is FuncDef:
            self._scope.declare(node.name, node.line)
            self._enter_function(node)
            return

        if t is ClassDef:
            self._scope.declare(node.name, node.line)
            self._enter_class(node)
            return

        if t is ReturnStmt:
            if self._in_function == 0:
                raise SemanticError("'return' outside function", node.line)
            if node.value is not None:
                self._check_expr(node.value)
            return

        if t is BreakStmt:
            if self._in_loop == 0:
                raise SemanticError("'break' outside loop", node.line)
            return

        if t is ContinueStmt:
            if self._in_loop == 0:
                raise SemanticError("'continue' outside loop", node.line)
            return

        if t is IfStmt:
            self._check_expr(node.condition)
            self._check_block(node.then_block)
            for cl in node.elif_clauses:
                self._check_expr(cl.condition)
                self._check_block(cl.block)
            if node.else_block:
                self._check_block(node.else_block)
            return

        if t is WhileStmt:
            self._check_expr(node.condition)
            self._in_loop += 1
            self._check_block(node.block)
            self._in_loop -= 1
            return

        if t is ForStmt:
            self._check_expr(node.iterable)
            self._in_loop += 1
            child = self._push_scope("<for>")
            child.declare(node.var, node.line)
            self._check_block(node.block, scope=child)
            self._pop_scope()
            self._in_loop -= 1
            return

        # Expression statement
        self._check_expr(node)

    def _check_expr(self, node):
        t = type(node)

        if t is Identifier:
            if not self._scope.resolve(node.name):
                raise SemanticError(f"Undefined variable '{node.name}'", node.line)
            return

        if t is BinaryOp:
            self._check_expr(node.left)
            self._check_expr(node.right)
            return

        if t is UnaryOp:
            self._check_expr(node.operand)
            return

        if t is FunctionCall:
            if not self._scope.resolve(node.name):
                raise SemanticError(f"Undefined function '{node.name}'", node.line)
            for a in node.args:
                self._check_expr(a)
            return

        if t is AttributeAccess:
            self._check_expr(node.obj)
            return

        if t is MethodCall:
            self._check_expr(node.obj)
            for a in node.args:
                self._check_expr(a)
            return

        if t is ListLiteral:
            for e in node.elements:
                self._check_expr(e)
            return

        if t is IndexAccess:
            self._check_expr(node.obj)
            self._check_expr(node.index)
            return

        if t in (Number, String):
            return

        # Fallback — treat as statement
        self._check(node)

    def _check_block(self, stmts, scope=None):
        if scope is None:
            scope = self._push_scope("<block>")
            for s in stmts:
                self._check(s)
            self._pop_scope()
        else:
            saved = self._scope
            self._scope = scope
            for s in stmts:
                self._check(s)
            self._scope = saved

    def _enter_function(self, node: FuncDef):
        child = self._push_scope(f"<func {node.name}>")
        for p in node.params:
            child.declare(p, node.line)
        self._in_function += 1
        for s in node.block:
            self._check(s)
        self._in_function -= 1
        # Warn on unused params
        for u in child.unused():
            if u in node.params:
                self.warnings.append(
                    f"[Warning] Parameter '{u}' in '{node.name}' is never used")
        self._pop_scope()

    def _enter_class(self, node: ClassDef):
        child = self._push_scope(f"<class {node.name}>")
        child.declare("self", node.line)
        for s in node.block:
            self._check(s)
        self._pop_scope()

    def _push_scope(self, name: str) -> SymbolTable:
        self._scope = SymbolTable(parent=self._scope, name=name)
        return self._scope

    def _pop_scope(self):
        self._scope = self._scope.parent
