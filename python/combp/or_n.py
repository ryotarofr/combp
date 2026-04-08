"""
複数コンビネータの代替実行。
"""

from __future__ import annotations

from typing import Any

from .or_ import or_
from .combinator_types import Combinator


def or_n[C](*combinators: Combinator[C, Any]) -> Combinator[C, Any]:
    """
    各コンビネータを順に試し、最初に成功したものを返す。

    全て失敗した場合、or_ の連鎖により最遠失敗（furthest）が自動的に追跡される。
    内部的には or_ を再帰的にネストして構築する。

    型パラメータ:
        C: コンテキスト型。HasOffset を実装していれば最遠失敗追跡が有効になる。

    Args:
        *combinators: 試行するコンビネータの可変長引数。
            少なくとも1つ必要。先頭から順に試行される。

    Returns:
        最初に成功したコンビネータの結果を返すコンビネータ。

    Raises:
        ValueError: combinators が空の場合。

    Example::

        c = or_n(same("x"), same("y"), same("a"))
        r = c(Ctx("abc"))
        # r.value == "a"（3番目で成功）
    """

    if not combinators:
        raise ValueError("or_n() には少なくとも1つのコンビネータが必要です。")

    def _nest(combs: list[Combinator[C, Any]]) -> Combinator[C, Any]:
        if len(combs) == 1:
            return combs[0]
        return or_(combs[0], _nest(combs[1:]))

    return _nest(list(combinators))
