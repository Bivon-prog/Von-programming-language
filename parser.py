"""Recursive-descent parser for the Von language."""
from __future__ import annotations
from typing import List, Any
from lexer import Token, TokenType
from ast_nodes import (
    Program, Number, String, Identifier, ListLiteral, IndexAccess, IndexAssign,
    BinaryOp, UnaryOp, Assignment, FunctionCall, MethodCall,
    AttributeAccess, AttributeAssign,
    ReturnStmt, BreakStmt, ContinueStmt,
    IfStmt, ElifClause, WhileStmt, ForStmt, FuncDef, ClassDef,
)


class ParseError(Exception):
    def __init__(self, msg, tok):
        super().__init__(f"[ParseError] Line {tok.line}, Col {tok.column}: {msg}")
        self.token = tok


class Parser:
    def __init__(self, tokens):
        self._tokens = tokens
        self._pos = 0

    def parse(self):
        stmts = []
        self._skip_nl()
        while not self._check(TokenType.EOF):
            stmts.append(self._stmt())
            self._skip_nl()
        return Program(stmts)

    def _stmt(self):
        t = self._cur().type
        if t == TokenType.DEF:      return self._func_def()
        if t == TokenType.CLASS:    return self._class_def()
        if t == TokenType.IF:       return self._if_stmt()
        if t == TokenType.WHILE:    return self._while_stmt()
        if t == TokenType.FOR:      return self._for_stmt()
        if t == TokenType.RETURN:   return self._return_stmt()
        if t == TokenType.BREAK:
            tok = self._adv(); self._expect_nl(); return BreakStmt(tok.line)
        if t == TokenType.CONTINUE:
            tok = self._adv(); self._expect_nl(); return ContinueStmt(tok.line)
        if t == TokenType.IDENTIFIER and self._peek_t(1) == TokenType.LBRACKET:
            return self._maybe_index_assign()
        if t == TokenType.IDENTIFIER and self._peek_t(1) == TokenType.EQUAL:
            return self._assignment()
        if (t == TokenType.IDENTIFIER
                and self._peek_t(1) == TokenType.DOT
                and self._peek_t(2) == TokenType.IDENTIFIER
                and self._peek_t(3) == TokenType.EQUAL):
            return self._attr_assign()
        node = self._expr()
        self._expect_nl()
        return node

    def _assignment(self):
        tok = self._adv()
        self._consume(TokenType.EQUAL, "Expected =")
        val = self._expr(); self._expect_nl()
        return Assignment(tok.lexeme, val, tok.line)

    def _return_stmt(self):
        tok = self._consume(TokenType.RETURN, "Expected return")
        val = None
        if not self._check(TokenType.NEWLINE) and not self._check(TokenType.EOF):
            val = self._expr()
        self._expect_nl()
        return ReturnStmt(val, tok.line)

    def _if_stmt(self):
        tok = self._consume(TokenType.IF, "Expected if")
        cond = self._expr()
        self._consume(TokenType.COLON, "Expected :"); self._expect_nl()
        then = self._block(); elifs = []
        while self._check(TokenType.ELIF):
            et = self._adv(); ec = self._expr()
            self._consume(TokenType.COLON, "Expected :"); self._expect_nl()
            elifs.append(ElifClause(ec, self._block(), et.line))
        else_b = None
        if self._check(TokenType.ELSE):
            self._adv()
            self._consume(TokenType.COLON, "Expected :"); self._expect_nl()
            else_b = self._block()
        return IfStmt(cond, then, elifs, else_b, tok.line)

    def _while_stmt(self):
        tok = self._consume(TokenType.WHILE, "Expected while")
        cond = self._expr()
        self._consume(TokenType.COLON, "Expected :"); self._expect_nl()
        return WhileStmt(cond, self._block(), tok.line)

    def _for_stmt(self):
        tok = self._consume(TokenType.FOR, "Expected for")
        var = self._consume(TokenType.IDENTIFIER, "Expected variable").lexeme
        self._consume(TokenType.IN, "Expected in")
        it = self._expr()
        self._consume(TokenType.COLON, "Expected :"); self._expect_nl()
        return ForStmt(var, it, self._block(), tok.line)

    def _func_def(self):
        tok = self._consume(TokenType.DEF, "Expected def")
        name = self._consume(TokenType.IDENTIFIER, "Expected function name").lexeme
        self._consume(TokenType.LPAREN, "Expected (")
        params = self._params()
        self._consume(TokenType.RPAREN, "Expected )")
        self._consume(TokenType.COLON, "Expected :"); self._expect_nl()
        return FuncDef(name, params, self._block(), tok.line)

    def _class_def(self):
        tok = self._consume(TokenType.CLASS, "Expected class")
        name = self._consume(TokenType.IDENTIFIER, "Expected class name").lexeme
        self._consume(TokenType.COLON, "Expected :"); self._expect_nl()
        return ClassDef(name, self._block(), tok.line)

    def _attr_assign(self):
        obj_tok = self._adv()
        self._adv()  # '.'
        attr_tok = self._adv()
        self._consume(TokenType.EQUAL, "Expected =")
        val = self._expr(); self._expect_nl()
        return AttributeAssign(Identifier(obj_tok.lexeme, obj_tok.line), attr_tok.lexeme, val, obj_tok.line)

    def _maybe_index_assign(self):
        name_tok = self._adv(); self._adv()
        idx = self._expr()
        self._consume(TokenType.RBRACKET, "Expected ]")
        if self._check(TokenType.EQUAL):
            self._adv(); val = self._expr(); self._expect_nl()
            return IndexAssign(name_tok.lexeme, idx, val, name_tok.line)
        node = self._postfix(
            IndexAccess(Identifier(name_tok.lexeme, name_tok.line), idx, name_tok.line))
        self._expect_nl(); return node

    def _params(self):
        p = []
        if self._check(TokenType.IDENTIFIER):
            p.append(self._adv().lexeme)
            while self._match(TokenType.COMMA):
                p.append(self._consume(TokenType.IDENTIFIER, "Expected param").lexeme)
        return p

    def _block(self):
        self._consume(TokenType.INDENT, "Expected INDENT")
        stmts = []; self._skip_nl()
        while not self._check(TokenType.DEDENT) and not self._check(TokenType.EOF):
            stmts.append(self._stmt()); self._skip_nl()
        self._consume(TokenType.DEDENT, "Expected DEDENT")
        return stmts

    def _expr(self):   return self._or()

    def _or(self):
        l = self._and()
        while self._check(TokenType.OR):
            op = self._adv().lexeme; l = BinaryOp(op, l, self._and())
        return l

    def _and(self):
        l = self._eq()
        while self._check(TokenType.AND):
            op = self._adv().lexeme; l = BinaryOp(op, l, self._eq())
        return l

    def _eq(self):
        l = self._cmp()
        while self._cur().type in (TokenType.EQ_EQ, TokenType.BANG_EQ):
            op = self._adv().lexeme; l = BinaryOp(op, l, self._cmp())
        return l

    def _cmp(self):
        l = self._term()
        while self._cur().type in (TokenType.LT, TokenType.GT,
                                    TokenType.LT_EQ, TokenType.GT_EQ):
            op = self._adv().lexeme; l = BinaryOp(op, l, self._term())
        return l

    def _term(self):
        l = self._factor()
        while self._cur().type in (TokenType.PLUS, TokenType.MINUS):
            op = self._adv().lexeme; l = BinaryOp(op, l, self._factor())
        return l

    def _factor(self):
        l = self._unary()
        while self._cur().type in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self._adv().lexeme; l = BinaryOp(op, l, self._unary())
        return l

    def _unary(self):
        if self._cur().type in (TokenType.MINUS, TokenType.PLUS, TokenType.NOT):
            op = self._adv().lexeme; return UnaryOp(op, self._unary())
        return self._primary()

    def _primary(self):
        tok = self._cur()
        if tok.type == TokenType.NUMBER:
            self._adv()
            v = float(tok.lexeme) if "." in tok.lexeme else int(tok.lexeme)
            return Number(v, tok.line)
        if tok.type == TokenType.STRING:
            self._adv(); return String(tok.lexeme[1:-1], tok.line)
        if tok.type == TokenType.LPAREN:
            self._adv(); e = self._expr()
            self._consume(TokenType.RPAREN, "Expected )"); return e
        if tok.type == TokenType.LBRACKET:
            return self._list_lit()
        if tok.type == TokenType.IDENTIFIER:
            return self._ident_or_call()
        raise ParseError(f"Unexpected token {tok.lexeme!r}", tok)

    def _list_lit(self):
        tok = self._consume(TokenType.LBRACKET, "Expected [")
        elems = []
        if not self._check(TokenType.RBRACKET):
            elems.append(self._expr())
            while self._match(TokenType.COMMA):
                if self._check(TokenType.RBRACKET): break
                elems.append(self._expr())
        self._consume(TokenType.RBRACKET, "Expected ]")
        return ListLiteral(elems, tok.line)

    def _ident_or_call(self):
        tok = self._adv()
        node = Identifier(tok.lexeme, tok.line)
        if self._check(TokenType.LPAREN):
            self._adv(); args = self._args()
            self._consume(TokenType.RPAREN, "Expected )")
            node = FunctionCall(tok.lexeme, args, tok.line)
        return self._postfix(node)

    def _postfix(self, node):
        while True:
            if self._check(TokenType.DOT):
                self._adv()
                mt = self._consume(TokenType.IDENTIFIER, "Expected attribute name")
                if self._check(TokenType.LPAREN):
                    self._adv(); args = self._args()
                    self._consume(TokenType.RPAREN, "Expected )")
                    node = MethodCall(node, mt.lexeme, args, mt.line)
                else:
                    node = AttributeAccess(node, mt.lexeme, mt.line)
            elif self._check(TokenType.LBRACKET):
                self._adv(); idx = self._expr()
                self._consume(TokenType.RBRACKET, "Expected ]")
                node = IndexAccess(node, idx, node.line)
            else:
                break
        return node

    def _args(self):
        a = []
        if not self._check(TokenType.RPAREN):
            a.append(self._expr())
            while self._match(TokenType.COMMA):
                a.append(self._expr())
        return a

    def _cur(self):       return self._tokens[self._pos]
    def _peek_t(self, n):
        i = self._pos + n
        return self._tokens[i].type if i < len(self._tokens) else TokenType.EOF
    def _adv(self):
        t = self._tokens[self._pos]
        if t.type != TokenType.EOF: self._pos += 1
        return t
    def _check(self, tt):  return self._cur().type == tt
    def _match(self, tt):
        if self._check(tt): self._adv(); return True
        return False
    def _consume(self, tt, msg):
        if self._check(tt): return self._adv()
        raise ParseError(msg + f" (got {self._cur().lexeme!r})", self._cur())
    def _expect_nl(self):
        if self._check(TokenType.NEWLINE): self._adv()
    def _skip_nl(self):
        while self._check(TokenType.NEWLINE): self._adv()
