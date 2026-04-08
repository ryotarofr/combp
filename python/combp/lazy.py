"""
遅延評価コンビネータ。
"""

from __future__ import annotations

from typing import Callable

from .combinator_types import Combinator, CombinatorResult


def lazy[C, T](get_combinator: Callable[[], Combinator[C, T]]) -> Combinator[C, T]:
    """
    コンビネータの構築を遅延させ、循環参照を回避する。

    ファクトリ関数は最初の呼び出し時に1回だけ実行され、以降はキャッシュを使用する。
    再帰的なパーサー（括弧のネストなど）を定義する際に必須となる。

    型パラメータ:
        C: コンテキスト型。
        T: 内側のコンビネータの結果型。

    Args:
        get_combinator: コンビネータを生成するファクトリ関数。
            引数なしで呼び出され、Combinator[C, T] を返す。
            この関数内で lazy の戻り値自身を参照することで循環参照を実現できる。

    Returns:
        ファクトリが生成するコンビネータと同じ振る舞いをするコンビネータ。

    Example::

        # 再帰パーサー: "a", "(a)", "((a))", ...
        expr: Combinator[Ctx, str] = lazy(
            lambda: or_(
                convert(chain_n(same("("), expr, same(")")),
                        lambda p, _: f"({p[1]})"),
                same("a"),
            )
        )
    """
    cached: Combinator[C, T] | None = None

    def _lazy(context: C) -> CombinatorResult[C, T]:
        nonlocal cached
        if cached is None:
            cached = get_combinator()
        return cached(context)

    return _lazy
