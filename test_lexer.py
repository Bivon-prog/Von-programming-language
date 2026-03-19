"""
Test script for the Lexer.
Tokenizes a small mathematical function that exercises:
  - function definition (def / return)
  - INDENT / DEDENT emission
  - arithmetic operators and comparison
  - if / else block
  - number literals (int + float)
  - comments (should be silently dropped)
"""

from lexer import Lexer, TokenType

SOURCE = """\
# Compute the quadratic discriminant
def discriminant(a, b, c):
    disc = b * b - 4.0 * a * c
    if disc > 0:
        return disc
    elif disc == 0:
        return 0
    else:
        return -1

result = discriminant(1, -3, 2)
"""

def main():
    lexer  = Lexer(SOURCE)
    tokens = lexer.tokenize()

    print(f"{'TYPE':<14} {'LEXEME':<16} {'LINE':>4}  {'COL':>4}")
    print("-" * 46)
    for tok in tokens:
        print(f"{tok.type.name:<14} {tok.lexeme!r:<16} {tok.line:>4}  {tok.column:>4}")

    # ---------------------------------------------------------------
    # Structural assertions — verify the token stream is well-formed
    # ---------------------------------------------------------------
    types = [t.type for t in tokens]

    # Function definition opens with INDENT, closes with DEDENT
    assert TokenType.DEF    in types, "Missing DEF token"
    assert TokenType.INDENT in types, "Missing INDENT token"
    assert TokenType.DEDENT in types, "Missing DEDENT token"

    # Keyword coverage
    for kw in (TokenType.IF, TokenType.ELIF, TokenType.ELSE, TokenType.RETURN):
        assert kw in types, f"Missing {kw.name} token"

    # Operators
    for op in (TokenType.STAR, TokenType.MINUS, TokenType.GT, TokenType.EQ_EQ):
        assert op in types, f"Missing operator {op.name}"

    # Numbers — both integer and float should appear
    number_lexemes = [t.lexeme for t in tokens if t.type == TokenType.NUMBER]
    assert "4.0" in number_lexemes, "Float literal 4.0 not found"
    assert "0"   in number_lexemes, "Integer literal 0 not found"

    # Stream must end with EOF
    assert types[-1] == TokenType.EOF, "Last token must be EOF"

    # INDENT / DEDENT must be balanced
    indent_count = types.count(TokenType.INDENT)
    dedent_count = types.count(TokenType.DEDENT)
    assert indent_count == dedent_count, (
        f"Unbalanced INDENT/DEDENT: {indent_count} INDENT vs {dedent_count} DEDENT"
    )

    print("\nAll assertions passed.")

if __name__ == "__main__":
    main()
