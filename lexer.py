"""
Lexer for the Von language.
Stack-based indentation tracker emits synthetic INDENT/DEDENT tokens.
"""
from __future__ import annotations
from enum import Enum, auto
from dataclasses import dataclass
from typing import List


class TokenType(Enum):
    # Literals
    NUMBER     = auto()
    STRING     = auto()
    IDENTIFIER = auto()
    # Keywords
    IF         = auto()
    ELIF       = auto()
    ELSE       = auto()
    WHILE      = auto()
    FOR        = auto()
    IN         = auto()
    BREAK      = auto()
    CONTINUE   = auto()
    DEF        = auto()
    CLASS      = auto()
    RETURN     = auto()
    AND        = auto()
    OR         = auto()
    NOT        = auto()
    # Operators
    PLUS       = auto()
    MINUS      = auto()
    STAR       = auto()
    SLASH      = auto()
    PERCENT    = auto()
    EQ_EQ      = auto()
    BANG_EQ    = auto()
    LT         = auto()
    GT         = auto()
    LT_EQ      = auto()
    GT_EQ      = auto()
    EQUAL      = auto()
    # Delimiters
    LPAREN     = auto()
    RPAREN     = auto()
    LBRACKET   = auto()
    RBRACKET   = auto()
    COLON      = auto()
    COMMA      = auto()
    DOT        = auto()
    # Synthetic
    NEWLINE    = auto()
    INDENT     = auto()
    DEDENT     = auto()
    EOF        = auto()


KEYWORDS = {
    "if": TokenType.IF, "elif": TokenType.ELIF, "else": TokenType.ELSE,
    "while": TokenType.WHILE, "for": TokenType.FOR, "in": TokenType.IN,
    "break": TokenType.BREAK, "continue": TokenType.CONTINUE,
    "def": TokenType.DEF, "class": TokenType.CLASS, "return": TokenType.RETURN,
    "and": TokenType.AND, "or": TokenType.OR, "not": TokenType.NOT,
}


@dataclass
class Token:
    type:   TokenType
    lexeme: str
    line:   int
    column: int

    def __repr__(self):
        return f"Token({self.type.name}, {self.lexeme!r}, line={self.line}, col={self.column})"


class LexerError(Exception):
    def __init__(self, msg: str, line: int, col: int):
        super().__init__(f"[LexerError] Line {line}, Col {col}: {msg}")
        self.line = line; self.column = col


class Lexer:
    def __init__(self, source: str):
        self._src    = source
        self._tokens: List[Token] = []
        self._start  = 0
        self._cur    = 0
        self._line   = 1
        self._lstart = 0
        self._indent_stack: List[int] = [0]
        self._at_bol = True   # at beginning of line

    def tokenize(self) -> List[Token]:
        while not self._end():
            self._start = self._cur
            self._scan()
        self._close_indents()
        self._add(TokenType.NEWLINE, "")
        self._add(TokenType.EOF, "")
        return self._tokens

    def _scan(self):
        if self._at_bol:
            self._handle_indent()
            if self._end():
                return

        c = self._advance()

        if c == '#':
            while not self._end() and self._peek() != '\n':
                self._advance()
            return
        if c in (' ', '\t', '\r'):
            return
        if c == '\n':
            if self._tokens and self._tokens[-1].type not in (
                    TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
                self._add(TokenType.NEWLINE, "\\n")
            self._line += 1
            self._lstart = self._cur
            self._at_bol = True
            return

        two = {('=','='): TokenType.EQ_EQ, ('!','='): TokenType.BANG_EQ,
               ('<','='): TokenType.LT_EQ, ('>','='): TokenType.GT_EQ}
        for (a, b), tt in two.items():
            if c == a and self._match(b):
                self._add(tt, c + b); return

        single = {'+':TokenType.PLUS,'-':TokenType.MINUS,'*':TokenType.STAR,
                  '/':TokenType.SLASH,'%':TokenType.PERCENT,'<':TokenType.LT,
                  '>':TokenType.GT,'=':TokenType.EQUAL,'(':TokenType.LPAREN,
                  ')':TokenType.RPAREN,'[':TokenType.LBRACKET,']':TokenType.RBRACKET,
                  ':':TokenType.COLON,',':TokenType.COMMA,'.':TokenType.DOT}
        if c in single:
            self._add(single[c], c); return

        if c in ('"', "'"):
            self._scan_string(c); return
        if c.isdigit():
            self._scan_number(); return
        if c.isalpha() or c == '_':
            self._scan_ident(); return

        raise LexerError(f"Unexpected character {c!r}", self._line, self._col())

    def _handle_indent(self):
        self._at_bol = False
        level = 0
        pos   = self._cur
        while pos < len(self._src) and self._src[pos] in (' ', '\t'):
            level = (level // 8 + 1) * 8 if self._src[pos] == '\t' else level + 1
            pos += 1
        if pos >= len(self._src):
            self._cur = pos; return
        nc = self._src[pos]
        if nc in ('\n', '#'):
            self._cur = pos; return
        self._cur = self._start = pos
        top = self._indent_stack[-1]
        if level > top:
            self._indent_stack.append(level)
            self._add(TokenType.INDENT, "")
        elif level < top:
            while self._indent_stack[-1] > level:
                self._indent_stack.pop()
                self._add(TokenType.DEDENT, "")
            if self._indent_stack[-1] != level:
                raise LexerError("Indentation mismatch", self._line, 1)

    def _close_indents(self):
        while len(self._indent_stack) > 1:
            self._indent_stack.pop()
            self._add(TokenType.DEDENT, "")

    def _scan_string(self, q):
        while not self._end() and self._peek() != q:
            if self._peek() == '\n':
                raise LexerError("Unterminated string", self._line, self._col())
            if self._peek() == '\\':
                self._advance()
            self._advance()
        if self._end():
            raise LexerError("Unterminated string", self._line, self._col())
        self._advance()
        self._add(TokenType.STRING, self._src[self._start:self._cur])

    def _scan_number(self):
        while not self._end() and self._peek().isdigit():
            self._advance()
        if not self._end() and self._peek() == '.' and self._peek2().isdigit():
            self._advance()
            while not self._end() and self._peek().isdigit():
                self._advance()
        self._add(TokenType.NUMBER, self._src[self._start:self._cur])

    def _scan_ident(self):
        while not self._end() and (self._peek().isalnum() or self._peek() == '_'):
            self._advance()
        lex = self._src[self._start:self._cur]
        self._add(KEYWORDS.get(lex, TokenType.IDENTIFIER), lex)

    def _end(self):   return self._cur >= len(self._src)
    def _advance(self):
        c = self._src[self._cur]; self._cur += 1; return c
    def _match(self, e):
        if self._end() or self._src[self._cur] != e: return False
        self._cur += 1; return True
    def _peek(self):  return '\0' if self._end() else self._src[self._cur]
    def _peek2(self): return '\0' if self._cur+1 >= len(self._src) else self._src[self._cur+1]
    def _col(self):   return self._cur - self._lstart
    def _add(self, tt, lex):
        col = (self._cur - self._lstart) - len(lex) + 1
        self._tokens.append(Token(tt, lex, self._line, col))
