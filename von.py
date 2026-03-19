#!/usr/bin/env python3
"""
von.py — Von language CLI
Usage:
    python von.py <file.von>   # run a file
    python von.py              # interactive REPL
"""
import sys, os
from lexer       import Lexer, LexerError
from parser      import Parser, ParseError
from interpreter import Interpreter, VonRuntimeError

BANNER = """\
  ██╗   ██╗ ██████╗ ███╗   ██╗
  ██║   ██║██╔═══██╗████╗  ██║
  ██║   ██║██║   ██║██╔██╗ ██║
  ╚██╗ ██╔╝██║   ██║██║╚██╗██║
   ╚████╔╝ ╚██████╔╝██║ ╚████║
    ╚═══╝   ╚═════╝ ╚═╝  ╚═══╝
  Von Language  v1.1.0
  Type 'exit' or Ctrl-C to quit.
"""


def _show_error(err: Exception, source: str):
    """Print the error with the offending source line highlighted."""
    print(err, file=sys.stderr)
    line_no = getattr(err, 'line', None) or getattr(getattr(err, 'token', None), 'line', None)
    if line_no:
        lines = source.splitlines()
        if 0 < line_no <= len(lines):
            print(f"  --> {lines[line_no - 1]}", file=sys.stderr)
            col = getattr(err, 'column', None) or getattr(getattr(err, 'token', None), 'column', 1)
            print(f"      {' ' * (col - 1)}^", file=sys.stderr)


def run_source(source: str, interp: Interpreter, filename="<stdin>") -> bool:
    try:
        tokens = Lexer(source).tokenize()
        ast    = Parser(tokens).parse()
        interp.run(ast)
        return True
    except (LexerError, ParseError, VonRuntimeError) as e:
        _show_error(e, source)
    except Exception as e:
        print(f"[InternalError] {e}", file=sys.stderr)
    return False


def run_file(path: str):
    if not os.path.exists(path):
        print(f"von: cannot open '{path}'", file=sys.stderr); sys.exit(1)
    source = open(path, encoding="utf-8").read()
    ok = run_source(source, Interpreter(), filename=path)
    sys.exit(0 if ok else 1)


def repl():
    print(BANNER)
    interp = Interpreter()
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
        run_source(source, interp)


def main():
    if len(sys.argv) == 2:   run_file(sys.argv[1])
    elif len(sys.argv) == 1: repl()
    else:
        print("Usage: python von.py [file.von]", file=sys.stderr); sys.exit(1)

if __name__ == "__main__":
    main()
