#!/usr/bin/env python3
"""
von.py — Von language compiler + VM  (v2.0)

Full pipeline:
  Source → Lexer → Parser → Semantic Analyser → Code Generator → VM

Usage:
    python von.py <file.von>          run a file
    python von.py --dump <file.von>   run + print bytecode disassembly
    python von.py                     interactive REPL
"""
import sys, os
from lexer       import Lexer,    LexerError
from parser      import Parser,   ParseError
from semantic    import SemanticAnalyser, SemanticError
from codegen     import CodeGen
from vm          import VM,       VonRuntimeError

BANNER = """\
  ██╗   ██╗ ██████╗ ███╗   ██╗
  ██║   ██║██╔═══██╗████╗  ██║
  ██║   ██║██║   ██║██╔██╗ ██║
  ╚██╗ ██╔╝██║   ██║██║╚██╗██║
   ╚████╔╝ ╚██████╔╝██║ ╚████║
    ╚═══╝   ╚═════╝ ╚═╝  ╚═══╝
  Von Language  v2.0.0  (bytecode VM)
  Type 'exit' or Ctrl-C to quit.
"""


def _show_error(err: Exception, source: str):
    print(err, file=sys.stderr)
    line_no = getattr(err, 'line', None) or getattr(getattr(err, 'token', None), 'line', None)
    if line_no:
        lines = source.splitlines()
        if 0 < line_no <= len(lines):
            print(f"  --> {lines[line_no - 1]}", file=sys.stderr)
            col = getattr(err, 'column', None) or getattr(getattr(err, 'token', None), 'column', 1) or 1
            print(f"      {' ' * (col - 1)}^", file=sys.stderr)


def compile_source(source: str):
    """Lex → Parse → Semantic → CodeGen. Returns (chunks, warnings) or raises."""
    tokens  = Lexer(source).tokenize()
    ast     = Parser(tokens).parse()
    analyser = SemanticAnalyser()
    analyser.analyse(ast)
    chunks  = CodeGen().compile(ast)
    return chunks, analyser.warnings


def run_source(source: str, dump: bool = False, filename: str = "<stdin>") -> bool:
    try:
        chunks, warnings = compile_source(source)
        for w in warnings:
            print(w, file=sys.stderr)
        if dump:
            for chunk in chunks:
                print(chunk.disassemble())
                print()
        VM(chunks).run()
        return True
    except (LexerError, ParseError, SemanticError) as e:
        _show_error(e, source)
    except VonRuntimeError as e:
        print(e, file=sys.stderr)
    except Exception as e:
        print(f"[InternalError] {e}", file=sys.stderr)
        import traceback; traceback.print_exc()
    return False


def run_file(path: str, dump: bool = False):
    if not os.path.exists(path):
        print(f"von: cannot open '{path}'", file=sys.stderr); sys.exit(1)
    source = open(path, encoding="utf-8").read()
    ok = run_source(source, dump=dump, filename=path)
    sys.exit(0 if ok else 1)


def repl():
    print(BANNER)
    buf, depth = [], 0
    while True:
        try:
            line = input("... " if buf else "von> ")
        except (EOFError, KeyboardInterrupt):
            print("\nBye."); break
        if line.strip() == "exit":
            print("Bye."); break
        buf.append(line)
        if line.rstrip().endswith(":"):
            depth += 1; continue
        if depth > 0:
            if line.strip() == "":
                depth -= 1
                if depth > 0: continue
            else:
                continue
        source = "\n".join(buf) + "\n"
        buf.clear(); depth = 0
        run_source(source)


def main():
    dump = "--dump" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--dump"]
    if len(args) == 1:   run_file(args[0], dump=dump)
    elif len(args) == 0: repl()
    else:
        print("Usage: python von.py [--dump] [file.von]", file=sys.stderr); sys.exit(1)


if __name__ == "__main__":
    main()
