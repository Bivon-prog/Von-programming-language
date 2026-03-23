"""
Phase 4 — Bytecode Compiler for the Von language.

Walks the AST and emits a flat list of instructions for the Von VM.
Each instruction is an (Opcode, optional_arg) tuple.

Stack-based VM model:
  - All operations push/pop values on an operand stack.
  - Local variables live in a frame's local slot array.
  - Constants live in a per-chunk constant pool.
"""
from __future__ import annotations
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Any, Optional

from ast_nodes import (
    Program, Assignment, Identifier, BinaryOp, UnaryOp,
    FunctionCall, MethodCall, ListLiteral, IndexAccess, IndexAssign,
    AttributeAccess, AttributeAssign,
    Number, String, ReturnStmt, BreakStmt, ContinueStmt,
    IfStmt, WhileStmt, ForStmt, FuncDef, ClassDef,
)


# ------------------------------------------------------------------ Opcodes

class Op(Enum):
    # Stack
    LOAD_CONST   = auto()   # push constants[arg]
    LOAD_NAME    = auto()   # push value of name arg
    STORE_NAME   = auto()   # pop → store in name arg
    LOAD_INDEX   = auto()   # pop index, pop obj → push obj[index]
    STORE_INDEX  = auto()   # pop val, pop index, pop obj → obj[index]=val
    LOAD_ATTR    = auto()   # pop obj → push obj.attr  (arg = attr name)
    STORE_ATTR   = auto()   # pop val, pop obj → obj.attr = val  (arg = attr name)

    # Arithmetic / logic
    BINARY_OP    = auto()   # pop r, pop l → push l op r  (arg = op string)
    UNARY_OP     = auto()   # pop v → push op v            (arg = op string)

    # Function / method
    CALL         = auto()   # arg = (name, argc)
    CALL_METHOD  = auto()   # arg = (method, argc)
    RETURN       = auto()   # pop return value, return from frame
    RETURN_NONE  = auto()   # return nil

    # List
    BUILD_LIST   = auto()   # arg = n  → pop n items, push list

    # Control flow
    JUMP         = auto()   # unconditional jump to arg (index)
    JUMP_IF_FALSE= auto()   # pop, jump to arg if falsy (does NOT pop on true)
    POP          = auto()   # discard top of stack

    # Loop helpers
    GET_ITER     = auto()   # pop iterable → push iterator object
    FOR_ITER     = auto()   # peek iterator: if exhausted jump arg, else push next val
    STORE_ITER_VAR = auto() # arg = name  (store top of stack into loop var)

    # Class
    BUILD_CLASS  = auto()   # arg = (name, method_chunk_indices)

    # Misc
    HALT         = auto()


# ------------------------------------------------------------------ Instruction / Chunk

@dataclass
class Instruction:
    op:  Op
    arg: Any = None

    def __repr__(self):
        return f"{self.op.name:<18} {self.arg!r}" if self.arg is not None else self.op.name


@dataclass
class Chunk:
    """A compiled unit — either the top-level program or a function body."""
    name:         str
    instructions: List[Instruction] = field(default_factory=list)
    constants:    List[Any]         = field(default_factory=list)
    params:       List[str]         = field(default_factory=list)

    def emit(self, op: Op, arg=None) -> int:
        self.instructions.append(Instruction(op, arg))
        return len(self.instructions) - 1   # index of emitted instruction

    def add_const(self, value: Any) -> int:
        """Add a constant to the pool and return its index."""
        try:
            return self.constants.index(value)
        except ValueError:
            self.constants.append(value)
            return len(self.constants) - 1

    def patch(self, idx: int, new_arg: Any):
        """Back-patch a jump target once we know the destination."""
        self.instructions[idx].arg = new_arg

    def disassemble(self) -> str:
        lines = [f"=== Chunk: {self.name} ==="]
        if self.constants:
            lines.append(f"  constants: {self.constants}")
        if self.params:
            lines.append(f"  params:    {self.params}")
        lines.append("")
        for i, ins in enumerate(self.instructions):
            lines.append(f"  {i:04d}  {ins}")
        return "\n".join(lines)


# ------------------------------------------------------------------ Code Generator

class CodeGen:
    def __init__(self):
        self._chunks: List[Chunk] = []          # all compiled chunks
        self._chunk:  Chunk       = None         # current chunk being written
        self._break_patches:  List[List[int]] = []  # stack of break jump indices
        self._continue_patches: List[List[int]] = []

    def compile(self, program: Program) -> List[Chunk]:
        main = Chunk(name="<main>")
        self._chunks.append(main)
        self._chunk = main
        for stmt in program.statements:
            self._gen(stmt)
        self._chunk.emit(Op.HALT)
        return self._chunks

    # ---------------------------------------------------------------- dispatch

    def _gen(self, node):
        t = type(node)

        if t is Assignment:
            self._gen_expr(node.value)
            self._chunk.emit(Op.STORE_NAME, node.name)
            return

        if t is AttributeAssign:
            self._gen_expr(node.obj)
            self._gen_expr(node.value)
            self._chunk.emit(Op.STORE_ATTR, node.attr)
            return

        if t is IndexAssign:
            self._chunk.emit(Op.LOAD_NAME, node.name)
            self._gen_expr(node.index)
            self._gen_expr(node.value)
            self._chunk.emit(Op.STORE_INDEX)
            return

        if t is FuncDef:
            chunk = self._compile_function(node)
            idx   = self._chunks.index(chunk)
            ci    = self._chunk.add_const(("__func__", idx, node.params))
            self._chunk.emit(Op.LOAD_CONST, ci)
            self._chunk.emit(Op.STORE_NAME, node.name)
            return

        if t is ClassDef:
            method_indices = {}
            for s in node.block:
                if isinstance(s, FuncDef):
                    mc  = self._compile_function(s)
                    idx = self._chunks.index(mc)
                    method_indices[s.name] = idx
            ci = self._chunk.add_const(("__class__", node.name, method_indices))
            self._chunk.emit(Op.LOAD_CONST, ci)
            self._chunk.emit(Op.STORE_NAME, node.name)
            return

        if t is ReturnStmt:
            if node.value is not None:
                self._gen_expr(node.value)
                self._chunk.emit(Op.RETURN)
            else:
                self._chunk.emit(Op.RETURN_NONE)
            return

        if t is BreakStmt:
            idx = self._chunk.emit(Op.JUMP, None)   # patched later
            self._break_patches[-1].append(idx)
            return

        if t is ContinueStmt:
            idx = self._chunk.emit(Op.JUMP, None)
            self._continue_patches[-1].append(idx)
            return

        if t is IfStmt:
            self._gen_if(node); return

        if t is WhileStmt:
            self._gen_while(node); return

        if t is ForStmt:
            self._gen_for(node); return

        # Expression statement — evaluate and discard result
        self._gen_expr(node)
        self._chunk.emit(Op.POP)

    def _gen_expr(self, node):
        t = type(node)

        if t is Number:
            ci = self._chunk.add_const(node.value)
            self._chunk.emit(Op.LOAD_CONST, ci); return

        if t is String:
            ci = self._chunk.add_const(node.value)
            self._chunk.emit(Op.LOAD_CONST, ci); return

        if t is Identifier:
            self._chunk.emit(Op.LOAD_NAME, node.name); return

        if t is ListLiteral:
            for e in node.elements:
                self._gen_expr(e)
            self._chunk.emit(Op.BUILD_LIST, len(node.elements)); return

        if t is AttributeAccess:
            self._gen_expr(node.obj)
            self._chunk.emit(Op.LOAD_ATTR, node.attr)
            return

        if t is IndexAccess:
            self._gen_expr(node.obj)
            self._gen_expr(node.index)
            self._chunk.emit(Op.LOAD_INDEX); return

        if t is BinaryOp:
            # Short-circuit: and / or need special jump logic
            if node.op == "and":
                self._gen_expr(node.left)
                j = self._chunk.emit(Op.JUMP_IF_FALSE, None)
                self._chunk.emit(Op.POP)
                self._gen_expr(node.right)
                self._chunk.patch(j, len(self._chunk.instructions))
                return
            if node.op == "or":
                self._gen_expr(node.left)
                j_true = self._chunk.emit(Op.JUMP_IF_FALSE, None)
                j_skip = self._chunk.emit(Op.JUMP, None)
                self._chunk.patch(j_true, len(self._chunk.instructions))
                self._chunk.emit(Op.POP)
                self._gen_expr(node.right)
                self._chunk.patch(j_skip, len(self._chunk.instructions))
                return
            self._gen_expr(node.left)
            self._gen_expr(node.right)
            self._chunk.emit(Op.BINARY_OP, node.op); return

        if t is UnaryOp:
            self._gen_expr(node.operand)
            self._chunk.emit(Op.UNARY_OP, node.op); return

        if t is FunctionCall:
            for a in node.args:
                self._gen_expr(a)
            self._chunk.emit(Op.CALL, (node.name, len(node.args))); return

        if t is MethodCall:
            self._gen_expr(node.obj)
            for a in node.args:
                self._gen_expr(a)
            self._chunk.emit(Op.CALL_METHOD, (node.method, len(node.args))); return

        # Fallback — treat as statement
        self._gen(node)

    # ---------------------------------------------------------------- control flow

    def _gen_if(self, node: IfStmt):
        end_jumps = []

        # if branch
        self._gen_expr(node.condition)
        j_false = self._chunk.emit(Op.JUMP_IF_FALSE, None)
        self._chunk.emit(Op.POP)
        for s in node.then_block:
            self._gen(s)
        end_jumps.append(self._chunk.emit(Op.JUMP, None))
        self._chunk.patch(j_false, len(self._chunk.instructions))
        self._chunk.emit(Op.POP)

        # elif branches
        for cl in node.elif_clauses:
            self._gen_expr(cl.condition)
            j_false = self._chunk.emit(Op.JUMP_IF_FALSE, None)
            self._chunk.emit(Op.POP)
            for s in cl.block:
                self._gen(s)
            end_jumps.append(self._chunk.emit(Op.JUMP, None))
            self._chunk.patch(j_false, len(self._chunk.instructions))
            self._chunk.emit(Op.POP)

        # else branch
        if node.else_block:
            for s in node.else_block:
                self._gen(s)

        # patch all end-of-branch jumps
        end = len(self._chunk.instructions)
        for j in end_jumps:
            self._chunk.patch(j, end)

    def _gen_while(self, node: WhileStmt):
        self._break_patches.append([])
        self._continue_patches.append([])

        loop_start = len(self._chunk.instructions)
        self._gen_expr(node.condition)
        j_exit = self._chunk.emit(Op.JUMP_IF_FALSE, None)
        self._chunk.emit(Op.POP)   # pop truthy condition

        for s in node.block:
            self._gen(s)

        # continue → jump back to condition check
        cont_target = len(self._chunk.instructions)
        for ci in self._continue_patches[-1]:
            self._chunk.patch(ci, cont_target)

        self._chunk.emit(Op.JUMP, loop_start)

        # exit: JUMP_IF_FALSE lands here — condition is still on stack, pop it
        exit_target = len(self._chunk.instructions)
        self._chunk.patch(j_exit, exit_target)
        self._chunk.emit(Op.POP)   # pop falsy condition

        # break jumps here (after the POP so stack is clean)
        break_target = len(self._chunk.instructions)
        for bi in self._break_patches[-1]:
            self._chunk.patch(bi, break_target)

        self._break_patches.pop()
        self._continue_patches.pop()

    def _gen_for(self, node: ForStmt):
        self._break_patches.append([])
        self._continue_patches.append([])

        self._gen_expr(node.iterable)
        self._chunk.emit(Op.GET_ITER)

        iter_start = len(self._chunk.instructions)
        j_exit = self._chunk.emit(Op.FOR_ITER, None)   # patched when done
        self._chunk.emit(Op.STORE_NAME, node.var)

        for s in node.block:
            self._gen(s)

        # continue → jump back to FOR_ITER
        for ci in self._continue_patches[-1]:
            self._chunk.patch(ci, iter_start)

        self._chunk.emit(Op.JUMP, iter_start)
        exit_target = len(self._chunk.instructions)
        self._chunk.patch(j_exit, exit_target)

        for bi in self._break_patches[-1]:
            self._chunk.patch(bi, exit_target)

        self._break_patches.pop()
        self._continue_patches.pop()

    # ---------------------------------------------------------------- functions

    def _compile_function(self, node: FuncDef) -> Chunk:
        chunk = Chunk(name=node.name, params=list(node.params))
        self._chunks.append(chunk)
        saved, self._chunk = self._chunk, chunk
        for s in node.block:
            self._gen(s)
        self._chunk.emit(Op.RETURN_NONE)
        self._chunk = saved
        return chunk
