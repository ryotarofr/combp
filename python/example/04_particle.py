"""
combp で書くパーティクル定義 DSL のサンプル。

対応構文:
  - 数値         : 3.14, -2, 30
  - 文字列       : "small_spark"
  - 識別子       : forward, hp
  - 範囲         : 2.0..3.0
  - 関数呼び出し : rgba(1, 0, 0, 1) / gradient(0 -> rgba(...), 1 -> rgba(...))
  - キーワード引数: rate = 30
  - グラデーション: 0.0 -> rgba(1,1,0,1)

例:
    emitter(
      rate = 30,
      life = 2.0..3.0,
      velocity = vec3(0, 5, 0),
      color = gradient(
        0.0 -> rgba(1.0, 1.0, 0.2, 1.0),
        1.0 -> rgba(0.1, 0.1, 0.1, 0.0)
      ),
      on_collide = "small_spark"
    )
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from combp import (
    Combinator, CombinatorResult,
    chain_n, chain_l, chain_r, convert, label, lazy, map_,
    option, or_n, peek, repeat, sep_by, use, err, ok,
)


# ===========================================================================
# Ctx
# ===========================================================================


@dataclass(frozen=True)
class Ctx:
    src: str
    offset: int = 0


# ===========================================================================
# プリミティブ
# ===========================================================================


def satisfy(pred, desc: str) -> Combinator[Ctx, str]:
    def _f(c: Ctx) -> CombinatorResult[Ctx, str]:
        if c.offset >= len(c.src):
            return err(c, f"{desc} が必要ですが EOF")
        ch = c.src[c.offset]
        if not pred(ch):
            return err(c, f"{desc} が必要ですが '{ch}'")
        return ok(Ctx(c.src, c.offset + 1), ch)
    return _f


def literal(s: str) -> Combinator[Ctx, str]:
    def _f(c: Ctx) -> CombinatorResult[Ctx, str]:
        if c.src.startswith(s, c.offset):
            return ok(Ctx(c.src, c.offset + len(s)), s)
        return err(c, f"'{s}' が必要")
    return _f


ws_char = satisfy(lambda ch: ch in " \t\r\n", "空白")
ws = map_(repeat(ws_char, must=0), lambda _: None)


def tok(p: Combinator[Ctx, Any]) -> Combinator[Ctx, Any]:
    """トークン + 後続空白スキップ。"""
    return chain_l(p, ws)


def sym(s: str) -> Combinator[Ctx, str]:
    return tok(literal(s))


# ===========================================================================
# 数値 / 識別子 / 文字列
# ===========================================================================

digit = satisfy(str.isdigit, "数字")
alpha = satisfy(lambda ch: ch.isalpha() or ch == "_", "英字")
alnum = satisfy(lambda ch: ch.isalnum() or ch == "_", "英数字")


def _number(c: Ctx) -> CombinatorResult[Ctx, float]:
    start = c.offset
    cur = c
    sign = 1
    if cur.offset < len(cur.src) and cur.src[cur.offset] == "-":
        sign = -1
        cur = Ctx(cur.src, cur.offset + 1)
    int_part = repeat(digit, must=1)(cur)
    if not int_part.ok:
        return err(c, "数値が必要")
    cur = int_part.context
    has_frac = False
    if cur.offset < len(cur.src) and cur.src[cur.offset] == ".":
        # ".." (範囲) と区別するため、次の文字も "." なら小数として扱わない
        if cur.offset + 1 < len(cur.src) and cur.src[cur.offset + 1] == ".":
            pass
        else:
            frac = repeat(digit, must=1)(Ctx(cur.src, cur.offset + 1))
            if frac.ok:
                cur = frac.context
                has_frac = True
    text = c.src[start:cur.offset]
    return ok(cur, float(text))


number = tok(_number)


def _ident(c: Ctx) -> CombinatorResult[Ctx, str]:
    first = alpha(c)
    if not first.ok:
        return err(c, "識別子が必要")
    rest = repeat(alnum, must=0)(first.context)
    chars = [first.value] + (rest.value if rest.ok else [])
    end_ctx = rest.context if rest.ok else first.context
    return ok(end_ctx, "".join(chars))


ident = tok(_ident)


def _string(c: Ctx) -> CombinatorResult[Ctx, str]:
    if c.offset >= len(c.src) or c.src[c.offset] != '"':
        return err(c, '"\\"" が必要')
    i = c.offset + 1
    while i < len(c.src) and c.src[i] != '"':
        i += 1
    if i >= len(c.src):
        return err(c, '閉じる "\\"" が見つからない')
    return ok(Ctx(c.src, i + 1), c.src[c.offset + 1:i])


string_lit = tok(_string)


# ===========================================================================
# AST
# ===========================================================================


@dataclass(frozen=True)
class Num:       value: float
@dataclass(frozen=True)
class Str:       value: str
@dataclass(frozen=True)
class Ident:     name: str
@dataclass(frozen=True)
class Range:     lo: "Expr"; hi: "Expr"
@dataclass(frozen=True)
class Call:      name: str; args: tuple["Arg", ...]
@dataclass(frozen=True)
class Stop:      at: "Expr"; value: "Expr"   # gradient stop: 0.0 -> rgba(...)

@dataclass(frozen=True)
class Positional: value: "Expr"
@dataclass(frozen=True)
class Keyword:    name: str; value: "Expr"

Expr = Num | Str | Ident | Range | Call | Stop
Arg = Positional | Keyword


# ===========================================================================
# 文法
# ===========================================================================

expr: Combinator[Ctx, Expr] = lazy(lambda: _expr_impl)

# atom = 数値 | 文字列 | 呼び出し or 識別子
atom: Combinator[Ctx, Expr] = or_n(
    map_(number, lambda v: Num(v)),
    map_(string_lit, lambda v: Str(v)),
    lazy(lambda: _call_or_ident),
)

# 範囲: atom (".." atom)?
def _maybe_range(lo: Expr, rest: Any) -> Expr:
    return Range(lo, rest) if rest is not None else lo

range_or_atom: Combinator[Ctx, Expr] = convert(
    chain_n(atom, option(chain_r(sym(".."), atom))),
    lambda parts, _: _maybe_range(parts[0], parts[1]),
)

# stop: expr "->" expr   (gradient 用。右結合で 1 階層だけ認める)
_expr_impl: Combinator[Ctx, Expr] = convert(
    chain_n(range_or_atom, option(chain_r(sym("->"), lazy(lambda: _expr_impl)))),
    lambda parts, _: Stop(parts[0], parts[1]) if parts[1] is not None else parts[0],
)

# 引数: キーワード引数 or 位置引数
kwarg: Combinator[Ctx, Arg] = convert(
    chain_n(ident, sym("="), expr),
    lambda parts, _: Keyword(parts[0], parts[2]),
)
posarg: Combinator[Ctx, Arg] = map_(expr, lambda e: Positional(e))

arg: Combinator[Ctx, Arg] = or_n(kwarg, posarg)

args: Combinator[Ctx, list[Arg]] = sep_by(arg, sym(","))

# 呼び出し or 識別子
call = convert(
    chain_n(ident, sym("("), args, sym(")")),
    lambda parts, _: Call(parts[0], tuple(parts[2])),
)

_call_or_ident: Combinator[Ctx, Expr] = use(
    peek(ident),
    lambda _name: or_n(call, map_(ident, lambda n: Ident(n))),
)


# EOF チェッカ
def _eof(c: Ctx) -> CombinatorResult[Ctx, None]:
    if c.offset >= len(c.src):
        return ok(c, None)
    return err(c, f"余分な入力: {c.src[c.offset:c.offset+20]!r}")


# トップレベル: 先頭空白 → 式 → EOF
top_parser: Combinator[Ctx, Expr] = chain_l(chain_r(ws, expr), _eof)


# ===========================================================================
# パース結果を pretty-print
# ===========================================================================


def pretty(e: Expr, indent: int = 0) -> str:
    pad = "  " * indent
    match e:
        case Num(v):       return f"{pad}Num({v})"
        case Str(v):       return f"{pad}Str({v!r})"
        case Ident(n):     return f"{pad}Ident({n})"
        case Range(a, b):  return f"{pad}Range(\n{pretty(a, indent+1)},\n{pretty(b, indent+1)}\n{pad})"
        case Stop(a, b):   return f"{pad}Stop(\n{pretty(a, indent+1)},\n{pretty(b, indent+1)}\n{pad})"
        case Call(n, xs):
            inner = ",\n".join(pretty_arg(x, indent+1) for x in xs)
            return f"{pad}Call({n})(\n{inner}\n{pad})"
    return f"{pad}?{e}"


def pretty_arg(a: Arg, indent: int) -> str:
    pad = "  " * indent
    if isinstance(a, Keyword):
        return f"{pad}{a.name} =\n{pretty(a.value, indent+1)}"
    return pretty(a.value, indent)


# ===========================================================================
# 実行
# ===========================================================================


SAMPLE = """
emitter(
  rate     = 30,
  life     = 2.0..3.0,
  velocity = vec3(0, 5, 0),
  color    = gradient(
    0.0 -> rgba(1.0, 1.0, 0.2, 1.0),
    0.5 -> rgba(1.0, 0.3, 0.0, 0.8),
    1.0 -> rgba(0.1, 0.1, 0.1, 0.0)
  ),
  size = curve(
    0.0 -> 0.1,
    0.3 -> 0.5,
    1.0 -> 0.0
  ),
  on_collide = "small_spark"
)
"""


if __name__ == "__main__":
    r = top_parser(Ctx(SAMPLE))
    if not r.ok:
        print("パース失敗:", r.error.message, "at offset", r.error.on.offset)
        raise SystemExit(1)

    print("=== AST ===")
    print(pretty(r.value))

    # 具体的な値の取り出し例
    assert isinstance(r.value, Call) and r.value.name == "emitter"
    kw = {a.name: a.value for a in r.value.args if isinstance(a, Keyword)}

    assert isinstance(kw["rate"], Num) and kw["rate"].value == 30
    assert isinstance(kw["life"], Range)
    assert isinstance(kw["color"], Call) and kw["color"].name == "gradient"
    assert isinstance(kw["on_collide"], Str) and kw["on_collide"].value == "small_spark"

    print("\n✓ パース結果の構造検証 OK")

    # 失敗ケース: エラー位置が出る
    bad = "emitter(rate = , life = 1.0)"
    r2 = top_parser(Ctx(bad))
    print("\n=== エラー例 ===")
    print(f"入力: {bad!r}")
    if not r2.ok:
        e = r2.error
        print(f"  offset={e.on.offset}: {e.message}")
        f = e.furthest
        while f is not None:
            print(f"  furthest@{f.on.offset}: {f.message}")
            f = f.furthest
    else:
        print("  (成功してしまった)", r2.value)
