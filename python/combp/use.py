"""
条件分岐コンビネータ。
"""

from __future__ import annotations

from typing import Callable

from .combinator_types import Combinator, CombinatorResult, err


def use[C, M, T](
    from_: Combinator[C, M],
    selector: Callable[[M], Combinator[C, T] | None],
) -> Combinator[C, T]:
    """
    from_ を実行し、その結果に基づいて次のコンビネータを動的に選択する。

    先行パーサーの結果をキーとして、後続のパーサーをディスパッチするパターンに使う。
    セレクタが None を返した場合、コンビネータは失敗する。

    型パラメータ:
        C: コンテキスト型。
        M: 先行コンビネータ（from_）の結果型。selector の引数に渡される中間型。
        T: selector が選択したコンビネータの結果型。最終的な成功値の型。

    Args:
        from_: 最初に実行するコンビネータ。この結果が selector に渡される。
        selector: from_ の結果を受け取り、次に実行するコンビネータを返す関数。
            該当するコンビネータがない場合は None を返す。

    Returns:
        selector が選択したコンビネータの結果を返すコンビネータ。

    Example::

        # 先頭文字を peek して対応するキーワードパーサーを選択
        def selector(ch: str):
            if ch == "i": return keyword("if")
            if ch == "w": return keyword("while")
            return None

        c = use(peek(any_char), selector)
        r = c(Ctx("if ..."))
        # r.value == "if"
    """

    def _use(context: C) -> CombinatorResult[C, T]:
        from_result = from_(context)
        if not from_result.ok:
            return from_result  # type: ignore[return-value]
        next_comb = selector(from_result.value)
        if next_comb is None:
            return err(
                context,
                f"use: セレクタが {from_result.value} に対して None を返しました",
            )
        return next_comb(from_result.context)

    return _use
