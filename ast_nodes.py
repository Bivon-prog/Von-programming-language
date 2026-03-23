"""AST node definitions for the Von language."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Any


@dataclass
class Number:
    value: float; line: int = 0

@dataclass
class String:
    value: str; line: int = 0

@dataclass
class Identifier:
    name: str; line: int = 0

@dataclass
class ListLiteral:
    elements: List[Any]; line: int = 0

@dataclass
class IndexAccess:
    obj: Any; index: Any; line: int = 0

@dataclass
class IndexAssign:
    name: str; index: Any; value: Any; line: int = 0

@dataclass
class BinaryOp:
    op: str; left: Any; right: Any; line: int = 0

@dataclass
class UnaryOp:
    op: str; operand: Any; line: int = 0

@dataclass
class Assignment:
    name: str; value: Any; line: int = 0

@dataclass
class FunctionCall:
    name: str; args: List[Any]; line: int = 0

@dataclass
class MethodCall:
    obj: Any; method: str; args: List[Any]; line: int = 0

@dataclass
class AttributeAccess:
    obj: Any; attr: str; line: int = 0

@dataclass
class AttributeAssign:
    obj: Any; attr: str; value: Any; line: int = 0

@dataclass
class ReturnStmt:
    value: Optional[Any]; line: int = 0

@dataclass
class BreakStmt:
    line: int = 0

@dataclass
class ContinueStmt:
    line: int = 0

@dataclass
class IfStmt:
    condition: Any
    then_block: List[Any]
    elif_clauses: List[Any]
    else_block: Optional[List[Any]]
    line: int = 0

@dataclass
class ElifClause:
    condition: Any; block: List[Any]; line: int = 0

@dataclass
class WhileStmt:
    condition: Any; block: List[Any]; line: int = 0

@dataclass
class ForStmt:
    var: str; iterable: Any; block: List[Any]; line: int = 0

@dataclass
class FuncDef:
    name: str; params: List[str]; block: List[Any]; line: int = 0

@dataclass
class ClassDef:
    name: str; block: List[Any]; line: int = 0

@dataclass
class Program:
    statements: List[Any]
