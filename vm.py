"""
Phase 5+6 — Von Virtual Machine (VM)

Executes the bytecode chunks produced by codegen.py.
Stack-based architecture:
  - operand_stack  holds intermediate values
  - call_stack     holds Frame objects (one per function call)
  - Each Frame has its own local variable dict
"""
from __future__ import annotations
import math as _math
from typing import Any, Dict, List, Optional

from codegen import Chunk, Op


# ------------------------------------------------------------------ runtime types

class VonRuntimeError(Exception):
    def __init__(self, msg: str, line: int = 0):
        super().__init__(f"[RuntimeError] {msg}")


class VonFunction:
    def __init__(self, chunk: Chunk):
        self.chunk = chunk
    def __repr__(self): return f"<function {self.chunk.name}>"


class VonClass:
    def __init__(self, name: str, methods: Dict[str, VonFunction]):
        self.name    = name
        self.methods = methods
    def __repr__(self): return f"<class {self.name}>"


class VonInstance:
    def __init__(self, klass: VonClass):
        self.klass  = klass
        self.fields: Dict[str, Any] = {}
    def __repr__(self): return f"<{self.klass.name} instance>"


class VonList:
    def __init__(self, items: list):
        self.items = list(items)
    def __repr__(self): return "[" + ", ".join(_von_str(i) for i in self.items) + "]"


class VonIterator:
    """Wraps a VonList for use in FOR_ITER."""
    def __init__(self, lst: VonList):
        self.items = lst.items
        self.index = 0

    def has_next(self) -> bool:
        return self.index < len(self.items)

    def next(self) -> Any:
        v = self.items[self.index]
        self.index += 1
        return v


# ------------------------------------------------------------------ helpers

def _von_str(v) -> str:
    if v is None:              return "nil"
    if isinstance(v, bool):    return "true" if v else "false"
    if isinstance(v, VonList): return repr(v)
    if isinstance(v, float) and v == int(v): return str(int(v))
    return str(v)

def _truthy(v) -> bool:
    if v is None or v is False: return False
    if isinstance(v, (int, float)) and v == 0: return False
    if isinstance(v, VonList) and len(v.items) == 0: return False
    return True


# ------------------------------------------------------------------ built-ins

def _b_print(*a):   print(*[_von_str(x) for x in a]); return None
def _b_input(p=""): return input(p)
def _b_num(x):
    try:    return int(x)
    except: return float(x)
def _b_range(*a):   return VonList(list(range(*[int(x) for x in a])))
def _b_len(x):
    if isinstance(x, VonList): return len(x.items)
    if isinstance(x, str):     return len(x)
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

BUILTINS: Dict[str, Any] = {
    "output": _b_print, "print": _b_print, "input": _b_input,
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


# ------------------------------------------------------------------ Frame

class Frame:
    def __init__(self, chunk: Chunk, locals_: Dict[str, Any]):
        self.chunk   = chunk
        self.locals  = locals_
        self.ip      = 0          # instruction pointer

    def fetch(self):
        ins = self.chunk.instructions[self.ip]
        self.ip += 1
        return ins


# ------------------------------------------------------------------ VM

class VM:
    def __init__(self, chunks: List[Chunk]):
        self._chunks  = chunks
        self._stack:  List[Any]   = []
        self._frames: List[Frame] = []
        self._globals: Dict[str, Any] = dict(BUILTINS)

    def run(self):
        main_frame = Frame(self._chunks[0], {})
        self._frames.append(main_frame)
        self._execute()

    # ---------------------------------------------------------------- main loop

    def _execute(self):
        while self._frames:
            frame = self._frames[-1]
            if frame.ip >= len(frame.chunk.instructions):
                self._frames.pop()
                continue

            ins = frame.fetch()
            op  = ins.op
            arg = ins.arg

            # ---- stack / names ----

            if op == Op.LOAD_CONST:
                raw = frame.chunk.constants[arg]
                # Reconstruct function/class objects from their descriptors
                if isinstance(raw, tuple) and raw[0] == "__func__":
                    _, chunk_idx, params = raw
                    self._stack.append(VonFunction(self._chunks[chunk_idx]))
                elif isinstance(raw, tuple) and raw[0] == "__class__":
                    _, name, method_map = raw
                    methods = {
                        mname: VonFunction(self._chunks[cidx])
                        for mname, cidx in method_map.items()
                    }
                    self._stack.append(VonClass(name, methods))
                else:
                    self._stack.append(raw)

            elif op == Op.LOAD_NAME:
                val = frame.locals.get(arg)
                if val is None and arg not in frame.locals:
                    val = self._globals.get(arg)
                    if val is None and arg not in self._globals:
                        raise VonRuntimeError(f"Undefined variable '{arg}'")
                self._stack.append(val)

            elif op == Op.STORE_NAME:
                val = self._stack.pop()
                # Store in local frame if we're inside a function, else global
                if len(self._frames) > 1:
                    frame.locals[arg] = val
                else:
                    self._globals[arg] = val

            elif op == Op.LOAD_ATTR:
                obj = self._stack.pop()
                if isinstance(obj, VonInstance):
                    if arg in obj.fields:
                        self._stack.append(obj.fields[arg])
                    else:
                        raise VonRuntimeError(f"'{obj.klass.name}' has no attribute '{arg}'")
                else:
                    raise VonRuntimeError(f"Cannot read attribute '{arg}' on {type(obj).__name__}")

            elif op == Op.STORE_ATTR:
                val = self._stack.pop()
                obj = self._stack.pop()
                if isinstance(obj, VonInstance):
                    obj.fields[arg] = val
                else:
                    raise VonRuntimeError(f"Cannot set attribute '{arg}' on {type(obj).__name__}")

            elif op == Op.LOAD_INDEX:
                idx = int(self._stack.pop())
                obj = self._stack.pop()
                if isinstance(obj, VonList): self._stack.append(obj.items[idx])
                elif isinstance(obj, str):   self._stack.append(obj[idx])
                else: raise VonRuntimeError("Index requires a list or string")

            elif op == Op.STORE_INDEX:
                val = self._stack.pop()
                idx = int(self._stack.pop())
                obj = self._stack.pop()
                if isinstance(obj, VonList): obj.items[idx] = val
                else: raise VonRuntimeError("Index assignment requires a list")

            # ---- arithmetic ----

            elif op == Op.BINARY_OP:
                r = self._stack.pop()
                l = self._stack.pop()
                self._stack.append(self._binop(arg, l, r))

            elif op == Op.UNARY_OP:
                v = self._stack.pop()
                if arg == "-":   self._stack.append(-v)
                elif arg == "+": self._stack.append(+v)
                elif arg == "not": self._stack.append(not _truthy(v))

            # ---- list ----

            elif op == Op.BUILD_LIST:
                items = list(reversed([self._stack.pop() for _ in range(arg)]))
                self._stack.append(VonList(items))

            # ---- control flow ----

            elif op == Op.JUMP:
                frame.ip = arg

            elif op == Op.JUMP_IF_FALSE:
                if not _truthy(self._stack[-1]):
                    frame.ip = arg

            elif op == Op.POP:
                self._stack.pop()

            # ---- iterators ----

            elif op == Op.GET_ITER:
                obj = self._stack.pop()
                if isinstance(obj, VonList):
                    self._stack.append(VonIterator(obj))
                else:
                    raise VonRuntimeError("'for' requires a list")

            elif op == Op.FOR_ITER:
                it = self._stack[-1]   # peek — leave iterator on stack
                if not isinstance(it, VonIterator) or not it.has_next():
                    self._stack.pop()  # remove exhausted iterator
                    frame.ip = arg
                else:
                    self._stack.append(it.next())

            elif op == Op.STORE_NAME:   # duplicate handled above
                pass

            # ---- calls ----

            elif op == Op.CALL:
                name, argc = arg
                args = list(reversed([self._stack.pop() for _ in range(argc)]))
                callee = frame.locals.get(name) or self._globals.get(name)
                if callee is None:
                    raise VonRuntimeError(f"Undefined '{name}'")
                self._do_call(callee, args, name)

            elif op == Op.CALL_METHOD:
                method_name, argc = arg
                args = list(reversed([self._stack.pop() for _ in range(argc)]))
                obj  = self._stack.pop()
                self._do_method(obj, method_name, args)

            elif op == Op.RETURN:
                retval = self._stack.pop()
                self._frames.pop()
                self._stack.append(retval)

            elif op == Op.RETURN_NONE:
                self._frames.pop()
                self._stack.append(None)

            elif op == Op.HALT:
                return

    # ---------------------------------------------------------------- call helpers

    def _do_call(self, callee, args, name):
        # Python built-in
        if callable(callee) and not isinstance(callee, (VonFunction, VonClass)):
            result = callee(*args)
            self._stack.append(result)
            return

        # Von function
        if isinstance(callee, VonFunction):
            chunk  = callee.chunk
            locals_ = {p: a for p, a in zip(chunk.params, args)}
            self._frames.append(Frame(chunk, locals_))
            return

        # Von class — instantiate
        if isinstance(callee, VonClass):
            inst = VonInstance(callee)
            init = callee.methods.get("init")
            if init:
                locals_ = {"self": inst}
                for p, a in zip(init.chunk.params[1:], args):
                    locals_[p] = a
                # Run init synchronously then push instance
                saved = self._frames[:]
                self._frames = [Frame(init.chunk, locals_)]
                self._execute()
                self._frames = saved
                # Discard the None that RETURN_NONE pushed
                if self._stack and self._stack[-1] is None:
                    self._stack.pop()
            self._stack.append(inst)
            return

        raise VonRuntimeError(f"'{name}' is not callable")

    def _run_init(self, chunk: Chunk, locals_: dict):
        """Run an init method synchronously (blocking) so we can push the instance after."""
        frame = Frame(chunk, locals_)
        saved_frames = self._frames[:]
        self._frames = [frame]
        self._execute()
        self._frames = saved_frames
        # Discard the None return value init pushed
        if self._stack and self._stack[-1] is None:
            self._stack.pop()

    def _do_method(self, obj, method_name, args):
        if isinstance(obj, VonInstance):
            m = obj.klass.methods.get(method_name)
            if m is None:
                raise VonRuntimeError(f"No method '{method_name}' on '{obj.klass.name}'")
            locals_ = {"self": obj}
            # params[0] is 'self', skip it when binding args
            for p, a in zip(m.chunk.params[1:], args):
                locals_[p] = a
            self._frames.append(Frame(m.chunk, locals_))
            return

        if isinstance(obj, VonList):
            if method_name == "length": self._stack.append(len(obj.items)); return
            if method_name == "append": obj.items.append(args[0]); self._stack.append(None); return
            if method_name == "pop":    self._stack.append(obj.items.pop()); return
            if method_name == "sort":   self._stack.append(VonList(sorted(obj.items))); return
            if method_name == "sum":    self._stack.append(sum(obj.items)); return
            if method_name == "max":    self._stack.append(max(obj.items)); return
            if method_name == "min":    self._stack.append(min(obj.items)); return

        if isinstance(obj, str):
            if method_name == "upper":  self._stack.append(obj.upper()); return
            if method_name == "lower":  self._stack.append(obj.lower()); return
            if method_name == "length": self._stack.append(len(obj)); return
            if method_name == "split":
                sep = args[0] if args else None
                self._stack.append(VonList(obj.split(sep))); return

        raise VonRuntimeError(f"No method '{method_name}' on {type(obj).__name__}")

    # ---------------------------------------------------------------- binary ops

    def _binop(self, op, l, r):
        if op == "+":
            if isinstance(l, str) or isinstance(r, str):
                return _von_str(l) + _von_str(r)
            if isinstance(l, VonList) and isinstance(r, VonList):
                return VonList(l.items + r.items)
            return l + r
        if op == "-":  return l - r
        if op == "*":  return l * r
        if op == "/":
            if r == 0: raise VonRuntimeError("Division by zero")
            return l / r
        if op == "%":
            if r == 0: raise VonRuntimeError("Modulo by zero")
            return l % r
        if op == "==": return l == r
        if op == "!=": return l != r
        if op == "<":  return l < r
        if op == ">":  return l > r
        if op == "<=": return l <= r
        if op == ">=": return l >= r
        raise VonRuntimeError(f"Unknown operator '{op}'")
