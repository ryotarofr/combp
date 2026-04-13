"""
combp で書くパーティクル定義 DSL のサンプル。

ゲームエンジンのパーティクルエフェクト（火花、煙、爆発など）を
テキストベースの独自 DSL で定義し、combp パーサーコンビネータで
構文解析して AST に変換する。

─── 対応構文 ───────────────────────────────────────────────

  リテラル:
    - 数値         : 3.14, -2, 30
    - 文字列       : "small_spark"
    - 識別子       : forward, hp

  複合式:
    - 範囲         : 2.0..3.0            （パーティクル寿命などのランダム幅）
    - 関数呼び出し : rgba(1, 0, 0, 1)    （色、ベクトル等の構築）
    - キーワード引数: rate = 30           （名前付きパラメータ）
    - ストップ     : 0.0 -> rgba(1,1,0,1)（グラデーション/カーブのキーフレーム）

─── 文法 (EBNF 風) ────────────────────────────────────────

  expr       = range_or_atom ( "->" expr )?      // stop（右結合）
  range_or_atom = atom ( ".." atom )?             // 範囲
  atom       = NUMBER | STRING | call_or_ident
  call_or_ident = IDENT "(" args ")" | IDENT      // 関数呼び出し or 識別子
  args       = ( arg ( "," arg )* )?
  arg        = IDENT "=" expr | expr              // kwarg or posarg

─── DSL 記述例 ────────────────────────────────────────────

  emitter(
    rate     = 30,                             // 毎秒 30 個放出
    life     = 2.0..3.0,                       // 寿命 2〜3 秒
    velocity = vec3(0, 5, 0),                  // 初速度
    color    = gradient(
      0.0 -> rgba(1.0, 1.0, 0.2, 1.0),        // 黄色から
      1.0 -> rgba(0.1, 0.1, 0.1, 0.0)         // 透明な灰色へ
    ),
    on_collide = "small_spark"                 // 衝突時に発火するサブエフェクト
  )

─── combp の各コンビネータがどこで活きるか ────────────────

  lazy    : expr ↔ call ↔ args ↔ expr の相互再帰を遅延評価で解決
  or_n    : atom の分岐（数値 | 文字列 | 呼び出し/識別子）
  option  : ".." や "->" の省略可能な後続部分
  chain_n : 固定長シーケンス（例: ident "(" args ")"）
  chain_l : トークン + 後続空白スキップ（値はトークン側だけ返す）
  chain_r : 先頭空白スキップ + 本体（値は本体側だけ返す）
  sep_by  : カンマ区切り引数リスト
  convert : パース結果のタプルを AST ノードに変換
  map_    : 単一値の型ラッピング（Num, Str, Ident 等）
  label   : エラーメッセージのカスタマイズ
  peek    : kwarg/posarg や call/ident の先読み分岐（入力を消費しない）
  use     : 先読み結果に基づく動的パーサー選択
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
# Ctx — パーサーコンテキスト
#
# combp のコンビネータは「コンテキスト → (新コンテキスト, 値)」という形で
# 動作する。Ctx は入力文字列と現在の読み取り位置を保持する。
# frozen=True にすることで、パース途中の状態が意図せず変更されるのを防ぐ。
# offset プロパティを持つため combp の HasOffset プロトコルを満たし、
# or_n の最遠失敗追跡や repeat の無限ループ防止が自動的に有効になる。
# ===========================================================================


@dataclass(frozen=True)
class Ctx:
    src: str
    offset: int = 0


# ===========================================================================
# プリミティブパーサー
#
# combp 本体はデータ構造に依存しない汎用ライブラリなので、
# 「1文字を読む」「特定の文字列にマッチする」といった最小単位は
# アプリケーション側で定義する。以下はこの DSL 用のプリミティブ群。
# ===========================================================================


def satisfy(pred, desc: str) -> Combinator[Ctx, str]:
    """条件 pred を満たす1文字を消費する。

    combp の repeat や sep_by と組み合わせて
    「数字の連続」「英数字の連続」などを構成する基本部品。
    """
    def _f(c: Ctx) -> CombinatorResult[Ctx, str]:
        if c.offset >= len(c.src):
            return err(c, f"{desc} が必要ですが EOF")
        ch = c.src[c.offset]
        if not pred(ch):
            return err(c, f"{desc} が必要ですが '{ch}'")
        return ok(Ctx(c.src, c.offset + 1), ch)
    return _f


def literal(s: str) -> Combinator[Ctx, str]:
    """固定文字列にマッチする。startswith で一括比較するため、
    satisfy を文字数分繰り返すより高速。
    sym("->") や sym("..") など記号トークンの土台。
    """
    def _f(c: Ctx) -> CombinatorResult[Ctx, str]:
        if c.src.startswith(s, c.offset):
            return ok(Ctx(c.src, c.offset + len(s)), s)
        return err(c, f"'{s}' が必要")
    return _f


# 空白: スペース、タブ、改行を0文字以上スキップ。
# repeat(ws_char, must=0) なので、空白がなくても成功する。
ws_char = satisfy(lambda ch: ch in " \t\r\n", "空白")
ws = map_(repeat(ws_char, must=0), lambda _: None)


def tok(p: Combinator[Ctx, Any]) -> Combinator[Ctx, Any]:
    """トークナイザ: パーサー p を実行した後、後続の空白をスキップする。

    chain_l(p, ws) は「p の結果を返しつつ、ws も消費する」という意味。
    これにより各パーサーは自分の後ろの空白を気にしなくてよくなる。
    """
    return chain_l(p, ws)


def sym(s: str) -> Combinator[Ctx, str]:
    """記号トークン: literal + 後続空白スキップ。
    sym("("), sym(".."), sym("->") のように使う。
    """
    return tok(literal(s))


# ===========================================================================
# 数値 / 識別子 / 文字列 パーサー
#
# DSL のリテラル値を読み取る。それぞれ tok() でラップしているため、
# パース後に後続の空白が自動スキップされる。
# ===========================================================================

# 1文字分のプリミティブ
digit = satisfy(str.isdigit, "数字")
alpha = satisfy(lambda ch: ch.isalpha() or ch == "_", "英字")
alnum = satisfy(lambda ch: ch.isalnum() or ch == "_", "英数字")


def _number(c: Ctx) -> CombinatorResult[Ctx, float]:
    """数値リテラルをパースする。

    対応フォーマット: 30, -2, 3.14, 0.5
    注意: ".." (範囲演算子) との曖昧性を解消するため、
    "." の次がさらに "." なら小数点ではなく範囲と判断する。

    例:
      "2.0..3.0" → Num(2.0) を返し、".." 以降は range_or_atom が処理
      "3.14"     → Num(3.14) を返す
    """
    start = c.offset
    cur = c

    # 符号（オプショナル）
    sign = 1
    if cur.offset < len(cur.src) and cur.src[cur.offset] == "-":
        sign = -1
        cur = Ctx(cur.src, cur.offset + 1)

    # 整数部（1桁以上必須）
    int_part = repeat(digit, must=1)(cur)
    if not int_part.ok:
        return err(c, "数値が必要")
    cur = int_part.context

    # 小数部（オプショナル）
    has_frac = False
    if cur.offset < len(cur.src) and cur.src[cur.offset] == ".":
        # ".." との区別: 次の文字も "." なら範囲演算子なので小数として扱わない
        if cur.offset + 1 < len(cur.src) and cur.src[cur.offset + 1] == ".":
            pass  # "2.0.." → 小数部なし、".." は後続パーサーに任せる
        else:
            frac = repeat(digit, must=1)(Ctx(cur.src, cur.offset + 1))
            if frac.ok:
                cur = frac.context
                has_frac = True

    text = c.src[start:cur.offset]
    return ok(cur, float(text))


number = tok(_number)


def _ident(c: Ctx) -> CombinatorResult[Ctx, str]:
    """識別子: 英字またはアンダースコアで始まり、英数字が続く。

    例: rate, vec3, on_collide, _private
    """
    first = alpha(c)
    if not first.ok:
        return err(c, "識別子が必要")
    rest = repeat(alnum, must=0)(first.context)
    chars = [first.value] + (rest.value if rest.ok else [])
    end_ctx = rest.context if rest.ok else first.context
    return ok(end_ctx, "".join(chars))


ident = tok(_ident)


def _string(c: Ctx) -> CombinatorResult[Ctx, str]:
    """文字列リテラル: ダブルクォートで囲まれたテキスト。

    例: "small_spark"
    エスケープシーケンスは未対応（必要なら拡張可能）。
    """
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
# AST (抽象構文木)
#
# パース結果をこれらの不変データクラスで表現する。
# frozen=True により、パース後の AST を安全に共有・比較できる。
# Python 3.10+ の match 文でパターンマッチによる分解が可能。
# ===========================================================================


@dataclass(frozen=True)
class Num:
    """数値リテラル。例: 30, 2.0, -1.5"""
    value: float

@dataclass(frozen=True)
class Str:
    """文字列リテラル。例: "small_spark" """
    value: str

@dataclass(frozen=True)
class Ident:
    """識別子。例: forward, hp"""
    name: str

@dataclass(frozen=True)
class Range:
    """範囲式。例: 2.0..3.0
    パーティクルの寿命やサイズなど、ランダム幅を持つパラメータに使用。
    """
    lo: "Expr"
    hi: "Expr"

@dataclass(frozen=True)
class Call:
    """関数呼び出し。例: rgba(1, 0, 0, 1), vec3(0, 5, 0)
    色、ベクトル、グラデーションなどの構築関数を表現。
    """
    name: str
    args: tuple["Arg", ...]

@dataclass(frozen=True)
class Stop:
    """グラデーション/カーブのキーフレーム。例: 0.0 -> rgba(1, 1, 0, 1)
    at が時間軸上の位置、value がその位置での値。
    """
    at: "Expr"
    value: "Expr"

@dataclass(frozen=True)
class Positional:
    """位置引数。例: rgba(1, 0, 0, 1) の各数値"""
    value: "Expr"

@dataclass(frozen=True)
class Keyword:
    """キーワード引数。例: rate = 30"""
    name: str
    value: "Expr"

# 型エイリアス
Expr = Num | Str | Ident | Range | Call | Stop
Arg = Positional | Keyword


# ===========================================================================
# 文法定義
#
# combp のコンビネータを組み合わせて、上記 EBNF に対応するパーサーを
# 宣言的に構築する。各パーサーは Combinator[Ctx, T] 型の値であり、
# 関数のように呼び出すと CombinatorResult[Ctx, T] を返す。
#
# 相互再帰の依存関係:
#   expr → range_or_atom → atom → _call_or_ident → call → args → arg → expr
# この循環を lazy() で遅延評価することで解決している。
# ===========================================================================

# ---------------------------------------------------------------------------
# expr (トップレベル式)
#
# lazy で遅延定義。_expr_impl がまだ存在しない時点でも参照できる。
# args → arg → expr → ... の相互再帰を成立させるために必須。
# ---------------------------------------------------------------------------
expr: Combinator[Ctx, Expr] = lazy(lambda: _expr_impl)


# ---------------------------------------------------------------------------
# atom (不可分な式)
#
# or_n で3つの選択肢を順に試す:
#   1. 数値    → "3.14" のように数字で始まる
#   2. 文字列  → '"' で始まる
#   3. 呼び出し or 識別子 → 英字で始まる
#
# 先頭文字が異なるため、or_n のバックトラックは最小限で済む。
# _call_or_ident は lazy で遅延参照（call → args → expr の再帰があるため）。
# ---------------------------------------------------------------------------
atom: Combinator[Ctx, Expr] = or_n(
    map_(number, lambda v: Num(v)),
    map_(string_lit, lambda v: Str(v)),
    lazy(lambda: _call_or_ident),
)


# ---------------------------------------------------------------------------
# range_or_atom (範囲式)
#
# atom の後に ".." が続けば Range、なければ atom をそのまま返す。
# option() により ".." がなくても成功する（None が返る）。
#
# 例: "2.0..3.0" → Range(Num(2.0), Num(3.0))
#     "30"       → Num(30.0)
# ---------------------------------------------------------------------------
def _maybe_range(lo: Expr, rest: Any) -> Expr:
    return Range(lo, rest) if rest is not None else lo

range_or_atom: Combinator[Ctx, Expr] = convert(
    chain_n(atom, option(chain_r(sym(".."), atom))),
    lambda parts, _: _maybe_range(parts[0], parts[1]),
)


# ---------------------------------------------------------------------------
# _expr_impl (式の本体: ストップ構文を含む)
#
# range_or_atom の後に "->" が続けば Stop（グラデーションのキーフレーム）。
# 右辺は再帰的に _expr_impl を参照するため、右結合で任意の深さまでネスト可能。
#
# 例: "0.0 -> rgba(1, 1, 0, 1)"     → Stop(Num(0.0), Call("rgba", ...))
#     "a -> b -> c"                  → Stop(Ident("a"), Stop(Ident("b"), Ident("c")))
#
# もし1階層に制限したい場合は lazy(lambda: _expr_impl) を range_or_atom に変更する。
# ---------------------------------------------------------------------------
_expr_impl: Combinator[Ctx, Expr] = convert(
    chain_n(range_or_atom, option(chain_r(sym("->"), lazy(lambda: _expr_impl)))),
    lambda parts, _: Stop(parts[0], parts[1]) if parts[1] is not None else parts[0],
)


# ---------------------------------------------------------------------------
# kwarg / posarg / arg (関数引数)
#
# 引数は「キーワード引数 (name = expr)」か「位置引数 (expr)」のどちらか。
#
# 素朴な実装 or_n(kwarg, posarg) だと、位置引数が識別子で始まる場合に
# kwarg が ident を消費 → "=" がなくて失敗 → バックトラック → posarg が
# 再度 ident を読む、という二重読みが発生する。
#
# 改善: option(peek(chain_n(ident, sym("=")))) で kwarg パターンを先読みし、
# マッチすれば kwarg、しなければ posarg へ直行する。peek は入力を消費しないため、
# 先読みの後に本番パーサーが最初から読み直しても無駄は最小限。
# ---------------------------------------------------------------------------

kwarg: Combinator[Ctx, Arg] = label(
    "'名前 = 値' 形式のキーワード引数が必要です",
    convert(
        chain_n(ident, sym("="), label("'=' の後に式が必要です", expr)),
        lambda parts, _: Keyword(parts[0], parts[2]),
    ),
)

posarg: Combinator[Ctx, Arg] = map_(expr, lambda e: Positional(e))

# 先読み: ident "=" パターンがあるかチェック（入力は消費しない）
_kwarg_lookahead: Combinator[Ctx, Any] = peek(chain_n(ident, sym("=")))

# use で先読み結果に応じてパーサーを動的に選択:
#   - マッチあり (not None) → kwarg パーサーを実行
#   - マッチなし (None)     → posarg パーサーを実行
arg: Combinator[Ctx, Arg] = use(
    option(_kwarg_lookahead),
    lambda matched: kwarg if matched is not None else posarg,
)

# sep_by でカンマ区切りの引数リストを構成
args: Combinator[Ctx, list[Arg]] = sep_by(arg, sym(","))


# ---------------------------------------------------------------------------
# call / _call_or_ident (関数呼び出し or 識別子)
#
# "rgba(1, 0, 0, 1)" と "forward" は両方とも識別子で始まるため、
# "(" の有無で分岐する必要がある。
#
# 素朴な実装 or_n(call, ident_map) だと、識別子の場合に call が
# ident を消費 → "(" がなくて失敗 → バックトラック → ident_map が
# 再度 ident を読む。
#
# 改善: peek(chain_n(ident, option(sym("(")))) で識別子と "(" の有無を
# 一度に先読みし、"(" があれば call、なければ Ident へ直行する。
# ---------------------------------------------------------------------------

# 関数呼び出し: ident "(" args ")"
call: Combinator[Ctx, Call] = convert(
    chain_n(ident, sym("("), args, sym(")")),
    lambda parts, _: Call(parts[0], tuple(parts[2])),
)

# 先読みで "(" の有無まで確認し、call か Ident を選択
_call_or_ident: Combinator[Ctx, Expr] = use(
    peek(chain_n(ident, option(sym("(")))),
    lambda parts: call if parts[1] is not None else map_(ident, lambda n: Ident(n)),
)


# ---------------------------------------------------------------------------
# EOF チェッカ / トップレベルパーサー
# ---------------------------------------------------------------------------

def _eof(c: Ctx) -> CombinatorResult[Ctx, None]:
    """入力の終端を確認する。余分な文字が残っていればエラー。"""
    if c.offset >= len(c.src):
        return ok(c, None)
    return err(c, f"余分な入力: {c.src[c.offset:c.offset+20]!r}")


# トップレベル: 先頭空白 → 式 → EOF
# chain_r(ws, expr): 先頭の空白をスキップしてから式をパース
# chain_l(..., _eof): 式の後に余分な入力がないことを確認
top_parser: Combinator[Ctx, Expr] = chain_l(chain_r(ws, expr), _eof)


# ===========================================================================
# pretty-print
#
# AST を人間が読みやすいインデント付きテキストで出力する。
# ===========================================================================


def pretty(e: Expr, indent: int = 0) -> str:
    """AST ノードをインデント付き文字列に変換する。"""
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
    """引数ノード (Keyword / Positional) を文字列に変換する。"""
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
    # -----------------------------------------------------------------------
    # パース実行: DSL テキスト → AST
    # -----------------------------------------------------------------------
    r = top_parser(Ctx(SAMPLE))
    if not r.ok:
        print("パース失敗:", r.error.message, "at offset", r.error.on.offset)
        raise SystemExit(1)

    print("=== AST ===")
    print(pretty(r.value))

    # -----------------------------------------------------------------------
    # 構造検証: パース結果が期待通りか assert で確認
    # -----------------------------------------------------------------------
    assert isinstance(r.value, Call) and r.value.name == "emitter"

    # match で各キーワード引数を名前付き辞書に展開
    kw = {a.name: a.value for a in r.value.args if isinstance(a, Keyword)}

    assert isinstance(kw["rate"], Num) and kw["rate"].value == 30
    assert isinstance(kw["life"], Range)
    assert isinstance(kw["color"], Call) and kw["color"].name == "gradient"
    assert isinstance(kw["on_collide"], Str) and kw["on_collide"].value == "small_spark"

    print("\n✓ パース結果の構造検証 OK")

    # -----------------------------------------------------------------------
    # エラー例: 不正な入力に対するエラーメッセージの確認
    #
    # "rate = " の後に値がない → kwarg 内の label が
    # "'=' の後に式が必要です" というメッセージを出す。
    # さらに combp の furthest 追跡により、最も深くまで進んだ
    # 失敗地点が自動的に報告される。
    # -----------------------------------------------------------------------
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
