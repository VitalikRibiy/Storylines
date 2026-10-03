"""Minimal parser for Lua table literals (as used in QuestieDB data files)."""
import re

_TOKEN = re.compile(r"""
    (?P<ws>\s+|--\[\[.*?\]\]|--[^\n]*)
  | (?P<num>-?(?:0x[0-9a-fA-F]+|\d+\.?\d*(?:[eE][-+]?\d+)?|\.\d+))
  | (?P<str>"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op>[{}\[\]=,;])
""", re.S | re.X)

_ESC = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'", "\n": "\n"}


def _unescape(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            if n.isdigit():
                m = re.match(r"\d{1,3}", s[i + 1:])
                out.append(chr(int(m.group())))
                i += 1 + len(m.group())
                continue
            out.append(_ESC.get(n, n))
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _tokens(text):
    pos = 0
    n = len(text)
    while pos < n:
        m = _TOKEN.match(text, pos)
        if not m:
            raise ValueError("Unexpected input at %d: %r" % (pos, text[pos:pos + 40]))
        pos = m.end()
        kind = m.lastgroup
        if kind == "ws":
            continue
        val = m.group(kind)
        if kind == "num":
            val = int(val, 16) if val.lower().startswith(("0x", "-0x")) else (float(val) if any(c in val for c in ".eE") else int(val))
        elif kind == "str":
            val = _unescape(val[1:-1])
        yield kind, val


class _Parser:
    def __init__(self, text):
        self.toks = list(_tokens(text))
        self.i = 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else (None, None)

    def take(self, op=None):
        tok = self.toks[self.i]
        if op is not None and tok != ("op", op):
            raise ValueError("Expected %r, got %r at token %d" % (op, tok, self.i))
        self.i += 1
        return tok

    def value(self):
        kind, val = self.take()
        if kind in ("num", "str"):
            return val
        if kind == "name":
            if val == "nil":
                return None
            if val in ("true", "false"):
                return val == "true"
            raise ValueError("Unsupported identifier %r" % val)
        if (kind, val) == ("op", "{"):
            return self.table()
        raise ValueError("Unexpected token %r" % ((kind, val),))

    def table(self):
        result = {}
        idx = 1
        while True:
            if self.peek() == ("op", "}"):
                self.take()
                return result
            if self.peek() == ("op", "["):
                self.take()
                key = self.value()
                self.take("]")
                self.take("=")
                v = self.value()
            elif self.peek()[0] == "name" and self.toks[self.i + 1] == ("op", "="):
                key = self.take()[1]
                self.take("=")
                v = self.value()
            else:
                key = idx
                idx += 1
                v = self.value()
            if v is not None:
                result[key] = v
            if self.peek() in (("op", ","), ("op", ";")):
                self.take()


def parse(text):
    """Parse a single Lua table literal ('{...}' optionally prefixed by 'return')."""
    text = text.strip()
    if text.startswith("return"):
        text = text[len("return"):]
    p = _Parser(text)
    p.take("{")
    return p.table()


def as_list(t):
    """Convert a positional Lua table (dict 1..n) into a Python list; None stays None."""
    if t is None:
        return None
    if isinstance(t, dict):
        n = max([k for k in t if isinstance(k, int)] or [0])
        return [t.get(i) for i in range(1, n + 1)]
    return t


def extract_long_strings(text):
    """Return {assignment target: contents} for `X = [[...]]` / `X = [=[...]=]` blocks."""
    out = {}
    for m in re.finditer(r"([A-Za-z_][\w.]*)\s*=\s*\[(=*)\[(.*?)\]\2\]", text, re.S):
        out[m.group(1)] = m.group(3)
    return out
