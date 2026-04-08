"""
combinator モジュールの包括的テスト。

TypeScript / Go / Rust 版と同等のテストケースを網羅する。
"""

from __future__ import annotations

import pytest
from dataclasses import dataclass
from typing import Optional

from combp import (
    chain,
    chain_n,
    chain_l,
    chain_r,
    convert,
    label,
    lazy,
    not_,
    option,
    or_,
    or_n,
    peek,
    repeat,
    sep_by,
    use,
)
from combp import Combinator, CombinatorResult, OnError, deeper_error, err, map_, ok

# ===========================================================================
# テスト用コンテキスト（Go/Rust/TS と同等のオフセット付き）
# ===========================================================================


@dataclass(frozen=True)
class Ctx:
    """オフセット追跡付きの文字列パースコンテキスト。"""

    src: str
    offset: int = 0


# ===========================================================================
# プリミティブパーサー（テスト用ヘルパー）
# ===========================================================================


def any_char(context: Ctx) -> CombinatorResult[Ctx, str]:
    """1文字を消費する。"""
    if context.offset >= len(context.src):
        return err(context, "any: 入力の終端です")
    ch = context.src[context.offset]
    return ok(Ctx(src=context.src, offset=context.offset + 1), ch)


def same(expected: str) -> Combinator[Ctx, str]:
    """指定した1文字にマッチする。"""

    def _same(context: Ctx) -> CombinatorResult[Ctx, str]:
        r = any_char(context)
        if not r.ok:
            return r
        if r.value != expected:
            return err(
                context, f"'{expected}' が期待されましたが '{r.value}' でした"
            )
        return r

    return _same


def digit(context: Ctx) -> CombinatorResult[Ctx, str]:
    """1桁の数字にマッチする。"""
    r = any_char(context)
    if not r.ok:
        return r
    if not r.value.isdigit():
        return err(context, f"数字が期待されましたが '{r.value}' でした")
    return r


def keyword(word: str) -> Combinator[Ctx, str]:
    """指定した文字列にマッチする。"""

    def _keyword(context: Ctx) -> CombinatorResult[Ctx, str]:
        if context.src[context.offset :].startswith(word):
            return ok(
                Ctx(src=context.src, offset=context.offset + len(word)), word
            )
        return err(context, f"'{word}' が期待されました")

    return _keyword


def parse(c: Combinator[Ctx, any], input_str: str) -> CombinatorResult[Ctx, any]:
    """ヘルパー: コンビネータに入力文字列を渡す。"""
    return c(Ctx(src=input_str))


# ===========================================================================
# テスト
# ===========================================================================


class TestBasic:
    """基本テスト"""

    def test_any(self):
        """1文字を消費する"""
        r = parse(any_char, "abc")
        assert r.ok
        assert r.value == "a"
        assert r.context.offset == 1

    def test_same(self):
        """指定した文字にマッチする"""
        r = parse(same("a"), "abc")
        assert r.ok
        assert r.value == "a"

        r2 = parse(same("x"), "abc")
        assert not r2.ok

    def test_chain(self):
        """2つのコンビネータを順次実行する"""
        c = chain(same("a"), same("b"))
        r = parse(c, "abc")
        assert r.ok
        assert r.value == ("a", "b")

    def test_or(self):
        """最初に成功した方を返す"""
        c = or_(same("x"), same("a"))
        r = parse(c, "abc")
        assert r.ok
        assert r.value == "a"

    def test_or_furthest_failure(self):
        """最遠失敗を追跡する"""
        # "ab" パーサーは offset=1 で失敗、"x" パーサーは offset=0 で失敗
        ab = chain(same("a"), same("x"))
        ab_mapped = convert(ab, lambda p, _: f"{p[0]}{p[1]}")
        xy = same("x")

        c = or_(ab_mapped, xy)
        r = parse(c, "abc")
        assert not r.ok
        error = r.error
        assert error.furthest is not None
        # "ab" 分岐の方が先まで進んだ (offset=1)
        assert error.furthest.on.offset == 1

    def test_convert(self):
        """成功結果を変換する"""
        c = convert(digit, lambda s, _: int(s))
        r = parse(c, "7abc")
        assert r.ok
        assert r.value == 7

    def test_map(self):
        """map_ で値だけを変換する"""
        c = map_(digit, lambda s: int(s) * 2)
        r = parse(c, "7abc")
        assert r.ok
        assert r.value == 14

    def test_not(self):
        """否定先読み"""
        c = not_(same("x"))
        r = parse(c, "abc")
        assert r.ok
        # コンテキストは進まない
        assert r.context.offset == 0

    def test_not_fail(self):
        """否定先読み - マッチしたら失敗"""
        c = not_(same("a"))
        r = parse(c, "abc")
        assert not r.ok

    def test_option(self):
        """オプショナル（失敗時 None）"""
        c = option(same("x"))
        r = parse(c, "abc")
        assert r.ok
        assert r.value is None

        r2 = parse(c, "xyz")
        assert r2.ok
        assert r2.value == "x"


class TestRepeat:
    """繰り返しテスト"""

    def test_repeat(self):
        """繰り返しマッチ"""
        c = repeat(digit, must=1)
        r = parse(c, "123abc")
        assert r.ok
        assert r.value == ["1", "2", "3"]

    def test_repeat_with_bounds(self):
        """最大回数制限"""
        c = repeat(digit, must=1, to=2)  # 最低1回、最大2回
        r = parse(c, "123abc")
        assert r.ok
        assert len(r.value) == 2

    def test_repeat_min_fail(self):
        """最低回数未満で失敗"""
        c = repeat(digit, must=3)
        r = parse(c, "12abc")
        assert not r.ok

    def test_repeat_infinite_loop_protection(self):
        """無限ループ防止"""
        # peek は入力を消費しないので、無限ループになるはず
        # offset チェックにより安全に停止する
        c = repeat(peek(same("a")), must=0)
        r = parse(c, "abc")
        assert r.ok
        # peek は入力を進めないので、結果は空リスト
        assert r.value == []

    def test_repeat_zero_must(self):
        """must=0 で0回マッチでも成功"""
        c = repeat(digit, must=0)
        r = parse(c, "abc")
        assert r.ok
        assert r.value == []

    def test_repeat_argument_validation(self):
        """不正な引数で例外"""
        with pytest.raises(ValueError):
            repeat(digit, must=1, to=0)
        with pytest.raises(ValueError):
            repeat(digit, must=3, to=2)


class TestSepBy:
    """sepBy テスト"""

    def test_sep_by(self):
        """区切り文字区切りリスト"""
        comma = same(",")
        c = sep_by(digit, comma, min_count=0)

        # 複数要素
        r = parse(c, "1,2,3abc")
        assert r.ok
        assert r.value == ["1", "2", "3"]

        # 空入力
        r2 = parse(c, "abc")
        assert r2.ok
        assert r2.value == []

        # 要素1つ
        r3 = parse(c, "5abc")
        assert r3.ok
        assert r3.value == ["5"]

    def test_sep_by_min(self):
        """最低要素数未満で失敗"""
        c = sep_by(digit, same(","), min_count=2)
        r = parse(c, "1abc")
        assert not r.ok


class TestControl:
    """制御コンビネータテスト"""

    def test_lazy(self):
        """遅延構築とキャッシュ"""
        call_count = [0]

        def factory():
            call_count[0] += 1
            return same("a")

        c = lazy(factory)

        # 初回呼び出しでファクトリが実行される
        r = parse(c, "abc")
        assert r.ok
        assert r.value == "a"
        assert call_count[0] == 1

        # 2回目はキャッシュを使う
        r2 = parse(c, "abc")
        assert r2.ok
        assert call_count[0] == 1

    def test_peek(self):
        """先読み（入力を消費しない）"""
        c = peek(same("a"))
        r = parse(c, "abc")
        assert r.ok
        assert r.value == "a"
        # peek は位置を進めない
        assert r.context.offset == 0

    def test_peek_fail(self):
        """先読みの失敗"""
        c = peek(same("x"))
        r = parse(c, "abc")
        assert not r.ok

    def test_use(self):
        """先行結果によるディスパッチ"""

        def selector(ch: str):
            if ch == "a":
                return keyword("abc")
            elif ch == "x":
                return keyword("xyz")
            else:
                return None

        c = use(peek(any_char), selector)

        r = parse(c, "abcdef")
        assert r.ok
        assert r.value == "abc"

        r2 = parse(c, "xyzabc")
        assert r2.ok
        assert r2.value == "xyz"

        r3 = parse(c, "qqq")
        assert not r3.ok

    def test_label(self):
        """エラーメッセージの上書き"""
        c = label("数値が必要です", digit)
        r = parse(c, "abc")
        assert not r.ok
        assert r.error.message == "数値が必要です"


class TestNAry:
    """可変長コンビネータテスト"""

    def test_chain_n(self):
        """N個の順次実行"""
        c = chain_n(same("a"), same("b"), same("c"))
        r = parse(c, "abcde")
        assert r.ok
        assert r.value == ["a", "b", "c"]

    def test_chain_n_fail(self):
        """途中で失敗"""
        c = chain_n(same("a"), same("x"), same("c"))
        r = parse(c, "abcde")
        assert not r.ok

    def test_chain_l(self):
        """最初の結果のみを返す"""
        c = chain_l(same("a"), same("b"), same("c"))
        r = parse(c, "abcde")
        assert r.ok
        assert r.value == "a"

    def test_chain_r(self):
        """最後の結果のみを返す"""
        c = chain_r(same("a"), same("b"), same("c"))
        r = parse(c, "abcde")
        assert r.ok
        assert r.value == "c"

    def test_or_n(self):
        """N個の代替実行"""
        c = or_n(same("x"), same("y"), same("a"))
        r = parse(c, "abc")
        assert r.ok
        assert r.value == "a"

    def test_or_n_all_fail(self):
        """全て失敗"""
        c = or_n(same("x"), same("y"), same("z"))
        r = parse(c, "abc")
        assert not r.ok


class TestIntegration:
    """統合テスト"""

    def test_line_parser(self):
        """複数行のパース"""
        eol = same("\n")
        not_eol = convert(chain(not_(eol), any_char), lambda p, _: p[1])
        line = convert(
            chain(repeat(not_eol, must=1), option(eol)),
            lambda p, _: "".join(p[0]),
        )
        lines = repeat(line, must=0)

        r = parse(lines, "line1\nline2\nline3")
        assert r.ok
        assert r.value == ["line1", "line2", "line3"]

    def test_number_parser(self):
        """数値パーサー"""
        digits = map_(repeat(digit, must=1), lambda ds: "".join(ds))
        number = map_(digits, int)

        r = parse(number, "42abc")
        assert r.ok
        assert r.value == 42

    def test_csv_parser(self):
        """カンマ区切り数値リスト"""
        digits = map_(repeat(digit, must=1), lambda ds: "".join(ds))
        number = map_(digits, int)
        csv = sep_by(number, same(","), min_count=1)

        r = parse(csv, "1,23,456")
        assert r.ok
        assert r.value == [1, 23, 456]

    def test_recursive_parser(self):
        """再帰パーサー (括弧のネスト)"""
        # 括弧でネストした文字列: "a", "(a)", "((a))" をパース
        inner: Combinator[Ctx, str] = lazy(
            lambda: or_(
                # 括弧あり: "(" inner ")"
                convert(
                    chain_n(same("("), inner, same(")")),
                    lambda parts, _: f"({parts[1]})",
                ),
                # 単一文字
                same("a"),
            )
        )

        r = parse(inner, "a")
        assert r.ok
        assert r.value == "a"

        r2 = parse(inner, "(a)")
        assert r2.ok
        assert r2.value == "(a)"

        r3 = parse(inner, "((a))")
        assert r3.ok
        assert r3.value == "((a))"

    def test_deeper_error_helper(self):
        """deeper_error ヘルパーの動作確認"""
        e1 = OnError(on=Ctx("abc", 0), message="err1")
        e2 = OnError(on=Ctx("abc", 3), message="err2")
        result = deeper_error(e1, e2)
        assert result.message == "err2"  # offset が大きい方

        result2 = deeper_error(e2, e1)
        assert result2.message == "err2"  # 常に offset が大きい方


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
