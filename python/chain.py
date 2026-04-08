"""
2つのコンビネータの順次実行。
"""

from __future__ import annotations

from .combinator_types import Combinator, CombinatorResult, ok


def chain[C, L, R](
    lhs: Combinator[C, L], rhs: Combinator[C, R]
) -> Combinator[C, tuple[L, R]]:
    """
    2つのコンビネータを順に実行し、結果をタプルで返す。

    lhs が成功した場合、その更新されたコンテキストから rhs を実行する。
    どちらかが失敗した時点でそのエラーをそのまま返す。

    型パラメータ:
        C: コンテキスト型。
        L: lhs の成功時の結果型。
        R: rhs の成功時の結果型。

    Args:
        lhs: 最初に実行するコンビネータ。
        rhs: lhs 成功後に実行するコンビネータ。

    Returns:
        成功時に (L の値, R の値) のタプルを返すコンビネータ。

    Example::

        c = chain(same("a"), same("b"))
        r = c(Ctx("abc"))
        # r.value == ("a", "b")
    """

    def _chain(context: C) -> CombinatorResult[C, tuple[L, R]]:
        lhs_result = lhs(context)
        if not lhs_result.ok:
            return lhs_result  # type: ignore[return-value]
        rhs_result = rhs(lhs_result.context)
        if not rhs_result.ok:
            return rhs_result  # type: ignore[return-value]
        return ok(rhs_result.context, (lhs_result.value, rhs_result.value))

    return _chain
