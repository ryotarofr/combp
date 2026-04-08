"""
オプショナルコンビネータ。
"""

from __future__ import annotations

from .combinator_types import Combinator, CombinatorResult, ok


def option[C, T](combinator: Combinator[C, T]) -> Combinator[C, T | None]:
    """
    コンビネータを試し、失敗した場合はエラーなしで None を返す。

    成功した場合は結果をそのまま返す。
    正規表現の ``?`` に相当する。コンテキストは失敗時には進まない。

    型パラメータ:
        C: コンテキスト型。
        T: 内側のコンビネータの結果型。

    Args:
        combinator: 省略可能な対象のコンビネータ。

    Returns:
        成功時に T 型の値、失敗時に None を返すコンビネータ。
        いずれの場合も ok=True となる。

    Example::

        c = option(same(","))
        r = c(Ctx("abc"))
        # r.ok == True, r.value is None
    """

    def _option(context: C) -> CombinatorResult[C, T | None]:
        result = combinator(context)
        if result.ok:
            return result  # type: ignore[return-value]
        return ok(context, None)

    return _option
