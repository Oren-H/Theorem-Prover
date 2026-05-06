"""
Tokeniser and recursive-descent parser for the PA REPL.

Grammar
-------
command_line  ::= expr EOF
expr          ::= call_expr
                | paren_expr
                | int_expr
                | fact_ref
call_expr     ::= NAME '(' arg_list? ')' plusplus*
paren_expr    ::= '(' expr ')' plusplus*
int_expr      ::= INT plusplus*
fact_ref      ::= '#' INT plusplus*
arg_list      ::= expr (',' expr)*
plusplus      ::= '++'

Input syntax notes
------------------
- Integer literals are auto-converted to Num: 0 → Zero(), 3 → Succ(Succ(Succ(Zero())))
- '++' is a postfix successor operator:  0++ → Succ(Zero()),  (0++)++ → Succ(Succ(Zero()))
- '#N' references fact N (1-indexed) from the current session fact_list.
- Nested command calls are supported and each nested call also records a fact.
"""
from __future__ import annotations
from typing import Any

from .types import Zero, Succ, Var, Num
from .errors import InvalidCommand, InvalidInput
from .commands import COMMANDS, fact_list


# ---------------------------------------------------------------------------
# Tokeniser
# ---------------------------------------------------------------------------

class Token:
    __slots__ = ("kind", "value")

    def __init__(self, kind: str, value: Any = None):
        self.kind = kind
        self.value = value

    def __repr__(self) -> str:
        return f"Token({self.kind!r}, {self.value!r})" if self.value is not None else f"Token({self.kind!r})"


def tokenise(src: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    n = len(src)
    while i < n:
        ch = src[i]
        if ch.isspace():
            i += 1
        elif ch == '+':
            if i + 1 < n and src[i + 1] == '+':
                tokens.append(Token("PLUSPLUS"))
                i += 2
            else:
                tokens.append(Token("PLUS"))
                i += 1
        elif ch.isdigit():
            j = i
            while j < n and src[j].isdigit():
                j += 1
            tokens.append(Token("INT", int(src[i:j])))
            i = j
        elif ch.isalpha() or ch == '_':
            j = i
            while j < n and (src[j].isalnum() or src[j] == '_'):
                j += 1
            tokens.append(Token("NAME", src[i:j]))
            i = j
        elif ch == '(':
            tokens.append(Token("LPAREN"))
            i += 1
        elif ch == ')':
            tokens.append(Token("RPAREN"))
            i += 1
        elif ch == ',':
            tokens.append(Token("COMMA"))
            i += 1
        elif ch == '#':
            i += 1
            j = i
            while j < n and src[j].isdigit():
                j += 1
            if j == i:
                raise InvalidInput("Expected a number after '#'")
            tokens.append(Token("FACT", int(src[i:j])))
            i = j
        else:
            raise InvalidInput(f"Unexpected character: {ch!r}")
    tokens.append(Token("EOF"))
    return tokens


# ---------------------------------------------------------------------------
# Helpers for int → Num conversion
# ---------------------------------------------------------------------------

def _int_to_num(n: int) -> Num:
    if n < 0:
        raise InvalidInput(f"Expected non-negative integer, got {n}")
    result: Num = Zero()
    for _ in range(n):
        result = Succ(result)
    return result


# ---------------------------------------------------------------------------
# Recursive-descent parser
# ---------------------------------------------------------------------------

class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    # --- low-level helpers --------------------------------------------------

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def consume(self, expected_kind: str | None = None) -> Token:
        tok = self.peek()
        if expected_kind is not None and tok.kind != expected_kind:
            raise InvalidInput(
                f"Expected {expected_kind!r} but got {tok.kind!r}"
                + (f" ({tok.value!r})" if tok.value is not None else "")
            )
        self.pos += 1
        return tok

    def _apply_plusplus(self, value: Any) -> Any:
        """Consume all trailing '++' tokens and wrap value in Succ."""
        while self.peek().kind == "PLUSPLUS":
            self.consume()
            if not isinstance(value, (Zero, Succ, Var)):
                raise InvalidInput(
                    "Cannot apply '++' to a non-Num value"
                )
            value = Succ(value)
        return value

    # --- grammar rules -------------------------------------------------------

    def parse_command_line(self) -> Any:
        result = self.parse_expr()
        self.consume("EOF")
        return result

    def parse_expr(self) -> Any:
        tok = self.peek()

        if tok.kind == "INT":
            self.consume()
            num = _int_to_num(tok.value)
            return self._apply_plusplus(num)

        if tok.kind == "LPAREN":
            self.consume()
            inner = self.parse_expr()
            self.consume("RPAREN")
            return self._apply_plusplus(inner)

        if tok.kind == "FACT":
            self.consume()
            idx = tok.value
            if idx < 1 or idx > len(fact_list):
                raise InvalidInput(
                    f"Fact #{idx} does not exist "
                    f"(session has {len(fact_list)} fact(s))"
                )
            value = fact_list[idx - 1]
            return self._apply_plusplus(value)

        if tok.kind == "NAME":
            name = tok.value
            self.consume()

            # Bare name not followed by '(' — treat as a term variable.
            if self.peek().kind != "LPAREN":
                if name in COMMANDS:
                    raise InvalidInput(
                        f"{name!r} is a command — call it with parentheses: {name}(...)"
                    )
                return self._apply_plusplus(Var(name))

            # Named command followed by '('.
            if name not in COMMANDS:
                raise InvalidCommand(
                    f"Unknown command: {name!r}\n"
                    f"Valid commands: {', '.join(COMMANDS)}"
                )
            fn, arity = COMMANDS[name]
            self.consume("LPAREN")
            args: list[Any] = []
            if self.peek().kind != "RPAREN":
                args.append(self.parse_expr())
                while self.peek().kind == "COMMA":
                    self.consume()
                    args.append(self.parse_expr())
            self.consume("RPAREN")
            if len(args) != arity:
                raise InvalidInput(
                    f"{name}() expects {arity} argument(s), got {len(args)}"
                )
            result = fn(*args)
            return self._apply_plusplus(result)

        raise InvalidInput(
            f"Unexpected token {tok.kind!r}"
            + (f" ({tok.value!r})" if tok.value is not None else "")
        )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse_and_run(src: str) -> Any:
    """
    Tokenise and evaluate a command string.
    Returns the top-level result (a Prop or Num).
    Nested command calls each record a fact as a side effect.
    Raises InvalidCommand, InvalidInput, or TypeMismatch on errors.
    """
    src = src.strip()
    if not src:
        raise InvalidInput("Empty input")
    tokens = tokenise(src)
    parser = Parser(tokens)
    return parser.parse_command_line()
