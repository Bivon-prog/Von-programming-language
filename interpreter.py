"""Tree-walking interpreter for the Von language."""
from __future__ import annotations
import math as _math
from typing import Any, Dict, List, Optional

from ast_nodes import (
    Program, Number, String, Identifier, ListLiteral, IndexAccess, IndexAssign,
    BinaryOp, UnaryOp, Assignment, FunctionCall, MethodCall,
    ReturnStmt, BreakStmt, ContinueStmt,
    IfStmt, WhileStmt, ForStmt, FuncDef, ClassDef,
)


class _Return(Exception):
    def __init__(self, v): self.value = v

class _Break(Exception): pass
class _Continue(Exception): pass

class VonRuntimeError(Exception):
    def __init__(self, msg, line=0):
        super().__init__(f"[RuntimeError] Line {line}: {msg}")


class Env:
    def __init__(self, parent=None):
        self._s: Dict[str, Any] = {}
        self._p = parent

    def get(self, name, line=0):
        if name in self._s: return self._s[name]
        if self._p:         return self._p.get(name, line)
        raise VonRuntimeError(f"Undefined variable {name!r}", line)

    def set(self, name, val):
        self._s[name] = val

    def assign(self, name, val, line=0):
        if name in self._s:               self._s[name] = val
        elif self._p and self._p._has(name): self._p.assign(name, val, line)
        else:                             self._s[name] = val

    def _has(self, name):
        return name in self._s or (self._p._has(name) if self._p else False)


class VonFunction:
    def __init__(self, node, closure):
        self.node = node; self.closure = closure
    def __repr__(self): return f"<function {self.node.name}>"

class VonClass:
    def __init__(self, node, closure):
        self.node = node; self.closure = closure
        self.methods: Dict[str, VonFunction] = {}
    def __repr__(self): return f"<class {self.node.name}>"

class VonInstance:
    def __init__(self, klass):
        self.klass = klass; self.fields: Dict[str, Any] = {}
    def __repr__(self): return f"<{self.klass.node.name} instance>"

class VonList:
    def __init__(self, items):
        self.items = list(items)
    def __repr__(self): return "[" + ", ".join(_von_str(i) for i in self.items) + "]"


def _von_str(v):
    if v is None:              return "nil"
    if isinstance(v, bool):    return "true" if v else "false"
    if isinstance(v, VonList): return repr(v)
    if isinstance(v, float) and v == int(v): return str(int(v))
    return str(v)

def _b_print(*a):   print(*[_von_str(x) for x in a]); return None
def _b_input(p=""): return input(p)
def _b_num(x):
    try:    return int(x)
    except: return float(x)
def _b_range(*a):   return VonList(range(*[int(x) for x in a]))
def _b_len(x):
    if isinstance(x, (VonList, str)): return len(x.items if isinstance(x, VonList) else x)
    raise VonRuntimeError("len() requires a list or string")
def _b_sum(x):
    if isinstance(x, VonList): return sum(x.items)
    raise VonRuntimeError("sum() requires a list")
def _b_sort(x):
    if isinstance(x, VonList): return VonList(sorted(x.items))
    raise VonRuntimeError("sort() requires a list")
def _b_append(lst, val):
    if isinstance(lst, VonList): lst.items.append(val); return None
    raise VonRuntimeError("append() requires a list")
def _b_pop(lst):
    if isinstance(lst, VonList): return lst.items.pop()
    raise VonRuntimeError("pop() requires a list")

BUILTINS = {
    "print": _b_print, "input": _b_input,
    "num": _b_num, "str": _von_str,
    "sqrt": _math.sqrt, "abs": abs, "pow": pow,
    "floor": _math.floor, "ceil": _math.ceil, "round": round,
    "max": max, "min": min,
    "sin": _math.sin, "cos": _math.cos, "tan": _math.tan,
    "log": _math.log, "log2": _math.log2, "log10": _math.log10,
    "exp": _math.exp,
    "range": _b_range, "len": _b_len, "sum": _b_sum,
    "sort": _b_sort, "append": _b_append, "pop": _b_pop,
    "pi": _math.pi, "e": _math.e, "tau": _math.tau,
    "true": True, "false": False, "nil": None,
}


class Interpreter:
    def __init__(self):
        self._globals = Env()
        for k, v in BUILTINS.items():
            self._globals.set(k, v)

    def run(self, program):
        for s in program.statements:
            self._exec(s, self._globals)

    def _exec(self, node, env):
        t = type(node)
        if t is Assignment:
            v = self._eval(node.value, env)
            env.assign(node.name, v, node.line); return v
        if t is IndexAssign:
            lst = env.get(node.name, node.line)
            idx = int(self._eval(node.index, env))
            val = self._eval(node.value, env)
            if isinstance(lst, VonList): lst.items[idx] = val; return val
            raise VonRuntimeError("Index assignment requires a list", node.line)
        if t is FuncDef:
            fn = VonFunction(node, env); env.set(node.name, fn); return fn
        if t is ClassDef:
            klass = VonClass(node, env)
            for s in node.block:
                if isinstance(s, FuncDef):
                    klass.methods[s.name] = VonFunction(s, env)
            env.set(node.name, klass); return klass
        if t is ReturnStmt:
            raise _Return(self._eval(node.value, env) if node.value is not None else None)
        if t is BreakStmt:    raise _Break()
        if t is ContinueStmt: raise _Continue()
        if t is IfStmt:       return self._exec_if(node, env)
        if t is WhileStmt:    return self._exec_while(node, env)
        if t is ForStmt:      return self._exec_for(node, env)
        return self._eval(node, env)

    def _exec_if(self, node, env):
        if self._truthy(self._eval(node.condition, env)):
            self._run_block(node.then_block, env); return
        for cl in node.elif_clauses:
            if self._truthy(self._eval(cl.condition, env)):
                self._run_block(cl.block, env); return
        if node.else_block is not None:
            self._run_block(node.else_block, env)

    def _exec_while(self, node, env):
        while self._truthy(self._eval(node.condition, env)):
            try:
                self._run_block(node.block, env)
            except _Break:    break
            except _Continue: continue

    def _exec_for(self, node, env):
        it = self._eval(node.iterable, env)
        items = it.items if isinstance(it, VonList) else list(it)
        for val in items:
            local = Env(parent=env)
            local.set(node.var, val)
            try:
                for s in node.block:
                    self._exec(s, local)
            except _Break:    break
            except _Continue: continue

    def _run_block(self, stmts, env):
        local = Env(parent=env)
        for s in stmts:
            self._exec(s, local)

    def _eval(self, node, env):
        t = type(node)
        if t is Number:      return node.value
        if t is String:      return node.value
        if t is Identifier:  return env.get(node.name, node.line)
        if t is ListLiteral: return VonList([self._eval(e, env) for e in node.elements])
        if t is IndexAccess:
            obj = self._eval(node.obj, env)
            idx = int(self._eval(node.index, env))
            if isinstance(obj, VonList): return obj.items[idx]
            if isinstance(obj, str):     return obj[idx]
            raise VonRuntimeError("Index access requires a list or string", node.line)
        if t is BinaryOp:     return self._binop(node, env)
        if t is UnaryOp:      return self._unary(node, env)
        if t is FunctionCall: return self._call(node, env)
        if t is MethodCall:   return self._method(node, env)
        return self._exec(node, env)

    def _binop(self, node, env):
        op = node.op
        if op == "and":
            l = self._eval(node.left, env)
            return l if not self._truthy(l) else self._eval(node.right, env)
        if op == "or":
            l = self._eval(node.left, env)
            return l if self._truthy(l) else self._eval(node.right, env)
        l = self._eval(node.left, env)
        r = self._eval(node.right, env)
        try:
            if op == "+":
                if isinstance(l, str) or isinstance(r, str):
                    return _von_str(l) + _von_str(r)
                if isinstance(l, VonList) and isinstance(r, VonList):
                    return VonList(l.items + r.items)
                return l + r
            if op == "-":  return l - r
            if op == "*":  return l * r
            if op == "/":
                if r == 0: raise VonRuntimeError("Division by zero", node.line)
                return l / r
            if op == "%":
                if r == 0: raise VonRuntimeError("Modulo by zero", node.line)
                return l % r
            if op == "==": return l == r
            if op == "!=": return l != r
            if op == "<":  return l < r
            if op == ">":  return l > r
            if op == "<=": return l <= r
            if op == ">=": return l >= r
        except TypeError as ex:
            raise VonRuntimeError(str(ex), node.line)
        raise VonRuntimeError(f"Unknown operator {op!r}", node.line)

    def _unary(self, node, env):
        v = self._eval(node.operand, env)
        if node.op == "-":   return -v
        if node.op == "+":   return +v
        if node.op == "not": return not self._truthy(v)
        raise VonRuntimeError(f"Unknown unary op {node.op!r}", node.line)

    def _call(self, node, env):
        callee = env.get(node.name, node.line)
        args   = [self._eval(a, env) for a in node.args]
        if callable(callee) and not isinstance(callee, (VonFunction, VonClass)):
            return callee(*args)
        if isinstance(callee, VonFunction):
            return self._invoke(callee, args, node.line)
        if isinstance(callee, VonClass):
            return self._instantiate(callee, args, node.line)
        raise VonRuntimeError(f"{node.name!r} is not callable", node.line)

    def _method(self, node, env):
        obj  = self._eval(node.obj, env)
        args = [self._eval(a, env) for a in node.args]
        if isinstance(obj, VonInstance):
            m = obj.klass.methods.get(node.method)
            if m is None:
                raise VonRuntimeError(
                    f"{obj.klass.node.name!r} has no method {node.method!r}", node.line)
            return self._invoke(m, args, node.line, instance=obj)
        if isinstance(obj, VonList):
            if node.method == "length": return len(obj.items)
            if node.method == "append": obj.items.append(args[0]); return None
            if node.method == "pop":    return obj.items.pop()
            if node.method == "sort":   return VonList(sorted(obj.items))
            if node.method == "sum":    return sum(obj.items)
            if node.method == "max":    return max(obj.items)
            if node.method == "min":    return min(obj.items)
        if isinstance(obj, str):
            if node.method == "upper":  return obj.upper()
            if node.method == "lower":  return obj.lower()
            if node.method == "length": return len(obj)
            if node.method == "split":
                sep = args[0] if args else None
                return VonList(obj.split(sep))
        raise VonRuntimeError(
            f"No method {node.method!r} on {type(obj).__name__}", node.line)

    def _invoke(self, fn, args, line, instance=None):
        if len(args) != len(fn.node.params):
            raise VonRuntimeError(
                f"{fn.node.name!r} expects {len(fn.node.params)} args, got {len(args)}", line)
        local = Env(parent=fn.closure)
        if instance is not None: local.set("self", instance)
        for p, a in zip(fn.node.params, args):
            local.set(p, a)
        try:
            for s in fn.node.block:
                self._exec(s, local)
        except _Return as r:
            return r.value
        return None

    def _instantiate(self, klass, args, line):
        inst = VonInstance(klass)
        init = klass.methods.get("init")
        if init: self._invoke(init, args, line, instance=inst)
        return inst

    @staticmethod
    def _truthy(v):
        if v is None or v is False: return False
        if isinstance(v, (int, float)) and v == 0: return False
        if isinstance(v, VonList) and len(v.items) == 0: return False
        return True
