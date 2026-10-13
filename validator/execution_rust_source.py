"""Locate Rust assertion macro invocations and their enclosing functions (stdlib only).

The trusted Cargo runner and the acceptance mapping both need the exact source
identity of `assert!`, `assert_eq!`, `assert_ne!` and `assert_matches!` calls.
This lexer understands comments, every string/char literal form and lifetimes,
so text inside literals or comments is never mistaken for an assertion.
"""

# @spec FR-004: Rust assertion identity — .specs/features/085-cargo-execution-runner/spec.md#fr-004

from __future__ import annotations

import re
from dataclasses import dataclass

ASSERTION_MACROS = frozenset({"assert", "assert_eq", "assert_ne", "assert_matches"})
_OPEN = {"(": ")", "[": "]", "{": "}"}
_CLOSE = frozenset(_OPEN.values())
_RAW_STRING = re.compile(r'(?:br|cr|r)(#*)"')
_PREFIXED_STRING = re.compile(r'(?:b|c)"')


@dataclass(frozen=True)
class RustAssertion:
    """One assertion invocation with 1-based positions (columns in chars and bytes)."""

    line: int
    column: int
    byte_column: int
    end_line: int
    text: str
    function: str | None


@dataclass(frozen=True)
class _Token:
    kind: str  # "ident", "punct" or "literal"
    value: str
    start: int
    end: int


def rust_assertions(source: str) -> list[RustAssertion]:
    """Return every assertion macro invocation in source order."""
    tokens = _tokens(source)
    functions = _function_at_token(tokens)
    starts = _line_starts(source)
    found: list[RustAssertion] = []
    for index in range(len(tokens)):
        if not _is_assertion(tokens, index):
            continue
        first = _path_start(tokens, index)
        close = _matching(tokens, index + 2)
        if close is None:
            continue
        begin, end = tokens[first].start, tokens[close].end
        line, column = _position(starts, begin)
        line_text = source[starts[line - 1] : begin]
        found.append(
            RustAssertion(
                line=line,
                column=column,
                byte_column=len(line_text.encode()) + 1,
                end_line=_position(starts, end - 1)[0],
                text=source[begin:end],
                function=functions[index],
            )
        )
    return found


def _is_assertion(tokens: list[_Token], index: int) -> bool:
    token = tokens[index]
    return (
        token.kind == "ident"
        and token.value in ASSERTION_MACROS
        and index + 2 < len(tokens)
        and tokens[index + 1].value == "!"
        and tokens[index + 2].value in _OPEN
    )


def _path_start(tokens: list[_Token], index: int) -> int:
    """Include a qualifying path such as `std::assert_eq` in the invocation span."""
    first = index
    while first >= 2 and tokens[first - 1].value == "::" and tokens[first - 2].kind == "ident":
        first -= 2
    if first >= 1 and tokens[first - 1].value == "::":
        first -= 1  # Leading `::std::assert!`.
    return first


def _matching(tokens: list[_Token], open_index: int) -> int | None:
    depth = 0
    for index in range(open_index, len(tokens)):
        value = tokens[index].value
        if tokens[index].kind != "punct":
            continue
        if value in _OPEN:
            depth += 1
        elif value in _CLOSE:
            depth -= 1
            if depth == 0:
                return index
    return None


def _function_at_token(tokens: list[_Token]) -> list[str | None]:
    """Name the innermost `fn` body enclosing each token."""
    stack: list[str | None] = []
    pending: tuple[str, int] | None = None
    result: list[str | None] = []
    for index, token in enumerate(tokens):
        result.append(next((name for name in reversed(stack) if name), None))
        if token.kind == "ident" and token.value == "fn" and index + 1 < len(tokens):
            name = tokens[index + 1]
            if name.kind == "ident":
                pending = (name.value.removeprefix("r#"), len(stack))
            continue
        if token.kind != "punct":
            continue
        if token.value in _OPEN:
            is_body = token.value == "{" and pending is not None and pending[1] == len(stack)
            stack.append(pending[0] if is_body and pending else None)
            if is_body:
                pending = None
        elif token.value in _CLOSE and stack:
            stack.pop()
        elif token.value == ";" and pending is not None and pending[1] == len(stack):
            pending = None  # Body-less declaration such as a trait method.
    return result


def _line_starts(source: str) -> list[int]:
    starts = [0]
    starts.extend(match.end() for match in re.finditer("\n", source))
    return starts


def _position(starts: list[int], offset: int) -> tuple[int, int]:
    low, high = 0, len(starts) - 1
    while low < high:
        middle = (low + high + 1) // 2
        if starts[middle] <= offset:
            low = middle
        else:
            high = middle - 1
    return low + 1, offset - starts[low] + 1


def _tokens(source: str) -> list[_Token]:
    tokens: list[_Token] = []
    index = 0
    while index < len(source):
        end, kind = _scan(source, index)
        if kind:
            tokens.append(_Token(kind, source[index:end], index, end))
        index = end
    return tokens


def _scan(source: str, index: int) -> tuple[int, str]:
    """Return the end of the lexeme at index and its kind ("" for trivia)."""
    char = source[index]
    if char.isspace():
        return index + 1, ""
    if source.startswith("//", index):
        newline = source.find("\n", index)
        return (len(source) if newline < 0 else newline), ""
    if source.startswith("/*", index):
        return _block_comment(source, index), ""
    literal = _literal(source, index)
    if literal is not None:
        return literal, "literal"
    if char == "'":
        return _quote(source, index)
    if source.startswith("r#", index) and _ident_char(source, index + 2):
        return _identifier(source, index + 2), "ident"
    if char.isalpha() or char == "_":
        return _identifier(source, index), "ident"
    if char.isdigit():
        return _identifier(source, index), "literal"
    if source.startswith("::", index):
        return index + 2, "punct"
    return index + 1, "punct"


def _ident_char(source: str, index: int) -> bool:
    return index < len(source) and (source[index].isalnum() or source[index] == "_")


def _identifier(source: str, index: int) -> int:
    while _ident_char(source, index):
        index += 1
    return index


def _block_comment(source: str, index: int) -> int:
    depth, index = 1, index + 2
    while index < len(source) and depth:
        if source.startswith("/*", index):
            depth, index = depth + 1, index + 2
        elif source.startswith("*/", index):
            depth, index = depth - 1, index + 2
        else:
            index += 1
    return index


def _literal(source: str, index: int) -> int | None:
    """Scan string, raw string and byte/C string literals starting at index."""
    raw = _RAW_STRING.match(source, index)
    if raw:
        terminator = '"' + raw.group(1)
        end = source.find(terminator, raw.end())
        return len(source) if end < 0 else end + len(terminator)
    if source[index] == '"' or _PREFIXED_STRING.match(source, index):
        return _escaped(source, source.index('"', index) + 1, '"')
    if source.startswith("b'", index):
        return _escaped(source, index + 2, "'")
    return None


def _escaped(source: str, index: int, terminator: str) -> int:
    while index < len(source):
        if source[index] == "\\":
            index += 2
        elif source[index] == terminator:
            return index + 1
        else:
            index += 1
    return index


def _quote(source: str, index: int) -> tuple[int, str]:
    """Distinguish a char literal from a lifetime or loop label."""
    if source.startswith("'\\", index):
        return _escaped(source, index + 1, "'"), "literal"
    if index + 2 < len(source) and source[index + 2] == "'":
        return index + 3, "literal"
    return _identifier(source, index + 1), "ident"
