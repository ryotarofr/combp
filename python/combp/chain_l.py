"""
複数コンビネータを順次実行し、最初の結果のみを返す。
"""

from __future__ import annotations

from typing import Any

from .chain_n import chain_n
from .convert import convert
from .combinator_types import Combinator


def chain_l[C](*combinators: Combinator[C, Any]) -> Combinator[C, Any]:
    """
    コンビネータを順に実行し、最初（左端）の結果のみを返す。

    2番目以降のコンビネータは実行されるが、その結果は捨てられる。
    トークン後の空白スキップなどに便利。

    型パラメータ:
        C: コンテキスト型。

    Args:
        *combinators: 順に実行するコンビネータの可変長引数。
            少なくとも1つ必要。

    Returns:
        成功時に最初のコンビネータの結果を返すコンビネータ。

    Raises:
        ValueError: combinators が空の場合。

    Example::

        # "a" をパースし、後続の "b" を消費するが結果は "a" のみ
        c = chain_l(same("a"), same("b"))
        r = c(Ctx("abc"))
        # r.value == "a", r.context.offset == 2
    """
    if not combinators:
        raise ValueError("chain_l() には少なくとも1つのコンビネータが必要です。")
    return convert(chain_n(*combinators), lambda it, _: it[0])
