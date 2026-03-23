# Von Language — Official Documentation
> Version 2.0.0

---

## Table of Contents

1. What is Von?
2. How to Run Von Programs
3. How the Compiler Works
4. Language Guide
5. Built-in Reference
6. Error Messages
7. Quick Reference Card

---

## 1. What is Von?

Von is a dynamically-typed, object-oriented programming language designed for mathematical computing.
It uses Python-like indentation syntax with no curly braces and no semicolons.
Von programs are stored in files with the .von extension and executed using von.py.

---

## 2. How to Run Von Programs

Run a file:
    python von.py myprogram.von

Interactive REPL:
    python von.py

Dump bytecode:
    python von.py --dump myprogram.von

Example hello.von:
    output("Hello from Von!")

Run:
    python von.py hello.von

---

## 3. How the Compiler Works

The Von compiler has 6 stages:

    Source Code (.von)
         |
    1. LEXER        lexer.py       Breaks source into tokens
         |
    2. PARSER       parser.py      Builds Abstract Syntax Tree (AST)
         |
    3. SEMANTIC     semantic.py    Validates names, scopes, control flow
         |
    4. CODE GEN     codegen.py     Compiles AST to bytecode instructions
         |
    5+6. VM         vm.py          Stack-based virtual machine executes bytecode
         |
       Output


Stage 1 - Lexer (lexer.py)
Reads source text and produces tokens. Uses a stack-based indentation tracker
to emit synthetic INDENT and DEDENT tokens so Von knows where blocks begin/end.

    x = 10 + 5
    becomes:
    IDENTIFIER 'x'  EQUAL '='  NUMBER '10'  PLUS '+'  NUMBER '5'  NEWLINE


Stage 2 - Parser (parser.py)
Builds an AST using recursive descent. Each grammar rule maps to a method.
Operator precedence is handled by the call hierarchy.


Stage 3 - Semantic Analyser (semantic.py)
Validates the AST before any code runs:
  - All variables declared before use
  - return only inside functions
  - break/continue only inside loops
  - Warns about unused function parameters


Stage 4 - Code Generator (codegen.py)
Compiles the AST into bytecode stored in Chunk objects.

    output(2 + 3)  compiles to:
    0000  LOAD_CONST   2
    0001  LOAD_CONST   3
    0002  BINARY_OP    '+'
    0003  CALL         ('output', 1)
    0004  POP

Key opcodes:
    LOAD_CONST      Push a constant
    LOAD_NAME       Push a variable value
    STORE_NAME      Pop and store into variable
    BINARY_OP       Apply arithmetic/logic operator
    CALL            Call a function
    CALL_METHOD     Call a method on an object
    LOAD_ATTR       Read object field (self.x)
    STORE_ATTR      Write object field (self.x = v)
    JUMP            Unconditional jump
    JUMP_IF_FALSE   Conditional jump
    FOR_ITER        Advance for-loop iterator
    BUILD_LIST      Build a list from stack items
    RETURN          Return value from function


Stage 5+6 - Virtual Machine (vm.py)
Stack-based VM that executes bytecode. Maintains:
  - Operand stack for intermediate values
  - Call stack of frames (one per function call)
  - Each frame has its own local variable dict


AST Nodes (ast_nodes.py)
Every language construct maps to a Python dataclass:
    Number, String, Identifier, BinaryOp, UnaryOp
    Assignment, AttributeAccess, AttributeAssign
    FunctionCall, MethodCall, ListLiteral
    IndexAccess, IndexAssign
    IfStmt, WhileStmt, ForStmt
    FuncDef, ClassDef
    ReturnStmt, BreakStmt, ContinueStmt

---

## 4. Language Guide

### Variables
    x = 10
    name = "Alice"
    pi_approx = 3.14159


### Data Types
    Integer   42
    Float     3.14
    String    "hello"
    Boolean   true, false
    Nil       nil
    List      [1, 2, 3]


### Output
    output("Hello, World!")
    output(42)
    output("Result: " + str(100))


### User Input
    name = input("Enter your name: ")
    age  = num(input("Enter your age: "))
    output("Hello, " + name)
    output("Next year: " + str(age + 1))

    input() always returns a string. Use num() to convert to a number.


### Operators

Arithmetic:   a + b   a - b   a * b   a / b   a % b
Comparison:   a == b  a != b  a < b   a > b   a <= b  a >= b
Logical:      a and b   a or b   not a

Precedence (highest to lowest):
    - + not   (unary)
    * / %
    + -
    < > <= >=
    == !=
    and
    or


### Strings
    msg = "Hello, Von!"
    output(msg.upper())     # HELLO, VON!
    output(msg.lower())     # hello, von!
    output(msg.length())    # 11
    output("Hi " + "there")
    output("x = " + str(42))


### Lists
    nums = [10, 20, 30, 40, 50]
    output(nums[0])        # 10
    nums[0] = 99           # update by index
    output(nums.length())  # 5
    output(nums.sum())     # 239
    output(nums.max())     # 99
    output(nums.min())     # 20
    output(nums.sort())    # sorted copy
    nums.append(60)
    last = nums.pop()
    a = [1, 2] + [3, 4]   # [1, 2, 3, 4]


### Conditionals
    score = 85
    if score >= 90:
        output("A")
    elif score >= 75:
        output("B")
    elif score >= 60:
        output("C")
    else:
        output("F")


### While Loop
    i = 1
    while i <= 5:
        output(i)
        i = i + 1

    # break and continue
    i = 0
    while i < 10:
        i = i + 1
        if i == 3:
            continue
        if i == 7:
            break
        output(i)


### For Loop
    for i in range(5):         # 0 1 2 3 4
        output(i)

    for i in range(1, 6):      # 1 2 3 4 5
        output(i)

    for i in range(0, 10, 2):  # 0 2 4 6 8
        output(i)

    scores = [85, 92, 78]
    for s in scores:
        output(s)


### Functions
    def add(a, b):
        return a + b

    output(add(10, 5))    # 15

    # Recursive
    def factorial(n):
        if n <= 1:
            return 1
        return n * factorial(n - 1)

    output(factorial(6))  # 720


### Classes
    class Rectangle:
        def init(self, width, height):
            self.width = width
            self.height = height

        def area(self):
            return self.width * self.height

        def describe(self):
            output("Area: " + str(self.area()))

    r = Rectangle(6, 4)
    r.describe()

    Rules:
    - init is the constructor, called automatically on creation
    - self refers to the current instance
    - self.field = value  sets an instance field
    - self.field          reads an instance field

---

## 5. Built-in Reference

I/O:
    output(x)          Print value to screen
    input(prompt)      Read a line of text from the user

Type Conversion:
    num(x)             Convert string to number
    str(x)             Convert any value to string

Math:
    sqrt(x)            Square root
    abs(x)             Absolute value
    pow(base, exp)     Exponentiation
    floor(x)           Round down
    ceil(x)            Round up
    round(x, n)        Round to n decimal places
    max(a, b)          Larger of two values
    min(a, b)          Smaller of two values
    sin(x)             Sine (radians)
    cos(x)             Cosine (radians)
    tan(x)             Tangent (radians)
    log(x)             Natural logarithm
    log2(x)            Base-2 logarithm
    log10(x)           Base-10 logarithm
    exp(x)             e raised to the power x

Lists:
    range(n)           List 0 to n-1
    range(a, b)        List a to b-1
    range(a, b, step)  List with step
    len(lst)           Length of list or string
    sum(lst)           Sum of all elements
    sort(lst)          Return sorted copy
    append(lst, x)     Add x to end
    pop(lst)           Remove and return last element

Constants:
    pi     3.141592653589793
    e      2.718281828459045
    tau    6.283185307179586
    true   Boolean true
    false  Boolean false
    nil    No value

---

## 6. Error Messages

LexerError - invalid character:
    [LexerError] Line 3, Col 5: Unexpected character '@'
      --> x = @10
              ^

ParseError - syntax error:
    [ParseError] Line 7, Col 1: Expected ':'
      --> if x > 0
          ^

SemanticError - undefined name or scope violation:
    [SemanticError] Line 5: Undefined variable 'total'
      --> output(total)
          ^

RuntimeError - error during execution:
    [RuntimeError] Division by zero

---

## 7. Quick Reference Card

    # Variable
    x = 42

    # Output
    output("Hello!")
    output("x = " + str(x))

    # Input
    name = input("Name: ")
    n = num(input("Number: "))

    # Condition
    if x > 0:
        output("positive")
    elif x == 0:
        output("zero")
    else:
        output("negative")

    # While loop
    while x > 0:
        x = x - 1

    # For loop
    for i in range(10):
        output(i)

    # Function
    def add(a, b):
        return a + b

    # List
    nums = [1, 2, 3]
    nums.append(4)
    output(nums.sum())

    # Class
    class Circle:
        def init(self, r):
            self.r = r
        def area(self):
            return pi * self.r * self.r

    c = Circle(5)
    output(round(c.area(), 2))

    # Math
    output(sqrt(16))
    output(round(pi, 4))
    output(sin(pi / 2))
    output(log10(1000))
