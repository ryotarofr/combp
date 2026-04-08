"""
2つのコンビネータの二者択一。
"""

from __future__ import annotations

from .combinator_types import Combinator, CombinatorResult, err, deeper_error


def or_[C, L, R](
    lhs: Combinator[C, L], rhs: Combinator[C, R]
) -> Combinator[C, L | R]:
    """
    lhs を先に試し、失敗したら rhs を試す（二者択一）。

    両方失敗した場合、入力をより先まで消費した分岐のエラーを furthest として
    記録する。これにより、ユーザーは「どの分岐が最も惜しかったか」を把握できる。

    型パラメータ:
        C: コンテキスト型。HasOffset を実装していれば最遠失敗追跡が有効になる。
        L: lhs の成功時の結果型。
        R: rhs の成功時の結果型。

    Args:
        lhs: 最初に試すコンビネータ。
        rhs: lhs が失敗した場合に試すコンビネータ。

    Returns:
        成功時に L | R 型の値を返すコンビネータ。
        lhs が成功すれば L、rhs が成功すれば R の値を返す。

    Example::

        c = or_(same("a"), same("b"))
        r = c(Ctx("bcd"))
        # r.value == "b"
    """

    def _or(context: C) -> CombinatorResult[C, L | R]:
        lhs_result = lhs(context)
        if lhs_result.ok:
            return lhs_result  # type: ignore[return-value]
        rhs_result = rhs(context)
        if rhs_result.ok:
            return rhs_result  # type: ignore[return-value]

        # 最も深くまで進んだエラーを furthest として記録する
        furthest = deeper_error(lhs_result.error, rhs_result.error)
        return err(context, "or", [lhs_result.error, rhs_result.error], furthest)

    return _or
