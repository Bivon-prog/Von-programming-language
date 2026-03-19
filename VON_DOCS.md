# Von Language — Official Documentation
> Version 1.1.0

---

## Table of Contents

1. [What is Von?](#1-what-is-von)
2. [How to Run Von Programs](#2-how-to-run-von-programs)
3. [How the Compiler Works](#3-how-the-compiler-works)
4. [Language Guide](#4-language-guide)
   - Variables
   - Data Types
   - Operators
   - Strings
   - Lists
   - Conditionals
   - While Loop
   - For Loop
   - Functions
   - Classes
   - Built-in Functions
5. [Built-in Reference](#5-built-in-reference)
6. [Error Messages](#6-error-messages)

---

## 1. What is Von?

Von is a dynamically-typed, object-oriented programming language designed for **mathematical computing**. It uses Python-like indentation syntax — no curly braces, no semicolons. Everything is an expression, and the language supports implicit type coercion, meaning numbers and strings can mix naturally in operations.

Von programs are stored in files with the `.von` extension and executed using the Von interpreter (`von.py`).

---

## 2. How to Run Von Programs

### Run a file
```
python von.py myprogram.von
```

### Start the interactive REPL
```
python von.py
```

In the REPL you type Von code line by line and see results immediately. Type `exit` to quit.

### Example
Create a file called `hello.von`:
```
print("Hello from Von!")
```
Run it:
```
python von.py hello.von
```
Output:
```
Hello from Von!
```

---

## 3. How the Compiler Works

When you run a `.von` file, the source code passes through a **4-stage pipeline** before anything executes.

```
Source Code (.von file)
        │
        ▼
┌───────────────┐
│   1. LEXER    │  lexer.py
│  (Tokenizer)  │
└───────────────┘
        │  Token stream
        ▼
┌───────────────┐
│   2. PARSER   │  parser.py
│  (AST Builder)│
└───────────────┘
        │  Abstract Syntax Tree (AST)
        ▼
┌───────────────────┐
│  3. AST NODES     │  ast_nodes.py
│  (Data Structures)│
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  4. INTERPRETER   │  interpreter.py
│  (Tree Walker)    │
└───────────────────┘
        │
        ▼
     Output
```

---

### Stage 1 — Lexer (`lexer.py`)

The Lexer reads the raw source text character by character and groups characters into **tokens** — the smallest meaningful units of the language.

For example, this Von code:
```
x = 10 + 5
```
Becomes this token stream:
```
IDENTIFIER  'x'
EQUAL       '='
NUMBER      '10'
PLUS        '+'
NUMBER      '5'
NEWLINE
```

The Lexer also handles **indentation** using a stack. When a line is more indented than the previous one, it emits a synthetic `INDENT` token. When indentation decreases, it emits one or more `DEDENT` tokens. This is how Von knows where blocks begin and end without curly braces.

```
def add(a, b):       ← INDENT emitted before next line
    return a + b     ← inside the block
                     ← DEDENT emitted when indentation drops
```

**Key token types:**

| Token       | Example         |
|-------------|-----------------|
| NUMBER      | `42`, `3.14`    |
| STRING      | `"hello"`       |
| IDENTIFIER  | `x`, `result`   |
| KEYWORD     | `if`, `def`, `for` |
| OPERATOR    | `+`, `==`, `<=` |
| INDENT      | (synthetic)     |
| DEDENT      | (synthetic)     |
| NEWLINE     | end of statement|
| EOF         | end of file     |

---

### Stage 2 — Parser (`parser.py`)

The Parser takes the flat token stream and builds a tree structure called an **Abstract Syntax Tree (AST)**. Each node in the tree represents a grammatical construct.

The parser uses **recursive descent** — each grammar rule in the language maps directly to a Python method:

| Grammar Rule   | Parser Method   |
|----------------|-----------------|
| `expression`   | `_expr()`       |
| `term`         | `_term()`       |
| `factor`       | `_factor()`     |
| `if_stmt`      | `_if_stmt()`    |
| `func_def`     | `_func_def()`   |
| `for_stmt`     | `_for_stmt()`   |

Operator precedence is handled naturally by the call hierarchy:

```
_expr → _or → _and → _eq → _cmp → _term → _factor → _unary → _primary
```

Lower in the chain = higher precedence. So `*` binds tighter than `+`, which binds tighter than `==`.

Example — parsing `2 + 3 * 4` produces this tree:
```
BinaryOp('+')
├── Number(2)
└── BinaryOp('*')
    ├── Number(3)
    └── Number(4)
```

---

### Stage 3 — AST Nodes (`ast_nodes.py`)

Every construct in Von has a corresponding Python dataclass. These are the building blocks of the AST.

| Node          | Represents                    |
|---------------|-------------------------------|
| `Number`      | A numeric literal `42`        |
| `String`      | A string literal `"hi"`       |
| `Identifier`  | A variable name `x`           |
| `BinaryOp`    | `a + b`, `x == y`             |
| `UnaryOp`     | `-x`, `not flag`              |
| `Assignment`  | `x = 10`                      |
| `FunctionCall`| `sqrt(16)`                    |
| `MethodCall`  | `nums.length()`               |
| `ListLiteral` | `[1, 2, 3]`                   |
| `IndexAccess` | `nums[0]`                     |
| `IndexAssign` | `nums[0] = 99`                |
| `IfStmt`      | `if / elif / else`            |
| `WhileStmt`   | `while` loop                  |
| `ForStmt`     | `for` loop                    |
| `FuncDef`     | `def` function definition     |
| `ClassDef`    | `class` definition            |
| `ReturnStmt`  | `return` statement            |
| `BreakStmt`   | `break`                       |
| `ContinueStmt`| `continue`                    |

---

### Stage 4 — Interpreter (`interpreter.py`)

The Interpreter walks the AST recursively and **executes** each node. It uses two core methods:

- `_exec(node, env)` — executes statements (assignments, loops, function defs)
- `_eval(node, env)` — evaluates expressions and returns a value

**Environment** is a scoped variable store. Each function call or block creates a new child environment that can read from its parent but writes locally. This is how variable scoping works.

```
Global Env
└── Function Env (when def is called)
    └── Block Env (inside if/while/for)
```

Control flow signals (`return`, `break`, `continue`) are implemented as Python exceptions that unwind the call stack cleanly.

---

## 4. Language Guide

### Variables

Assign a value with `=`. No type declaration needed.

```
x = 10
name = "Alice"
pi_approx = 3.14159
```

---

### Data Types

| Type    | Example           |
|---------|-------------------|
| Integer | `42`              |
| Float   | `3.14`            |
| String  | `"hello"`         |
| Boolean | `true`, `false`   |
| Nil     | `nil`             |
| List    | `[1, 2, 3]`       |

Von uses **weak typing** — types coerce automatically in operations:
```
result = "Value: " + str(42)   # "Value: 42"
```

---

### Operators

**Arithmetic**
```
a + b    # addition
a - b    # subtraction
a * b    # multiplication
a / b    # division (always returns float)
a % b    # modulo (remainder)
```

**Comparison**
```
a == b   # equal
a != b   # not equal
a < b    # less than
a > b    # greater than
a <= b   # less than or equal
a >= b   # greater than or equal
```

**Logical**
```
a and b  # both true
a or b   # either true
not a    # invert
```

**Operator Precedence** (highest to lowest):
```
1. - + not        (unary)
2. * / %
3. + -
4. < > <= >=
5. == !=
6. and
7. or
```

---

### Strings

```
greeting = "Hello, World!"
name = "Von"

# Concatenation
message = "Hello, " + name

# String methods
print(greeting.upper())    # HELLO, WORLD!
print(greeting.lower())    # hello, world!
print(greeting.length())   # 13

# Convert to string
x = 42
print("x is " + str(x))
```

---

### Lists

```
# Create a list
nums = [10, 20, 30, 40, 50]

# Access by index (zero-based)
print(nums[0])    # 10
print(nums[2])    # 30

# Update by index
nums[0] = 99

# List methods
print(nums.length())   # 5
print(nums.sum())      # 239
print(nums.max())      # 99
print(nums.min())      # 20
sorted = nums.sort()   # returns a new sorted list
nums.append(60)        # add to end
last = nums.pop()      # remove and return last item

# Concatenate two lists
a = [1, 2, 3]
b = [4, 5, 6]
c = a + b              # [1, 2, 3, 4, 5, 6]
```

---

### Conditionals

```
score = 85

if score >= 90:
    print("A")
elif score >= 75:
    print("B")
elif score >= 60:
    print("C")
else:
    print("F")
```

Conditions can use any expression. A value is **falsy** if it is `nil`, `false`, `0`, or an empty list. Everything else is truthy.

---

### While Loop

```
i = 1
while i <= 5:
    print(i)
    i = i + 1
```

Use `break` to exit early, `continue` to skip to the next iteration:

```
i = 0
while i < 10:
    i = i + 1
    if i == 3:
        continue    # skip 3
    if i == 7:
        break       # stop at 7
    print(i)
```

---

### For Loop

Iterate over a range or a list:

```
# range(stop)
for i in range(5):
    print(i)        # 0 1 2 3 4

# range(start, stop)
for i in range(1, 6):
    print(i)        # 1 2 3 4 5

# range(start, stop, step)
for i in range(0, 10, 2):
    print(i)        # 0 2 4 6 8

# iterate a list
scores = [85, 92, 78]
for s in scores:
    print(s)
```

---

### Functions

```
def greet(name):
    print("Hello, " + name)

greet("Alice")
```

Functions can return values:

```
def add(a, b):
    return a + b

result = add(10, 5)
print(result)    # 15
```

Functions can call other functions:

```
def square(x):
    return x * x

def sum_of_squares(a, b):
    return square(a) + square(b)

print(sum_of_squares(3, 4))    # 25
```

Recursive functions work too:

```
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print(factorial(6))    # 720
```

---

### Classes

```
class Circle:
    def init(self, radius):
        self.radius = radius

    def area(self):
        return pi * self.radius * self.radius

    def perimeter(self):
        return 2 * pi * self.radius


c = Circle(5)
print(round(c.area(), 2))        # 78.54
print(round(c.perimeter(), 2))   # 31.42
```

- `init` is the constructor, called automatically when you create an instance
- `self` refers to the current instance
- Access instance fields with `self.fieldname`

---

### User Input

```
name = input("Enter your name: ")
age  = num(input("Enter your age: "))

print("Hello, " + name)
print("Next year you will be " + str(age + 1))
```

`input()` always returns a string. Use `num()` to convert to a number.

---

## 5. Built-in Reference

### I/O
| Function       | Description                        |
|----------------|------------------------------------|
| `print(x)`     | Print value to screen              |
| `input(prompt)`| Read a line of text from the user  |

### Type Conversion
| Function  | Description                        |
|-----------|------------------------------------|
| `num(x)`  | Convert string to number           |
| `str(x)`  | Convert any value to string        |

### Math
| Function        | Description                          |
|-----------------|--------------------------------------|
| `sqrt(x)`       | Square root                          |
| `abs(x)`        | Absolute value                       |
| `pow(base, exp)`| Exponentiation                       |
| `floor(x)`      | Round down                           |
| `ceil(x)`       | Round up                             |
| `round(x, n)`   | Round to n decimal places            |
| `max(a, b)`     | Larger of two values                 |
| `min(a, b)`     | Smaller of two values                |
| `sin(x)`        | Sine (radians)                       |
| `cos(x)`        | Cosine (radians)                     |
| `tan(x)`        | Tangent (radians)                    |
| `log(x)`        | Natural logarithm                    |
| `log2(x)`       | Base-2 logarithm                     |
| `log10(x)`      | Base-10 logarithm                    |
| `exp(x)`        | e raised to the power x              |

### Lists
| Function          | Description                        |
|-------------------|------------------------------------|
| `range(n)`        | List of integers 0 to n-1          |
| `range(a, b)`     | List of integers a to b-1          |
| `range(a, b, s)`  | List with step s                   |
| `len(lst)`        | Length of list or string           |
| `sum(lst)`        | Sum of all elements                |
| `sort(lst)`       | Return sorted copy of list         |
| `append(lst, x)`  | Add x to end of list               |
| `pop(lst)`        | Remove and return last element     |

### Constants
| Name  | Value                  |
|-------|------------------------|
| `pi`  | 3.141592653589793      |
| `e`   | 2.718281828459045      |
| `tau` | 6.283185307179586      |
| `true`| Boolean true           |
| `false`| Boolean false         |
| `nil` | No value               |

---

## 6. Error Messages

Von reports three types of errors, all with line numbers:

**LexerError** — invalid character in source
```
[LexerError] Line 3, Col 5: Unexpected character '@'
  --> x = @10
          ^
```

**ParseError** — code doesn't match grammar
```
[ParseError] Line 7, Col 1: Expected ':' (got 'print')
  --> if x > 0
      ^
```

**RuntimeError** — something went wrong during execution
```
[RuntimeError] Line 12: Division by zero
  --> result = a / b
               ^
```

---

## Quick Reference Card

```
# Variable
x = 42

# Condition
if x > 0:
    print("positive")
elif x == 0:
    print("zero")
else:
    print("negative")

# While loop
while x > 0:
    x = x - 1

# For loop
for i in range(10):
    print(i)

# Function
def add(a, b):
    return a + b

# List
nums = [1, 2, 3]
nums.append(4)
print(nums[0])

# Class
class Point:
    def init(self, x, y):
        self.x = x
        self.y = y
    def distance(self):
        return sqrt(self.x * self.x + self.y * self.y)

p = Point(3, 4)
print(p.distance())    # 5

# Built-ins
print(sqrt(16))        # 4
print(round(pi, 2))    # 3.14
print(sin(pi / 2))     # 1
```
