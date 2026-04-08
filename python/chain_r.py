"""
複数コンビネータを順次実行し、最後の結果のみを返す。
"""

from __future__ import annotations

from typing import Any

from .chain_n import chain_n
from .convert import convert
from .combinator_types import Combinator


def chain_r[C](*combinators: Combinator[C, Any]) -> Combinator[C, Any]:
    """
    コンビネータを順に実行し、最後（右端）の結果のみを返す。

    最後以外のコンビネータは実行されるが、その結果は捨てられる。
    プレフィクスやデリミタを読み飛ばしてから本体を取得する場合に便利。

    型パラメータ:
        C: コンテキスト型。

    Args:
        *combinators: 順に実行するコンビネータの可変長引数。
            少なくとも1つ必要。

    Returns:
        成功時に最後のコンビネータの結果を返すコンビネータ。

    Raises:
        ValueError: combinators が空の場合。

    Example::

        # 先頭の空白を読み飛ばし、数字だけ取得
        c = chain_r(same(" "), digit)
        r = c(Ctx(" 7"))
        # r.value == "7"
    """
    if not combinators:
        raise ValueError("chain_r() には少なくとも1つのコンビネータが必要です。")
    return convert(chain_n(*combinators), lambda it, _: it[-1])
