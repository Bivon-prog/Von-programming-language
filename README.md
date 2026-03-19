# Von Programming Language

Von is a dynamically-typed, object-oriented programming language designed for mathematical computing. It uses Python-like indentation syntax — no curly braces, no semicolons.

## Run a program
```
python von.py myprogram.von
```

## Interactive REPL
```
python von.py
```

## Example
```
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print(factorial(10))
```

See `VON_DOCS.md` for the full language documentation.
