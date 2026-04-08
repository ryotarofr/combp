"""
先読みコンビネータ。
"""

from __future__ import annotations

from .combinator_types import Combinator, CombinatorResult, ok


def peek[C, T](combinator: Combinator[C, T]) -> Combinator[C, T]:
    """
    コンビネータを実行するが、成功時にコンテキストを元に戻す（先読み）。

    入力を消費せずに「次に何が来るか」を確認したい場合に使う。
    失敗した場合はそのままエラーを返す。

    型パラメータ:
        C: コンテキスト型。
        T: 内側のコンビネータの結果型。

    Args:
        combinator: 先読み対象のコンビネータ。

    Returns:
        成功時にコンテキストを元の位置に戻した上で T 型の値を返すコンビネータ。

    Example::

        c = peek(same("a"))
        r = c(Ctx("abc"))
        # r.value == "a", r.context.offset == 0（位置は進まない）
    """

    def _peek(context: C) -> CombinatorResult[C, T]:
        result = combinator(context)
        if not result.ok:
            return result
        return ok(context, result.value)

    return _peek
