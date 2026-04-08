"""
複数コンビネータの順次実行。
"""

from __future__ import annotations

from typing import Any

from .combinator_types import Combinator, CombinatorResult, ok


def chain_n[C](*combinators: Combinator[C, Any]) -> Combinator[C, list[Any]]:
    """
    一連のコンビネータを順に実行し、結果をリストで返す。

    いずれかが失敗した時点でそのエラーを返す。
    型安全なタプル版が必要な場合は chain を入れ子にすること。

    型パラメータ:
        C: コンテキスト型。

    Args:
        *combinators: 順に実行するコンビネータの可変長引数。
            各コンビネータの結果型は任意（Any）。

    Returns:
        成功時に各コンビネータの結果を格納した list[Any] を返すコンビネータ。
        リストのインデックスは combinators の順序に対応する。

    Example::

        c = chain_n(same("a"), same("b"), same("c"))
        r = c(Ctx("abcde"))
        # r.value == ["a", "b", "c"]
    """

    def _chain_n(context: C) -> CombinatorResult[C, list[Any]]:
        results: list[Any] = []
        current = context

        for c in combinators:
            result = c(current)
            if not result.ok:
                return result  # type: ignore[return-value]
            results.append(result.value)
            current = result.context

        return ok(current, results)

    return _chain_n
