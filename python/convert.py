"""
変換関数による成功結果の型変換。
"""

from __future__ import annotations

from typing import Callable

from .combinator_types import Combinator, CombinatorResult, ok


def convert[C, A, B](
    combinator: Combinator[C, A],
    func: Callable[[A, C], B],
) -> Combinator[C, B]:
    """
    成功結果を変換関数で別の型に写す。

    内側のコンビネータが成功した場合、その値とコンテキストを func に渡して変換する。
    失敗した場合はそのままエラーを返す。

    型パラメータ:
        C: コンテキスト型。
        A: 変換前の結果型（内側のコンビネータの成功型）。
        B: 変換後の結果型。

    Args:
        combinator: 内側のコンビネータ。
        func: 変換関数。(成功値: A, コンテキスト: C) -> B の形式。
            コンテキストを参照して変換結果を調整したい場合に有用。

    Returns:
        成功時に B 型の値を返すコンビネータ。

    Example::

        # 数字文字を int に変換
        c = convert(digit, lambda s, _: int(s))
        r = c(Ctx("7abc"))
        # r.value == 7
    """

    def _convert(context: C) -> CombinatorResult[C, B]:
        result = combinator(context)
        if not result.ok:
            return result  # type: ignore[return-value]
        return ok(result.context, func(result.value, result.context))

    return _convert


def map_[C, A, B](
    combinator: Combinator[C, A],
    func: Callable[[A], B],
) -> Combinator[C, B]:
    """
    convert の簡易版。コンテキストを無視して値だけを変換する。

    型パラメータ:
        C: コンテキスト型。
        A: 変換前の結果型。
        B: 変換後の結果型。

    Args:
        combinator: 内側のコンビネータ。
        func: 変換関数。(成功値: A) -> B の形式。

    Returns:
        成功時に B 型の値を返すコンビネータ。

    Example::

        c = map_(digit, lambda s: int(s) * 2)
        r = c(Ctx("7abc"))
        # r.value == 14
    """
    return convert(combinator, lambda a, _: func(a))
